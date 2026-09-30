"""
streamlit_app.py - Smart Parking Management System
Integrated with MySQL ParkingLot database.
OCR + YOLO for plate recognition, C for fare calculation, MySQL for persistence.
"""

import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import pandas as pd
from datetime import datetime

# MySQL integration
import db

st.set_page_config(page_title="Smart Parking", layout="wide")

# ── Session state ────────────────────────────────────────────────
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""
if "page" not in st.session_state:
    st.session_state.page = "Scan"
if "db_ok" not in st.session_state:
    ok, info = db.test_connection()
    st.session_state.db_ok   = ok
    st.session_state.db_info = info

# ── Header ───────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;'>🚗 Smart Parking System</h1>", unsafe_allow_html=True)

# DB status badge
if st.session_state.db_ok:
    st.markdown(
        "<div style='text-align:center;color:#22c55e;font-size:13px;'>🟢 MySQL Connected (ParkingLot @ localhost:3306)</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"<div style='text-align:center;color:#ef4444;font-size:13px;'>🔴 MySQL Error: {st.session_state.db_info}</div>",
        unsafe_allow_html=True
    )

# ── Navigation ───────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📷 Scan", use_container_width=True):
        st.session_state.page = "Scan"
with c2:
    if st.button("📋 Records", use_container_width=True):
        st.session_state.page = "Records"
with c3:
    if st.button("🅿 Parking Map", use_container_width=True):
        st.session_state.page = "Map"
with c4:
    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.page = "Dashboard"

st.markdown("---")

# ── Models ───────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    return YOLO("best.pt"), easyocr.Reader(['en'])

model, reader = load_models()

patterns = [
    r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}",
    r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}"
]

