"""
streamlit_app.py - Smart Parking Management System

A production-style parking terminal UI on top of the existing, verified
pipeline: camera -> YOLO plate detection -> EasyOCR -> plate_ocr.py
(assembly/voting) -> MySQL (db.py) -> fare calculation (C binary).

This file wires that pipeline to the customer-facing screens in
ui/components.py. The pipeline itself is unchanged from the working
version - only what gets shown to the person standing at the terminal
has changed. No OCR reads, confidence scores, session IDs, or SQL details
are ever rendered here; see ui/components.py for the presentation layer.
"""

import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import os
import time
import pandas as pd
from datetime import datetime

# Plate text assembly / validation (post-processing only - the YOLO model
# and the EasyOCR reader are untouched, so recognition accuracy is unchanged)
import plate_ocr

# MySQL integration
import db

# Presentation layer - styling + reusable customer-facing UI blocks
from ui import styles, components

st.set_page_config(page_title="Parking", layout="wide", initial_sidebar_state="collapsed")
styles.inject()

# ── Session state ────────────────────────────────────────────────
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""
if "pending_plate" not in st.session_state:      # read, but not yet confirmed
    st.session_state.pending_plate = ""
if "last_processed" not in st.session_state:     # (plate, unix_ts) de-dupe guard
    st.session_state.last_processed = ("", 0.0)
if "page" not in st.session_state:
    st.session_state.page = "Scan"
if "db_ok" not in st.session_state:
    ok, info = db.test_connection()
    st.session_state.db_ok   = ok
    st.session_state.db_info = info

# ── Top bar ──────────────────────────────────────────────────────
components.render_topbar(st.session_state.page)

# ── Models ───────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    return YOLO("best.pt"), easyocr.Reader(['en'])

model, reader = load_models()

# Plate layouts and character repair live in plate_ocr.py.
OCR_MIN_CONF = 0.15      # ignore EasyOCR reads below this confidence
VOTE_THRESHOLD = 2       # a plate must be seen in this many separate frames
SCAN_SECONDS = 45        # wall-clock scan budget; OCR speed varies a lot
REPROCESS_COOLDOWN = 25  # seconds; a re-read of the same plate is ignored so a
                         # fresh entry is not instantly turned into an exit


def preprocess_plate(img):
    """Upscale, sharpen, and convert plate crop for better OCR accuracy."""
    if img is None or img.size == 0:
        return None
    h, w = img.shape[:2]
    scale = max(1, int(100 / max(h, 1)))
    if scale > 1:
        img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)


def run_scan(frame_ph):
    """
    Drive the camera for up to SCAN_SECONDS, voting per frame on the best
    plate read. Identical detection/matching logic to the verified pipeline -
    only the per-frame technical status text has been removed; the camera
    feed itself is still shown live.

    Returns "locked", "near_miss" or "none". On "locked",
    st.session_state.detected_plate is set; on "near_miss",
    st.session_state.pending_plate is set for manual confirmation.
    """
    cap = cv2.VideoCapture(0)

    # Warm-up: discard first 15 frames so camera auto-exposure settles
    for _ in range(15):
        cap.read()

    plate_votes = {}   # plate -> {"votes", "score"}
    scan_started = time.time()

    while time.time() - scan_started < SCAN_SECONDS:
        ret, frame = cap.read()
        if not ret:
            break

        display_frame = frame.copy()
        frame_candidates = {}   # plate -> best candidate seen this frame

        results = model(frame, conf=0.20, verbose=False)

        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                continue

            for idx, box in enumerate(r.boxes.xyxy):
                x1, y1, x2, y2 = map(int, box)

                # Subtle box on the live feed - useful feedback, not a debug overlay
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (37, 99, 235), 2)

                pad = 12
                h_f, w_f = frame.shape[:2]
                x1p = max(0, x1 - pad);  y1p = max(0, y1 - pad)
                x2p = min(w_f, x2 + pad); y2p = min(h_f, y2 + pad)
                plate_crop = frame[y1p:y2p, x1p:x2p]

                if plate_crop.size == 0:
                    continue

                ocr_inputs = [plate_crop]
                proc = preprocess_plate(plate_crop)
                if proc is not None:
                    ocr_inputs.append(proc)

                for img_candidate in ocr_inputs:
                    ocr_out = reader.readtext(img_candidate, detail=1, paragraph=False)

                    # Assemble the text boxes into plate candidates. This is
                    # what recovers two-line plates ("MH12" + "AB1234") and
                    # look-alike characters (I/1, O/0, B/8) that a per-box
                    # regex could never match.
                    for cand in plate_ocr.extract_plates(ocr_out, min_conf=OCR_MIN_CONF):
                        prev = frame_candidates.get(cand["plate"])
                        if prev is None or cand["score"] > prev["score"]:
                            frame_candidates[cand["plate"]] = cand

        # One vote per plate per frame
        for plate_text, cand in frame_candidates.items():
            slot = plate_votes.setdefault(plate_text, {"votes": 0, "score": 0.0})
            slot["votes"] += 1
            slot["score"] = max(slot["score"], cand["score"])

        best_plate = max(
            plate_votes.items(),
            key=lambda kv: (kv[1]["votes"], kv[1]["score"]),
            default=None
        )

        if best_plate and best_plate[1]["votes"] >= VOTE_THRESHOLD:
            st.session_state.detected_plate = best_plate[0]
            try:
                cap.release()
            except Exception:
                pass
            return "locked"

        frame_ph.image(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))

    try:
        cap.release()
    except Exception:
        pass

    # Never throw away a near miss: a plate seen in only one frame is
    # offered for confirmation instead of being silently dropped.
    near_miss = max(
        plate_votes.items(),
        key=lambda kv: (kv[1]["votes"], kv[1]["score"]),
        default=None
    )
    if near_miss:
        st.session_state.pending_plate = near_miss[0]
        return "near_miss"

    return "none"


