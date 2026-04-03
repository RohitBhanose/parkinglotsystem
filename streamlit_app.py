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

pattern = r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}"

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

                    plate = frame[y1:y2, x1:x2]
                    text = reader.readtext(plate)

                    if text:
                        raw = text[0][-2].replace(" ", "").upper()
                        match = re.findall(pattern, raw)

                        if match:
                            st.session_state.detected_plate = match[0]
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
    else:
        df = pd.DataFrame(columns=["Number Plate", "Entry Time", "Exit Time"])

    # 🔥 Normalize Exit Time (critical fix)
    df["Exit Time"] = df["Exit Time"].fillna("").astype(str).str.strip()

    # 🔥 Find active entry
    active_rows = df[
        (df["Number Plate"] == plate) &
        (df["Exit Time"] == "")
    ]

    # ---------------- ENTRY ----------------
    if active_rows.empty:

        new_entry = {
            "Number Plate": plate,
            "Entry Time": current_time_str,
            "Exit Time": ""
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(file, index=False)

        st.success("🚀 ENTRY RECORDED")
        st.info(f"⏱ Entry Time: {current_time_str}")

    # ---------------- EXIT ----------------
    else:
        idx = active_rows.index[-1]

        entry_time_str = df.loc[idx, "Entry Time"]
        exit_time_str = current_time_str

        df.loc[idx, "Exit Time"] = exit_time_str
        df.to_csv(file, index=False)

        st.success("🚪 EXIT RECORDED")
        st.info(f"⏱ Exit Time: {exit_time_str}")

        # Convert to timestamps
        entry_ts = int(datetime.strptime(entry_time_str, "%d/%m/%Y %H:%M:%S").timestamp())
        exit_ts = int(datetime.strptime(exit_time_str, "%d/%m/%Y %H:%M:%S").timestamp())

        # Call C billing program
        result = subprocess.check_output(
            ["parkinglot.exe", str(entry_ts), str(exit_ts)]
        ).decode()

        # ---------------- CLEAN BILL UI ----------------
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

    # Reset for next scan
    st.session_state.detected_plate = ""