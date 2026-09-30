import cv2, re
import numpy as np
from ultralytics import YOLO
import easyocr

model_path = r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\best.pt'
model = YOLO(model_path)
reader = easyocr.Reader(['en'], gpu=False)

patterns = [
    r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}',
    r'[0-9]{2}BH[0-9]{4}[A-Z]{1,2}'
]

print('Opening camera...')
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('ERROR: Camera not available')
    exit(1)

print('Camera open. Capturing 30 frames to check YOLO detections...')
detection_count = 0
ocr_attempts = 0
plates_found = []

for i in range(30):
    ret, frame = cap.read()
    if not ret:
        print(f'Frame {i}: read failed')
        continue

    results = model(frame, conf=0.3, verbose=False)
    
    for r in results:
        if r.boxes is not None and len(r.boxes) > 0:
            detection_count += 1
            print(f'Frame {i}: YOLO detected {len(r.boxes)} box(es), confs={[f"{c:.2f}" for c in r.boxes.conf.tolist()]}')
            
            for box in r.boxes.xyxy:
                x1, y1, x2, y2 = map(int, box)
                # Expand box slightly for better OCR
                h, w = frame.shape[:2]
                pad = 5
                x1p = max(0, x1-pad); y1p = max(0, y1-pad)
                x2p = min(w, x2+pad); y2p = min(h, y2+pad)
                plate_img = frame[y1p:y2p, x1p:x2p]
                
                if plate_img.size == 0:
                    print(f'  Empty crop!')
                    continue
                
                # Save the crop for inspection
                crop_path = rf'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\database\plate_crop_{i}.jpg'
                cv2.imwrite(crop_path, plate_img)
                print(f'  Crop saved: {crop_path}, shape={plate_img.shape}')
                
                # Run OCR
                ocr_attempts += 1
                text_results = reader.readtext(plate_img)
                print(f'  OCR raw results: {text_results}')
                
                for t in text_results:
                    raw = re.sub(r'[^A-Z0-9]', '', t[1].upper())
                    print(f'  Cleaned text: {raw}')
                    for p in patterns:
                        match = re.findall(p, raw)
                        if match:
                            plates_found.append(match[0])
                            print(f'  PLATE FOUND: {match[0]}')
    
    if i % 5 == 0:
        print(f'Frame {i}: no detections so far ({detection_count} total detections)')

cap.release()
print(f'\nSummary:')
print(f'  Frames captured: 30')
print(f'  YOLO detections: {detection_count}')
print(f'  OCR attempts: {ocr_attempts}')
print(f'  Plates found: {plates_found}')

if detection_count == 0:
    print('\nDIAGNOSIS: YOLO model is NOT detecting any license plates.')
    print('Point a real number plate at the camera, or confidence threshold may be too high.')
elif not plates_found:
    print('\nDIAGNOSIS: YOLO detects plates but OCR cannot read them.')
    print('Check the saved plate_crop_*.jpg files for image quality.')