# ════════════════════════════════════════════════════════════════
# PAGE: SCAN (the terminal)
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "Scan":

    _, center, _ = st.columns([1, 3, 1])
    with center:
        components.welcome_card()

        _, btn_col, _ = st.columns([1, 1.4, 1])
        with btn_col:
            start = st.button("Scan Vehicle", type="primary",
                              width="stretch", key="start_scan")

        camera_slot = st.empty()

        if start:
            frame_ph = components.camera_stage(camera_slot)
            outcome = run_scan(frame_ph)
            camera_slot.empty()

            if outcome == "near_miss":
                components.info_card(
                    "Almost there",
                    f"We read {components.plate_pretty(st.session_state.pending_plate)} "
                    "- please confirm it below.",
                )
            elif outcome == "none":
                components.no_plate_card()

        # Manual entry fallback - also confirms a low-confidence scan.
        # A widget's session_state value can't be reassigned after the widget
        # has been instantiated in the same run, so a completed transaction
        # requests the clear here (before manual_entry_block creates the
        # text_input below) instead of clearing it directly at the end.
        if st.session_state.pop("_clear_manual_input", False):
            st.session_state.manual_input = ""
        prefill = st.session_state.detected_plate or st.session_state.pending_plate
        if prefill and st.session_state.get("manual_input", "") != prefill:
            st.session_state.manual_input = prefill
        submitted, manual_value = components.manual_entry_block(prefill)
        if submitted:
            st.session_state.detected_plate = manual_value.upper().strip()
            st.session_state.pending_plate = ""

        plate = st.session_state.detected_plate

        # De-dupe guard: ignore a re-read of the same plate moments after it
        # was processed, so it can't be mistaken for an exit right after entry.
        last_plate, last_ts = st.session_state.last_processed
        if plate and plate == last_plate and time.time() - last_ts < REPROCESS_COOLDOWN:
            components.duplicate_scan_card(plate)
            plate = ""
            st.session_state.detected_plate = ""

        if plate:
            components.plate_detected_banner(plate)
            now = datetime.now()

            if not st.session_state.db_ok:
                components.service_unavailable_card()
            else:
                st.session_state.last_processed = (plate, time.time())

                try:
                    active = db.get_active_session(plate)
                except Exception:
                    active = None
                    components.processing_failed_card()
                else:
                    # ── ENTRY ──────────────────────────────────
                    if active is None:
                        try:
                            result = db.register_vehicle_entry(plate, "CAR")
                        except Exception:
                            result = {"success": False}

                        if result.get("success"):
                            components.entry_success_card(
                                plate, result["slot_number"], now.strftime("%I:%M %p")
                            )
                        else:
                            components.processing_failed_card()

                    # ── EXIT ───────────────────────────────────
                    else:
                        entry_time = active["entry_time"]
                        exit_time  = now

                        try:
                            fare = db.call_c_fare_calculator(
                                entry_time.timestamp(), exit_time.timestamp()
                            )
                        except Exception:
                            # Fallback: simple calculation, matches the C
                            # calculator's base-rate-only behaviour
                            dur_sec = max(60, int((exit_time - entry_time).total_seconds()))
                            fare = {
                                "status": "ACTIVE",
                                "total_duration": dur_sec,
                                "base_minutes": dur_sec,
                                "base_rate": 0.67,
                                "base_amount": round(dur_sec * 0.67, 2),
                                "peak_minutes": 0,
                                "peak_surcharge": 0.80,
                                "peak_amount": 0.0,
                                "total_amount": round(dur_sec * 0.67, 2),
                                "is_rush_hour": 0
                            }

                        try:
                            exit_result = db.process_vehicle_exit(plate, fare, "CASH")
                        except Exception:
                            exit_result = {"success": False}

                        # NOTE: the C calculator's "TOTAL_DURATION" is actually the raw
                        # elapsed seconds between entry and exit (its fare math treats
                        # 1 elapsed second as 1 billable "minute" - a deliberate demo
                        # shortcut in parkinglot.c, unchanged here). That makes it the
                        # correct input for a real elapsed-time display.
                        components.exit_billing_card(
                            plate,
                            components.format_duration(fare["total_duration"]),
                            fare["base_amount"], fare["peak_amount"],
                            fare["total_amount"], bool(fare["is_rush_hour"]),
                        )

                        if not exit_result.get("success"):
                            st.markdown(
                                "<div class='pk-footnote'>Please show this screen "
                                "to the parking attendant.</div>",
                                unsafe_allow_html=True,
                            )

                        if os.path.exists("payment_qr.png"):
                            _, qcol, _ = st.columns([1, 1, 1])
                            with qcol:
                                st.markdown(
                                    "<div class='pk-footnote' style='margin-top:1rem;'>"
                                    "Scan to pay</div>", unsafe_allow_html=True
                                )
                                st.image("payment_qr.png", width=180)

            st.session_state.detected_plate = ""
            st.session_state.pending_plate = ""
            st.session_state._clear_manual_input = True

