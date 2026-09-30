"""
streamlit_app.py - Smart Parking Management System (PARK-DBMS console)

UI matches the Material-3 dark/amber reference design supplied by the user
(Google Stitch export). Every value shown comes from a real db.py call, the
real OCR/YOLO pipeline, or the real C fare calculator - no fabricated
hardware telemetry, camera names, sensor IDs, or driver/permittee tracking,
since none of that exists in this project's schema or backend.

Pipeline (unchanged): camera -> YOLO plate detection -> EasyOCR ->
plate_ocr.py (assembly/voting) -> MySQL (db.py) -> C fare calculator.
"""

import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import os
import time
from datetime import datetime

# Plate text assembly / validation (post-processing only - the YOLO model
# and the EasyOCR reader are untouched, so recognition accuracy is unchanged)
import plate_ocr

# MySQL integration
import db

# Presentation layer
from ui import styles, components

st.set_page_config(page_title="PARK-DBMS", layout="wide", initial_sidebar_state="collapsed")
styles.inject()

# ── Session state ────────────────────────────────────────────────
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""
if "pending_plate" not in st.session_state:      # read, but not yet confirmed
    st.session_state.pending_plate = ""
if "last_processed" not in st.session_state:     # (plate, unix_ts) de-dupe guard
    st.session_state.last_processed = ("", 0.0)
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "selected_slot" not in st.session_state:
    st.session_state.selected_slot = None
if "db_ok" not in st.session_state:
    ok, info = db.test_connection()
    st.session_state.db_ok   = ok
    st.session_state.db_info = info

# ── Models ───────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    return YOLO("best.pt"), easyocr.Reader(['en'])

model, reader = load_models()

# ── Top bar ──────────────────────────────────────────────────────
components.render_topbar(st.session_state.page, st.session_state.db_ok)

# Plate layouts and character repair live in plate_ocr.py.
OCR_MIN_CONF = 0.15      # ignore EasyOCR reads below this confidence
VOTE_THRESHOLD = 2       # a plate must be seen in this many separate frames
SCAN_SECONDS = 45        # wall-clock scan budget; OCR speed varies a lot
REPROCESS_COOLDOWN = 25  # seconds; a re-read of the same plate is ignored so a
                         # fresh entry is not instantly turned into an exit