# ════════════════════════════════════════════════════════════════
# PAGE: SCAN
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "Scan":

    st.subheader("Live Scan — OCR Number Plate Recognition")

    col_cam, col_info = st.columns([2, 1])

    with col_cam:
        start = st.button("▶ Start Camera")
        stop  = st.button("⏹ Stop Camera")
        frame_placeholder = st.empty()
        status_placeholder = st.empty()

    with col_info:
        info_box = st.empty()

    def preprocess_plate(img):
        """Upscale, sharpen, and convert plate crop for better OCR accuracy."""
        if img is None or img.size == 0:
            return None
        h, w = img.shape[:2]
        # Upscale small crops
        scale = max(1, int(100 / max(h, 1)))
        if scale > 1:
            img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        # Slight blur to reduce noise, then sharpen
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
        # Back to BGR for EasyOCR
        return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    if start:
        cap = cv2.VideoCapture(0)

        # Warm-up: discard first 15 frames so camera auto-exposure settles
        for _ in range(15):
            cap.read()

        # Accumulate votes: plate_text -> count
        # Accept after 2 matching reads (robust, but not so strict it never triggers)
        plate_votes = {}
        VOTE_THRESHOLD = 2
        MAX_FRAMES = 400   # ~40 seconds at ~10 fps

        for frame_num in range(MAX_FRAMES):
            if stop:
                break

            ret, frame = cap.read()
            if not ret:
                status_placeholder.warning("Camera read failed.")
                break

            display_frame = frame.copy()
            ocr_status_texts = []   # human-readable OCR reads this frame

            results = model(frame, conf=0.20, verbose=False)
            yolo_detected = False

            for r in results:
                if r.boxes is None or len(r.boxes) == 0:
                    continue

                for idx, box in enumerate(r.boxes.xyxy):
                    x1, y1, x2, y2 = map(int, box)
                    conf_score = float(r.boxes.conf[idx])
                    yolo_detected = True

                    # Draw green box + label on live feed
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Plate {conf_score:.2f}",
                                (x1, max(14, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # Crop with generous padding
                    pad = 12
                    h_f, w_f = frame.shape[:2]
                    x1p = max(0, x1 - pad);  y1p = max(0, y1 - pad)
                    x2p = min(w_f, x2 + pad); y2p = min(h_f, y2 + pad)
                    plate_crop = frame[y1p:y2p, x1p:x2p]

                    if plate_crop.size == 0:
                        continue

                    # Run OCR on BOTH raw crop and preprocessed crop
                    candidates = [plate_crop]
                    proc = preprocess_plate(plate_crop)
                    if proc is not None:
                        candidates.append(proc)

                    for img_candidate in candidates:
                        ocr_out = reader.readtext(img_candidate, detail=1, paragraph=False)

                        for t in ocr_out:
                            txt  = t[1] if len(t) > 1 else ""
                            oconf = t[2] if len(t) > 2 else 0.0

                            # Accept any read with confidence >= 0.1 (very permissive)
                            if oconf < 0.1:
                                continue

                            raw = re.sub(r'[^A-Z0-9]', '', txt.upper())
                            ocr_status_texts.append(f'"{raw}"({oconf:.2f})')

                            for p in patterns:
                                for m in re.findall(p, raw):
                                    plate_votes[m] = plate_votes.get(m, 0) + 1
                                    if plate_votes[m] >= VOTE_THRESHOLD:
                                        # Lock the plate, stop camera, done
                                        st.session_state.detected_plate = m
                                        cap.release()
                                        # Show final frozen frame with box
                                        frame_placeholder.image(
                                            cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                                        )
                                        status_placeholder.success(
                                            f"✅ Plate confirmed: **{m}**"
                                        )
                                        break
                            if st.session_state.detected_plate:
                                break
                        if st.session_state.detected_plate:
                            break
                    if st.session_state.detected_plate:
                        break
                if st.session_state.detected_plate:
                    break

            if st.session_state.detected_plate:
                break

            # Update live feed every frame
            frame_placeholder.image(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))

            # Status bar — show what OCR is actually reading so user can debug
            if yolo_detected and ocr_status_texts:
                pending = ", ".join(
                    f"{k}({v}/{VOTE_THRESHOLD})" for k, v in plate_votes.items()
                )
                status_placeholder.info(
                    f"🔍 YOLO✅ OCR reads: {' | '.join(ocr_status_texts[-3:])}  "
                    f"{'  Votes: ' + pending if plate_votes else ''}"
                )
            elif yolo_detected:
                status_placeholder.warning(
                    f"🟡 Plate box found — OCR couldn't read text (frame {frame_num + 1}). "
                    "Move plate closer / improve lighting."
                )
            else:
                status_placeholder.caption(
                    f"📷 Scanning frame {frame_num + 1} — point plate at camera"
                )

        # Always release camera after loop ends
        try:
            cap.release()
        except Exception:
            pass

        if not st.session_state.detected_plate:
            status_placeholder.warning("⚠️ No plate detected. Try better lighting, hold the plate steady, or enter manually below.")

    # Manual plate input (for testing without camera)
    with col_info:
        st.markdown("**Or enter plate manually:**")
        manual_plate = st.text_input("Number Plate", value=st.session_state.detected_plate,
                                     placeholder="MH12AB1234", key="manual_input")
        if st.button("Process Plate"):
            st.session_state.detected_plate = manual_plate.upper().strip()

    plate = st.session_state.detected_plate

    if plate:
        with col_info:
            st.success(f"✅ Detected: **{plate}**")
            now = datetime.now()

            if not st.session_state.db_ok:
                st.error("Database not connected. Cannot process.")
            else:
                # Check if vehicle has an active session
                active = db.get_active_session(plate)

                # ── ENTRY ──────────────────────────────────────
                if active is None:
                    st.info("🟢 Vehicle not parked — processing ENTRY")
                    result = db.register_vehicle_entry(plate, "CAR")

                    if result["success"]:
                        st.success(f"🚀 Entry Recorded!")
                        st.info(f"🅿 Slot Assigned: **{result['slot_number']}**")
                        st.caption(f"Session ID: {result['session_id']}")
                    else:
                        st.error(f"Entry failed: {result['message']}")

                # ── EXIT ───────────────────────────────────────
                else:
                    st.warning("🔴 Vehicle IS parked — processing EXIT")
                    entry_time = active["entry_time"]
                    exit_time  = now

                    st.caption(f"Slot: {active['slot_number']} | Entry: {entry_time.strftime('%H:%M:%S')}")

                    # Call C fare calculator
                    entry_ts = entry_time.timestamp()
                    exit_ts  = exit_time.timestamp()

                    try:
                        fare = db.call_c_fare_calculator(entry_ts, exit_ts)
                        fare_ok = True
                    except Exception as e:
                        st.warning(f"C calculator error ({e}), using fallback")
                        # Fallback: simple calculation
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
                        fare_ok = False

                    # Store in MySQL
                    exit_result = db.process_vehicle_exit(plate, fare, "CASH")

                    if exit_result["success"]:
                        st.success("🚪 Exit Recorded in MySQL!")
                    else:
                        st.error(f"Exit DB error: {exit_result['message']}")

                    # ── Receipt ────────────────────────────────
                    st.markdown("---")
                    st.markdown("## 🧾 Parking Receipt")

                    receipt = pd.DataFrame({
                        "Details": [
                            "Vehicle Number", "Slot",
                            "Entry Time", "Exit Time", "Duration",
                            "Base Minutes", "Base Rate", "Base Amount",
                            "Peak Minutes", "Peak Rate", "Peak Amount",
                            "Rush Hour"
                        ],
                        "Value": [
                            plate, active["slot_number"],
                            entry_time.strftime("%H:%M:%S"),
                            exit_time.strftime("%H:%M:%S"),
                            f"{fare['total_duration']} min",
                            str(fare["base_minutes"]),
                            f"₹{fare['base_rate']:.2f}/min",
                            f"₹{fare['base_amount']:.2f}",
                            str(fare["peak_minutes"]),
                            f"₹{fare['peak_surcharge']:.2f}/min",
                            f"₹{fare['peak_amount']:.2f}",
                            "✅ Yes" if fare["is_rush_hour"] else "❌ No"
                        ]
                    })
                    st.table(receipt)

                    st.markdown(
                        f"<h2 style='text-align:center;color:#22c55e;'>Total Fare: ₹{fare['total_amount']:.2f}</h2>",
                        unsafe_allow_html=True
                    )

                    if fare["is_rush_hour"]:
                        st.markdown(
                            "<p style='text-align:center;color:#f59e0b;'>⚡ Rush Hour Pricing Applied</p>",
                            unsafe_allow_html=True
                        )

                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if os.path.exists("payment_qr.png"):
                            st.markdown("### Scan to Pay")
                            st.image("payment_qr.png", width=200)

        st.session_state.detected_plate = ""

# ════════════════════════════════════════════════════════════════
# PAGE: RECORDS
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Records":
    st.subheader("📋 Parking Records — MySQL Database")

    tab1, tab2, tab3 = st.tabs(["All Records", "Active Sessions", "Search Vehicle"])

    with tab1:
        try:
            records = db.get_parking_records(200)
            if records:
                df = pd.DataFrame(records)
                st.dataframe(df, use_container_width=True)
                st.caption(f"Total records: {len(df)}")
            else:
                st.info("No records yet.")
        except Exception as e:
            st.error(f"DB error: {e}")

    with tab2:
        try:
            active_list = db.get_active_sessions()
            if active_list:
                df = pd.DataFrame(active_list)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No vehicles currently parked.")
        except Exception as e:
            st.error(f"DB error: {e}")

    with tab3:
        search_plate = st.text_input("Enter Number Plate", placeholder="MH12AB1234")
        if st.button("Search") and search_plate:
            try:
                results = db.search_vehicle(search_plate)
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True)
                else:
                    st.warning("No records found for this vehicle.")
            except Exception as e:
                st.error(f"DB error: {e}")

