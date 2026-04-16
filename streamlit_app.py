import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import pandas as pd
from datetime import datetime

# ---------------- INIT ----------------
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""

if "selected_record" not in st.session_state:
    st.session_state.selected_record = None

if "page" not in st.session_state:
    st.session_state.page = "Scan"

# 🔥 PARKING SLOTS
PARKING_SLOTS = [
    "1","2","3","4","5","6","7","8","9",
    "J","K","L","M","N","O","P",
    "61","62","63","64","65","66","67"
]

# ---------------- HEADER ----------------
st.markdown("<h1 style='text-align:center;'>Smart Parking System</h1>", unsafe_allow_html=True)

# ---------------- NAVBAR ----------------
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Scan", use_container_width=True):
        st.session_state.page = "Scan"

with col2:
    if st.button("Records", use_container_width=True):
        st.session_state.page = "Records"

with col3:
    if st.button("Parking Map", use_container_width=True):
        st.session_state.page = "Map"
# ---------------- MODELS ----------------
@st.cache_resource
def load_models():
    return YOLO("best.pt"), easyocr.Reader(['en'])

model, reader = load_models()

patterns = [
    r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}",
    r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}"
]

# ---------------- SCAN PAGE ----------------
if st.session_state.page == "Scan":

    start = st.button("Start Scan", use_container_width=True)
    frame_placeholder = st.empty()

    if start:
        cap = cv2.VideoCapture(0)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = model(frame, conf=0.3)

            for r in results:
                if r.boxes is not None:
                    for box in r.boxes.xyxy:
                        x1,y1,x2,y2 = map(int, box)
                        plate_img = frame[y1:y2, x1:x2]
                        text = reader.readtext(plate_img)

                        for t in text:
                            raw = re.sub(r'[^A-Z0-9]', '', t[-2].upper())
                            for p in patterns:
                                match = re.findall(p, raw)
                                if match:
                                    st.session_state.detected_plate = match[0]

            frame_placeholder.image(frame, channels="BGR")

            if st.session_state.detected_plate:
                cap.release()
                break

    plate = st.session_state.detected_plate

    if plate:
        st.success(f"Detected: {plate}")

        file = "parking_data.csv"
        now = datetime.now()

        if os.path.exists(file):
            df = pd.read_csv(file)
            df["Exit Time"] = df["Exit Time"].fillna("").astype(str).str.strip()
        else:
            df = pd.DataFrame(columns=["Token","Number Plate","Entry Time","Exit Time","Paid","Slot"])

        token = 1 if len(df)==0 else int(df["Token"].max())+1

        active = df[(df["Number Plate"] == plate) & (df["Exit Time"] == "")]

        # ENTRY
        if active.empty:


            new_entry = pd.DataFrame([{
                "Token": token,
                "Number Plate": plate,
                "Entry Time": now.strftime("%d/%m/%Y %H:%M:%S"),
                "Exit Time": "",
                "Paid": "No",
                "Slot": ""
            }])

            df = pd.concat([df, new_entry], ignore_index=True)
            df.to_csv(file, index=False)

            st.success(f"Entry recorded | Token {token}")

        # EXIT
        else:
            idx = active.index[-1]

            entry_time_str = df.loc[idx, "Entry Time"]
            entry_time = datetime.strptime(entry_time_str, "%d/%m/%Y %H:%M:%S")
            exit_time = now

            df.loc[idx, "Exit Time"] = exit_time.strftime("%d/%m/%Y %H:%M:%S")

            duration_seconds = int((exit_time - entry_time).total_seconds())
            duration_minutes = max(1, duration_seconds)

            rate = 1.0
            amount = duration_minutes * rate

            df.to_csv(file, index=False)

            st.success("Exit recorded")

            # 🔥 BILL TABLE FORMAT
            st.markdown("## Parking Bill")

            bill_df = pd.DataFrame({
                "Field": ["Vehicle Number", "Entry Time", "Exit Time", "Duration", "Rate"],
                "Details": [
                    plate,
                    entry_time.strftime("%H:%M:%S"),
                    exit_time.strftime("%H:%M:%S"),
                    f"{duration_minutes} minutes",
                    f"₹{rate} / min"
                ]
            })

            st.table(bill_df)

            st.markdown("---")

            # 🔥 BIG TOTAL
            st.markdown(f"# 💰 ₹ {amount}")

            st.markdown("---")

            # 🔥 CENTERED QR + TEXT
            col1, col2, col3 = st.columns([1,2,1])

            with col2:
                st.markdown("### Scan this QR for e-bill")
                if os.path.exists("payment_qr.png"):
                    st.image("payment_qr.png", width=250)
                else:
                    st.warning("payment_qr.png not found")

        st.session_state.detected_plate = ""

# ---------------- RECORDS ----------------
elif st.session_state.page == "Records":
    st.title("Records")

    if os.path.exists("parking_data.csv"):
        df = pd.read_csv("parking_data.csv")
        st.dataframe(df)

# ---------------- MAP ----------------
elif st.session_state.page == "Map":
    st.title("Parking Map")

    if os.path.exists("parking_map.png"):
        st.image("parking_map.png", use_container_width=True)