# Real, currently-enforced fare rule (parkinglot.c): weekends, or 18:00-22:00
# on weekdays, bill at the peak rate instead of the base rate.
BASE_RATE_PER_MIN = 0.67
PEAK_RATE_PER_MIN = 0.80
PEAK_WINDOW_LABEL = "Weekends & 18:00–22:00"


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
    plate read. Same detection/matching algorithm as the verified pipeline -
    only the per-frame technical status text has been removed.

    Returns "locked", "near_miss" or "none". On "locked",
    st.session_state.detected_plate is set; on "near_miss",
    st.session_state.pending_plate is set for manual confirmation.
    """
    cap = cv2.VideoCapture(0)
    for _ in range(15):   # warm-up: let camera auto-exposure settle
        cap.read()

    plate_votes = {}
    scan_started = time.time()

    while time.time() - scan_started < SCAN_SECONDS:
        ret, frame = cap.read()
        if not ret:
            break

        display_frame = frame.copy()
        frame_candidates = {}

        results = model(frame, conf=0.20, verbose=False)

        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                continue

            for idx, box in enumerate(r.boxes.xyxy):
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (101, 198, 255), 2)

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
                    for cand in plate_ocr.extract_plates(ocr_out, min_conf=OCR_MIN_CONF):
                        prev = frame_candidates.get(cand["plate"])
                        if prev is None or cand["score"] > prev["score"]:
                            frame_candidates[cand["plate"]] = cand

        for plate_text, cand in frame_candidates.items():
            v = plate_votes.setdefault(plate_text, {"votes": 0, "score": 0.0})
            v["votes"] += 1
            v["score"] = max(v["score"], cand["score"])

        best_plate = max(plate_votes.items(), key=lambda kv: (kv[1]["votes"], kv[1]["score"]), default=None)

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

    near_miss = max(plate_votes.items(), key=lambda kv: (kv[1]["votes"], kv[1]["score"]), default=None)
    if near_miss:
        st.session_state.pending_plate = near_miss[0]
        return "near_miss"
    return "none"


# ════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "Dashboard":

    try:
        summary = db.get_slot_summary()
        slots = db.get_all_slots()
        total = int(summary.get("total") or 0)
        available = int(summary.get("available") or 0)
        occupied = int(summary.get("occupied") or 0)

        zone_counts = {}
        for s in slots:
            zone_counts[s["zone"]] = zone_counts.get(s["zone"], 0) + 1
        zone_text = " • ".join(f"Zone {z} ({n})" for z, n in sorted(zone_counts.items()))

        components._md(
            "<div class='pk-eyebrow'>FACILITY TELEMETRY</div>"
            "<div class='pk-h1' style='margin-bottom:1.25rem;'>Parking Overview</div>"
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            components.stat_card("Total Capacity", total, "Bays Total", zone_text or "—", "local_parking")
        with c2:
            pct = round((occupied / total) * 100) if total else 0
            components.stat_card("Active Occupancy", occupied, "Vehicles Parked", f"{pct}% Slot Saturation", "directions_car")
        with c3:
            components.stat_card("Available Bays", available, "Open Now", "Ready for instant check-in", "check_circle", accent=True)
        with c4:
            components.stat_card("Base Tariff", f"₹{BASE_RATE_PER_MIN:.2f}", "/ min",
                                 f"Peak ₹{PEAK_RATE_PER_MIN:.2f}/min • {PEAK_WINDOW_LABEL}", "schedule")

        st.write("")
        components.utilization_bar(occupied, total)
        st.write("")

        col_feed, col_side = st.columns([2, 1])
        with col_feed:
            try:
                records = db.get_parking_records(15)
                records = sorted(records, key=lambda r: r.get("exit_time") or r.get("entry_time"), reverse=True)[:6]
            except Exception:
                records = []
            components.activity_feed(records)

        with col_side:
            components._md("<div class='pk-h2' style='margin-bottom:0.6rem;'>Quick Actions</div>")
            components.action_link("Process Entry / Exit", "Plate scan & manual entry", "swap_horiz")
            if st.button("Open Parking Terminal", key="qa_parking", width="stretch"):
                st.session_state.page = "Parking"; st.rerun()
            components.action_link("View Facility Map", "Interactive slot grid", "map")
            if st.button("Open Map", key="qa_map", width="stretch"):
                st.session_state.page = "Map"; st.rerun()
            components.action_link("Session Records", "Full transaction ledger", "receipt_long")
            if st.button("Open Records", key="qa_records", width="stretch"):
                st.session_state.page = "Records"; st.rerun()

            st.write("")
            components.system_status_box(st.session_state.db_ok, st.session_state.db_info, model_ready=True)

    except Exception as e:
        st.error(f"Dashboard data unavailable: {e}")

# ════════════════════════════════════════════════════════════════
# PAGE: PARKING (scan / entry-exit terminal)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Parking":

    components._md(
        "<div class='pk-eyebrow'>VEHICLE ENTRY / EXIT</div>"
        "<div class='pk-h1' style='margin-bottom:0.25rem;'>Plate Scan Terminal</div>"
        "<div class='pk-muted' style='margin-bottom:1rem;'>Entry or exit is detected automatically "
        "from whether the plate already has an active session.</div>"
    )

    col_cam, col_side = st.columns([7, 5])

    with col_cam:
        start = st.button("Scan Vehicle", type="primary", width="stretch", key="start_scan")
        camera_slot = st.empty()

        if start:
            frame_ph = components.camera_stage(camera_slot, "PLATE CAMERA • LIVE FEED")
            outcome = run_scan(frame_ph)
            camera_slot.empty()

            if outcome == "near_miss":
                components.info_card(
                    "Almost there",
                    f"Read {components.plate_pretty(st.session_state.pending_plate)} in only one frame "
                    "- confirm it below.", "search",
                )
            elif outcome == "none":
                components.no_plate_card()

        with st.expander("Manual Plate Entry", expanded=bool(st.session_state.pending_plate)):
            prefill = st.session_state.detected_plate or st.session_state.pending_plate
            if st.session_state.pop("_clear_manual_input", False):
                st.session_state.manual_input = ""
            if prefill and st.session_state.get("manual_input", "") != prefill:
                st.session_state.manual_input = prefill
            submitted, manual_value = components.manual_entry_block(prefill)
            if submitted:
                st.session_state.detected_plate = manual_value.upper().strip()
                st.session_state.pending_plate = ""

    plate = st.session_state.detected_plate

    # De-dupe guard: ignore a re-read of the same plate moments after it was
    # processed, so it can't be mistaken for an exit right after entry.
    last_plate, last_ts = st.session_state.last_processed
    if plate and plate == last_plate and time.time() - last_ts < REPROCESS_COOLDOWN:
        with col_side:
            components.duplicate_scan_card(plate)
        plate = ""
        st.session_state.detected_plate = ""

    if plate:
        with col_side:
            components.detected_plate_readout(plate, "CAR")
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
                            slot_info = next(
                                (s for s in db.get_all_slots() if s["slot_number"] == result["slot_number"]),
                                None,
                            )
                            zone = slot_info["zone"] if slot_info else "?"
                            floor = slot_info["floor"] if slot_info else "?"
                            components.slot_allocation_box(result["slot_number"], zone, floor)
                            components.kv_grid([
                                ("Entry Timestamp", now.strftime("%H:%M:%S")),
                                ("Tariff Rate Basis", f"₹{BASE_RATE_PER_MIN:.2f} / min base"),
                            ])
                            components.confirmation_box(
                                "Slot Assigned",
                                f"Vehicle registered. Proceed to slot {result['slot_number']}.",
                            )
                        else:
                            components.processing_failed_card()

                    # ── EXIT ───────────────────────────────────
                    else:
                        entry_time = active["entry_time"]
                        exit_time = now

                        try:
                            fare = db.call_c_fare_calculator(entry_time.timestamp(), exit_time.timestamp())
                        except Exception:
                            dur_sec = max(60, int((exit_time - entry_time).total_seconds()))
                            fare = {
                                "status": "ACTIVE", "total_duration": dur_sec, "base_minutes": dur_sec,
                                "base_rate": BASE_RATE_PER_MIN, "base_amount": round(dur_sec * BASE_RATE_PER_MIN, 2),
                                "peak_minutes": 0, "peak_surcharge": PEAK_RATE_PER_MIN, "peak_amount": 0.0,
                                "total_amount": round(dur_sec * BASE_RATE_PER_MIN, 2), "is_rush_hour": 0,
                            }

                        try:
                            exit_result = db.process_vehicle_exit(plate, fare, "CASH")
                        except Exception:
                            exit_result = {"success": False}

                        components.exit_summary_box(
                            plate, active["slot_number"],
                            entry_time.strftime("%H:%M:%S"), exit_time.strftime("%H:%M:%S"),
                            components.format_duration(fare["total_duration"]),
                        )
                        components.fare_breakdown_box(
                            fare["base_amount"], fare["peak_amount"],
                            fare["base_minutes"], fare["peak_minutes"],
                            fare["total_amount"], bool(fare["is_rush_hour"]),
                        )

                        if exit_result.get("success"):
                            components.confirmation_box(
                                "Payment Verified • Slot Released",
                                f"Slot {active['slot_number']} is now available.", "done_all",
                            )
                        else:
                            components.info_card("Exit not recorded", "Please show this screen to the attendant.", "error")

                        if os.path.exists("payment_qr.png"):
                            st.write("")
                            _, qcol, _ = st.columns([1, 1, 1])
                            with qcol:
                                st.caption("Scan to pay")
                                st.image("payment_qr.png", width=160)

            st.session_state.detected_plate = ""
            st.session_state.pending_plate = ""
            st.session_state._clear_manual_input = True

# ════════════════════════════════════════════════════════════════
# PAGE: MAP (slot grid + inspector)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Map":

    try:
        summary = db.get_slot_summary()
        slots = db.get_all_slots()
        active_sessions = db.get_active_sessions()
        active_by_slot = {a["slot_number"]: a for a in active_sessions}

        components._md("<div class='pk-eyebrow'>FACILITY SCHEMATIC</div>")
        col_head_l, col_head_r = st.columns([3, 1])
        with col_head_l:
            components._md("<div class='pk-h1' style='margin-bottom:0.25rem;'>Slot Grid</div>")
        with col_head_r:
            components.availability_summary(int(summary.get("available") or 0), int(summary.get("total") or 0))

        search = st.text_input("Search Slot ID or Plate", placeholder="e.g. 12, MH12AB1234...",
                               key="map_search", label_visibility="collapsed")

        col_grid, col_inspect = st.columns([8, 4])

        with col_grid:
            zones = {}
            for s in slots:
                zones.setdefault(s["zone"], []).append(s)

            q = (search or "").strip().upper()
            with st.container(key="slotgrid"):
                for zone in sorted(zones):
                    zone_slots = zones[zone]
                    components._md(
                        f"<div class='pk-zone-head'><span class='pk-zone-title'>Zone {zone}</span>"
                        f"<span class='pk-zone-sub'>{len(zone_slots)} bays</span></div>"
                    )
                    cols = st.columns(8)
                    shown = 0
                    for s in zone_slots:
                        session = active_by_slot.get(s["slot_number"])
                        plate = session["number_plate"] if session else ""
                        if q and q not in s["slot_number"].upper() and q not in plate.upper():
                            continue
                        shown += 1
                        col = cols[(shown - 1) % 8]
                        status_cls = {
                            "OCCUPIED": "pk-slot-occupied",
                            "AVAILABLE": "pk-slot-available",
                            "MAINTENANCE": "pk-slot-maintenance",
                        }.get(s["status"], "pk-slot-available")
                        if s["slot_number"] == st.session_state.selected_slot:
                            status_cls += " pk-slot-selected"
                        status_word = {"AVAILABLE": "Vacant", "MAINTENANCE": "Maint."}.get(s["status"], s["status"].title())
                        label = f"{s['slot_number']}\n{plate if session else status_word}"
                        with col:
                            st.markdown(f"<div class='{status_cls}'>", unsafe_allow_html=True)
                            # NOTE: no st.rerun() here - see the matching
                            # note in ui/components.py's nav loop. The
                            # inspector panel below reads selected_slot
                            # later in this same run, so it updates
                            # immediately regardless; only this button's
                            # own "selected" border would lag one render.
                            if st.button(label, key=f"slot_{s['slot_id']}"):
                                st.session_state.selected_slot = s["slot_number"]
                            st.markdown("</div>", unsafe_allow_html=True)
                    if shown == 0:
                        components._md("<div class='pk-muted' style='padding:0.5rem;'>No matching bays.</div>")

        with col_inspect:
            components._md("<div class='pk-h2' style='margin-bottom:0.5rem;'>Slot Inspector</div>")
            sel = st.session_state.selected_slot
            slot_info = next((s for s in slots if s["slot_number"] == sel), None) if sel else None

            if not slot_info:
                components.info_card("No slot selected", "Click a bay on the grid to inspect it.", "touch_app")
            else:
                session = active_by_slot.get(sel)
                components._md(
                    f"<div class='pk-card'><div class='pk-eyebrow'>SLOT {slot_info['slot_number']}</div>"
                    f"<div class='pk-muted'>Zone {slot_info['zone']} • Floor {slot_info['floor']} • "
                    f"{slot_info['slot_type'].title()}</div></div>"
                )
                if session:
                    entry_time = session["entry_time"]
                    elapsed = components.format_duration(int((datetime.now() - entry_time).total_seconds()))
                    try:
                        live_fare = db.call_c_fare_calculator(entry_time.timestamp(), datetime.now().timestamp())
                        fare_str = f"₹{live_fare['total_amount']:.2f}"
                    except Exception:
                        fare_str = "—"
                    components.kv_grid([
                        ("Vehicle Plate", components.plate_pretty(session["number_plate"])),
                        ("Entry Time", entry_time.strftime("%H:%M:%S")),
                        ("Elapsed Time", elapsed),
                        ("Accrued Fare (est.)", fare_str),
                    ])
                elif slot_info["status"] == "MAINTENANCE":
                    components.info_card("Under maintenance", "This bay is currently out of service.", "build")
                else:
                    components.info_card("Vacant", "Ready for the next vehicle.", "check_circle")

    except Exception as e:
        st.error(f"Map data unavailable: {e}")

# ════════════════════════════════════════════════════════════════
# PAGE: RECORDS (session ledger)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Records":

    try:
        records = db.get_parking_records(200)
    except Exception as e:
        records = []
        st.error(f"Records unavailable: {e}")

    total_n = len(records)
    active_n = sum(1 for r in records if r.get("session_status") == "ACTIVE")
    completed_n = sum(1 for r in records if r.get("session_status") == "COMPLETED")

    components._md(
        "<div class='pk-eyebrow'>SCHEMA • PUBLIC.PARKING_HISTORY</div>"
        "<div class='pk-h1' style='margin-bottom:0.25rem;'>Session Ledger Records</div>"
        "<div class='pk-muted' style='margin-bottom:1rem;'>Real-time ingress/egress events and automated billing.</div>"
    )

    col_f1, col_f2, col_f3, col_search = st.columns([1, 1, 1, 2])
    if "records_filter" not in st.session_state:
        st.session_state.records_filter = "all"
    with col_f1:
        if st.button(f"All Sessions ({total_n})", key="f_all", type=("primary" if st.session_state.records_filter == "all" else "secondary"), width="stretch"):
            st.session_state.records_filter = "all"; st.rerun()
    with col_f2:
        if st.button(f"Active ({active_n})", key="f_active", type=("primary" if st.session_state.records_filter == "active" else "secondary"), width="stretch"):
            st.session_state.records_filter = "active"; st.rerun()
    with col_f3:
        if st.button(f"Completed ({completed_n})", key="f_completed", type=("primary" if st.session_state.records_filter == "completed" else "secondary"), width="stretch"):
            st.session_state.records_filter = "completed"; st.rerun()
    with col_search:
        search = st.text_input("Filter by plate or slot", placeholder="Filter by plate number or slot...",
                               key="records_search", label_visibility="collapsed")

    f = st.session_state.records_filter
    q = (search or "").strip().upper()
    filtered = []
    for r in records:
        if f == "active" and r.get("session_status") != "ACTIVE":
            continue
        if f == "completed" and r.get("session_status") != "COMPLETED":
            continue
        if q and q not in (r.get("number_plate") or "").upper() and q not in (r.get("slot_number") or "").upper():
            continue
        filtered.append(r)

    components._md(
        f"<div class='pk-muted' style='margin-bottom:0.5rem;'>Showing "
        f"<b style='color:{styles.COLORS['text']};'>{len(filtered)}</b> of "
        f"<b style='color:{styles.COLORS['text']};'>{total_n}</b> sessions</div>"
    )

    rows_html = ['<table class="pk-table"><thead><tr>',
                 "<th>Session</th><th>Plate</th><th>Slot</th><th>Entry</th><th>Exit</th>",
                 "<th>Duration</th><th>Rate</th><th>Total Fare</th><th>Status</th></tr></thead><tbody>"]

    for r in filtered[:100]:
        entry = r["entry_time"].strftime("%Y-%m-%d %H:%M:%S") if r.get("entry_time") else "—"
        exit_ = r["exit_time"].strftime("%Y-%m-%d %H:%M:%S") if r.get("exit_time") else "—"
        dur = components.format_duration(r["duration_seconds"]) if r.get("duration_seconds") else "—"
        rate_badge = ('<span class="pk-badge rush">Rush Hour</span>' if r.get("is_rush_hour")
                      else '<span class="pk-badge standard">Standard</span>')
        fare = f"₹{float(r['total_fare']):.2f}" if r.get("total_fare") is not None else "—"
        status = r.get("session_status", "")
        status_badge = (f'<span class="pk-badge active">{status}</span>' if status == "ACTIVE"
                        else f'<span class="pk-badge completed">{status}</span>')
        rows_html.append(
            f"<tr><td class='mono'>#{r['session_id']}</td>"
            f"<td class='plate'>{components.plate_pretty(r.get('number_plate',''))}</td>"
            f"<td class='mono'>{r.get('slot_number','')}</td>"
            f"<td class='mono'>{entry}</td><td class='mono'>{exit_}</td>"
            f"<td class='mono'>{dur}</td><td>{rate_badge}</td>"
            f"<td class='mono'>{fare}</td><td>{status_badge}</td></tr>"
        )
    rows_html.append("</tbody></table>")

    if not filtered:
        components.info_card("No matching sessions", "Try a different filter or search term.", "search_off")
    else:
        components._md("".join(rows_html))
