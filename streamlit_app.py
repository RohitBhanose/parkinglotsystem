import streamlit as st
import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Smart Parking", layout="wide")

# ---------------- INIT ----------------
if "detected_plate" not in st.session_state:
    st.session_state.detected_plate = ""

if "page" not in st.session_state:
    st.session_state.page = "Scan"

PARKING_SLOTS = [str(i) for i in range(1, 31)]

# ---------------- HEADER ----------------
st.markdown("<h1 style='text-align:center;'>🚗 Smart Parking System</h1>", unsafe_allow_html=True)

# ---------------- NAV ----------------
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Scan", use_container_width=True):
        st.session_state.page = "Scan"
with c2:
    if st.button("Records", use_container_width=True):
        st.session_state.page = "Records"
with c3:
    if st.button("Parking Map", use_container_width=True):
        st.session_state.page = "Map"

st.markdown("---")

# ---------------- MODELS ----------------
@st.cache_resource
def load_models():
    return YOLO("best.pt"), easyocr.Reader(['en'])

model, reader = load_models()

patterns = [
    r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}",
    r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}"
]

# ---------------- DATA ----------------
def load_data():
    if os.path.exists("parking_data.csv"):
        df = pd.read_csv("parking_data.csv")
    else:
        df = pd.DataFrame(columns=["Number Plate","Entry Time","Exit Time","Slot"])

    df["Exit Time"] = df["Exit Time"].fillna("").astype(str).str.strip()
    df["Slot"] = df["Slot"].fillna("").astype(str)
    return df

def save_data(df):
    df.to_csv("parking_data.csv", index=False)

# ---------------- SCAN ----------------
if st.session_state.page == "Scan":

    st.subheader("Live Scan")

    col_cam, col_info = st.columns([2,1])

    with col_cam:
        start = st.button("Start Camera")
        frame_placeholder = st.empty()

    with col_info:
        info_box = st.empty()

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
        with col_info:

            st.success(f"Detected: {plate}")

            df = load_data()
            now = datetime.now()

            active = df[(df["Number Plate"] == plate) & (df["Exit Time"] == "")]

            # ENTRY
            if active.empty:
                occupied = df[df["Exit Time"] == ""]["Slot"].tolist()
                slot = next((s for s in PARKING_SLOTS if s not in occupied), None)

                df = pd.concat([df, pd.DataFrame([{
                    "Number Plate": plate,
                    "Entry Time": now.strftime("%d/%m/%Y %H:%M:%S"),
                    "Exit Time": "",
                    "Slot": slot
                }])], ignore_index=True)

                save_data(df)

                st.success("🚀 Entry Recorded")
                st.info(f"🅿 Slot {slot}")

            # EXIT
            else:
                idx = active.index[-1]

                entry_time = datetime.strptime(df.loc[idx, "Entry Time"], "%d/%m/%Y %H:%M:%S")
                exit_time = now

                df.loc[idx, "Exit Time"] = exit_time.strftime("%d/%m/%Y %H:%M:%S")
                save_data(df)

                duration = max(1, int((exit_time - entry_time).total_seconds()))
                rate = 1.0
                total = duration * rate

                st.success("🚪 Exit Recorded")

                st.markdown("## Parking Receipt")

                receipt = pd.DataFrame({
                    "Details": [
                        "Vehicle Number",
                        "Entry Time",
                        "Exit Time",
                        "Duration",
                        "Rate"
                    ],
                    "Value": [
                        plate,
                        entry_time.strftime("%H:%M:%S"),
                        exit_time.strftime("%H:%M:%S"),
                        f"{duration} minutes",
                        f"₹{rate} / minute"
                    ]
                })

                st.table(receipt)

                st.markdown("---")

                st.markdown(
                    f"<h2 style='text-align:center;'>Total Fare: ₹{total:.2f}</h2>",
                    unsafe_allow_html=True
                )

                if os.path.exists("payment_qr.png"):
                    st.image("payment_qr.png", width=200)

        st.session_state.detected_plate = ""

# ---------------- RECORDS ----------------
elif st.session_state.page == "Records":
    st.subheader("Parking Records")
    st.dataframe(load_data())

# ---------------- MAP ----------------
elif st.session_state.page == "Map":

    st.subheader("Parking Map")

    if os.path.exists("parking_map.png"):
        st.image("parking_map.png", use_container_width=True)

    st.markdown("---")

    df = load_data()
    active_df = df[df["Exit Time"] == ""]

    slot_map = {}
    for slot in PARKING_SLOTS:
        row = active_df[active_df["Slot"].astype(str) == slot]
        if not row.empty:
            slot_map[slot] = row.iloc[-1]["Number Plate"]
        else:
            slot_map[slot] = None

    for i in range(0, len(PARKING_SLOTS), 5):
        cols = st.columns(5)

        for j in range(5):
            if i+j < len(PARKING_SLOTS):
                slot = PARKING_SLOTS[i+j]

                if slot_map[slot] is None:
                    cols[j].success(f"Slot {slot}")
                else:
                    cols[j].error(f"Slot {slot}\n{slot_map[slot]}")