# ════════════════════════════════════════════════════════════════
# PAGE: PARKING MAP
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Map":
    st.subheader("🅿 Parking Map — Live from MySQL")

    if os.path.exists("parking_map.png"):
        st.image("parking_map.png", use_container_width=True)

    st.markdown("---")

    try:
        slots = db.get_all_slots()
        summary = db.get_slot_summary()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Slots",     summary.get("total",     30))
        c2.metric("Available",       summary.get("available", 0), delta=None)
        c3.metric("Occupied",        summary.get("occupied",  0))

        st.markdown("---")
        st.markdown("### Slot Grid")

        for i in range(0, len(slots), 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(slots):
                    s = slots[i + j]
                    label = f"Slot {s['slot_number']}\n({s['zone']}{s['floor']})"
                    if s["status"] == "AVAILABLE":
                        cols[j].success(label)
                    elif s["status"] == "OCCUPIED":
                        cols[j].error(label)
                    else:
                        cols[j].warning(label + "\n[MNT]")
    except Exception as e:
        st.error(f"DB error: {e}")

# ════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Dashboard":
    st.subheader("📊 Dashboard — Analytics from MySQL")

    try:
        summary = db.get_slot_summary()
        active_list = db.get_active_sessions()
        revenue_data = db.get_daily_revenue()

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Slots",     summary.get("total",    30))
        col2.metric("Available",       summary.get("available", 0))
        col3.metric("Occupied",        summary.get("occupied",  0))
        col4.metric("Active Sessions", len(active_list))

        st.markdown("---")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 🚗 Currently Parked")
            if active_list:
                df = pd.DataFrame(active_list)[["number_plate","slot_number","entry_time","minutes_parked"]]
                df.columns = ["Plate","Slot","Entry","Minutes Parked"]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No vehicles currently parked.")

        with col_right:
            st.markdown("### 💰 Daily Revenue")
            if revenue_data:
                df = pd.DataFrame(revenue_data)
                df["revenue_date"] = pd.to_datetime(df["revenue_date"]).dt.strftime("%d %b")
                df = df.rename(columns={
                    "revenue_date":      "Date",
                    "total_sessions":    "Sessions",
                    "total_revenue":     "Revenue (₹)",
                    "rush_hour_sessions":"Rush Hour"
                })
                st.dataframe(df[["Date","Sessions","Revenue (₹)","Rush Hour"]], use_container_width=True)
            else:
                st.info("No revenue data yet.")

        st.markdown("---")
        st.markdown("### 📈 Revenue Chart")
        if revenue_data:
            chart_df = pd.DataFrame(revenue_data)
            chart_df["revenue_date"] = pd.to_datetime(chart_df["revenue_date"])
            chart_df = chart_df.sort_values("revenue_date")
            st.bar_chart(chart_df.set_index("revenue_date")["total_revenue"])

    except Exception as e:
        st.error(f"Dashboard DB error: {e}")
