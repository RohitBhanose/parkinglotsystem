import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import pandas as pd
import subprocess
from datetime import datetime

# ---------------- INIT ----------------
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""

# Load models
model = YOLO("best.pt")
reader = easyocr.Reader(['en'])

st.set_page_config(page_title="Smart Parking", layout="wide")
st.title("🚗 Smart Parking System")

start = st.button("▶ Scan Vehicle")
frame_placeholder = st.empty()

# Multiple patterns (MH + BH)
patterns = [
    r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}",   # MH12AB1234
    r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}"         # 22BH1234AA
]

# ---------------- DETECTION ----------------
if start:
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            st.error("Camera error")
            break

        results = model(frame, conf=0.3)

        for r in results:
            if r.boxes is not None:
                for box in r.boxes.xyxy:
                    x1, y1, x2, y2 = map(int, box)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    plate_img = frame[y1:y2, x1:x2]
                    text = reader.readtext(plate_img)

                    if text:
                        for t in text:
                            raw = t[-2].upper()
                            raw = re.sub(r'[^A-Z0-9]', '', raw)

                            for p in patterns:
                                match = re.findall(p, raw)
                                if match:
                                    st.session_state.detected_plate = match[0]
                                    break

                            if st.session_state.detected_plate:
                                break

        frame_placeholder.image(frame, channels="BGR")

        if st.session_state.detected_plate:
            cap.release()
            break

# ---------------- ENTRY / EXIT ----------------
plate = st.session_state.detected_plate

if plate:

    st.success("✅ Plate Detection Complete")
    st.markdown(f"### 🚗 {plate}")

    current_time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    file = "parking_data.csv"

    # Load or create CSV
    if os.path.exists(file):
        df = pd.read_csv(file)

        # Auto-fix old CSV (no Token column)
        if "Token" not in df.columns:
            df.insert(0, "Token", range(1, len(df) + 1))
            df.to_csv(file, index=False)

    else:
        df = pd.DataFrame(columns=["Token", "Number Plate", "Entry Time", "Exit Time"])

    # Normalize Exit Time
    df["Exit Time"] = df["Exit Time"].fillna("").astype(str).str.strip()

    # Generate next token safely
    if len(df) == 0 or df["Token"].isnull().all():
        next_token = 1
    else:
        next_token = int(df["Token"].max()) + 1

    # Find active entries
    active_rows = df[
        (df["Number Plate"] == plate) &
        (df["Exit Time"] == "")
    ]

    # ---------------- ENTRY ----------------
    if active_rows.empty:

        new_entry = {
            "Token": next_token,
            "Number Plate": plate,
            "Entry Time": current_time_str,
            "Exit Time": ""
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(file, index=False)

        st.success("🚀 ENTRY RECORDED")
        st.info(f"🎟 Token: {next_token}")
        st.info(f"⏱ Entry Time: {current_time_str}")

    # ---------------- EXIT ----------------
    else:
        idx = active_rows.index[-1]
        token = df.loc[idx, "Token"]

        entry_time_str = df.loc[idx, "Entry Time"]
        exit_time_str = current_time_str

        df.loc[idx, "Exit Time"] = exit_time_str
        df.to_csv(file, index=False)

        st.success("🚪 EXIT RECORDED")
        st.info(f"🎟 Token: {token}")
        st.info(f"⏱ Exit Time: {exit_time_str}")

        # Convert to timestamps
        entry_ts = int(datetime.strptime(entry_time_str, "%d/%m/%Y %H:%M:%S").timestamp())
        exit_ts = int(datetime.strptime(exit_time_str, "%d/%m/%Y %H:%M:%S").timestamp())

        # Call C billing program
        try:
            result = subprocess.check_output(
                ["parkinglot.exe", str(entry_ts), str(exit_ts)]
            ).decode()

            lines = result.split("\n")

            duration = next((l for l in lines if "Duration" in l), "")
            rate = next((l for l in lines if "Rate" in l), "")
            amount = next((l for l in lines if "Amount" in l), "")

            st.subheader("💰 Parking Bill")

            if duration:
                st.write(f"⏱ {duration}")
            if rate:
                st.write(f"💸 {rate}")
            if amount:
                st.success(f"✅ {amount}")

        except Exception as e:
            st.error("Billing system error")
            st.text(str(e))

    # Reset for next scan
    st.session_state.detected_plate = ""

# ---------------- DASHBOARD ----------------
st.divider()
st.subheader("📊 Parking Records")

if os.path.exists("parking_data.csv"):
    df = pd.read_csv("parking_data.csv")
    st.dataframe(df, use_container_width=True)