# ════════════════════════════════════════════════════════════════
# PAGE: AVAILABILITY
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Availability":

    _, center, _ = st.columns([1, 3, 1])
    with center:
        try:
            summary = db.get_slot_summary()
            slots = db.get_all_slots()
            components.availability_summary(
                int(summary.get("available", 0) or 0), int(summary.get("total", 0) or 0)
            )
            components.slot_grid_by_zone(slots)
        except Exception:
            components.info_card(
                "Availability is temporarily unavailable",
                "Please check with the parking attendant.",
                tone="error",
            )

# ════════════════════════════════════════════════════════════════
# PAGE: OPERATOR  (staff-facing: records, live sessions, revenue)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Operator":

    st.markdown("<div class='pk-eyebrow' style='margin-top:0.5rem;'>Operator view</div>",
                unsafe_allow_html=True)

    tab_overview, tab_records, tab_reference = st.tabs(["Overview", "Records", "Reference"])

    with tab_overview:
        try:
            summary = db.get_slot_summary()
            active_list = db.get_active_sessions()
            revenue_data = db.get_daily_revenue()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Slots",     summary.get("total",    30))
            col2.metric("Available",       summary.get("available", 0))
            col3.metric("Occupied",        summary.get("occupied",  0))
            col4.metric("Active Sessions", len(active_list))

            st.markdown("---")
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("**Currently Parked**")
                if active_list:
                    df = pd.DataFrame(active_list)[["number_plate", "slot_number", "entry_time", "minutes_parked"]]
                    df.columns = ["Plate", "Slot", "Entry", "Minutes Parked"]
                    st.dataframe(df, width="stretch")
                else:
                    st.caption("No vehicles currently parked.")

            with col_right:
                st.markdown("**Daily Revenue**")
                if revenue_data:
                    df = pd.DataFrame(revenue_data)
                    df["revenue_date"] = pd.to_datetime(df["revenue_date"]).dt.strftime("%d %b")
                    df = df.rename(columns={
                        "revenue_date":       "Date",
                        "total_sessions":     "Sessions",
                        "total_revenue":      "Revenue (₹)",
                        "rush_hour_sessions": "Rush Hour"
                    })
                    st.dataframe(df[["Date", "Sessions", "Revenue (₹)", "Rush Hour"]],
                                width="stretch")
                else:
                    st.caption("No revenue data yet.")

            if revenue_data:
                st.markdown("---")
                st.markdown("**Revenue Trend**")
                chart_df = pd.DataFrame(revenue_data)
                chart_df["revenue_date"] = pd.to_datetime(chart_df["revenue_date"])
                chart_df = chart_df.sort_values("revenue_date")
                st.bar_chart(chart_df.set_index("revenue_date")["total_revenue"])

        except Exception as e:
            st.error(f"Dashboard data unavailable: {e}")

    with tab_records:
        sub1, sub2, sub3 = st.tabs(["All Records", "Active Sessions", "Search Vehicle"])

        with sub1:
            try:
                records = db.get_parking_records(200)
                if records:
                    df = pd.DataFrame(records)
                    st.dataframe(df, width="stretch")
                    st.caption(f"Total records: {len(df)}")
                else:
                    st.caption("No records yet.")
            except Exception as e:
                st.error(f"DB error: {e}")

        with sub2:
            try:
                active_list = db.get_active_sessions()
                if active_list:
                    st.dataframe(pd.DataFrame(active_list), width="stretch")
                else:
                    st.caption("No vehicles currently parked.")
            except Exception as e:
                st.error(f"DB error: {e}")

        with sub3:
            search_plate = st.text_input("Enter Number Plate", placeholder="MH12AB1234")
            if st.button("Search") and search_plate:
                try:
                    results = db.search_vehicle(search_plate)
                    if results:
                        st.dataframe(pd.DataFrame(results), width="stretch")
                    else:
                        st.caption("No records found for this vehicle.")
                except Exception as e:
                    st.error(f"DB error: {e}")

    with tab_reference:
        if os.path.exists("parking_map.png"):
            st.image("parking_map.png", width="stretch")
        else:
            st.caption("No site map on file.")
        st.markdown("---")
        st.caption(
            f"Database: {'Connected' if st.session_state.db_ok else 'Unavailable - ' + str(st.session_state.db_info)}"
        )
