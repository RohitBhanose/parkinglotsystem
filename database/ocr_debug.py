import cv2, re
from ultralytics import YOLO
import easyocr

model = YOLO(r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\best.pt')
reader = easyocr.Reader(['en'], gpu=False)

patterns = [
    r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}',
    r'[0-9]{2}BH[0-9]{4}[A-Z]{1,2}'
]

def preprocess_plate(img):
    if img is None or img.size == 0: return None
    h, w = img.shape[:2]
    scale = max(1, int(100 / max(h, 1)))
    if scale > 1:
        img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    import numpy as np
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

print('Opening camera. Point plate at camera. Watching for 60 frames...')
cap = cv2.VideoCapture(0)
for _ in range(10): cap.read()  # warmup

for i in range(60):
    ret, frame = cap.read()
    if not ret: break
    
    results = model(frame, conf=0.25, verbose=False)
    for r in results:
        if r.boxes is None or len(r.boxes) == 0: continue
        for idx, box in enumerate(r.boxes.xyxy):
            x1,y1,x2,y2 = map(int, box)
            conf = float(r.boxes.conf[idx])
            print(f'\nFrame {i}: YOLO detection conf={conf:.2f}, box=({x1},{y1},{x2},{y2})')
            
            pad = 8
            h_f,w_f = frame.shape[:2]
            crop = frame[max(0,y1-pad):min(h_f,y2+pad), max(0,x1-pad):min(w_f,x2+pad)]
            cv2.imwrite(rf'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\database\crop_{i}.jpg', crop)
            
            processed = preprocess_plate(crop)
            
            # Try OCR with NO confidence threshold first - show ALL reads
            ocr_raw = reader.readtext(crop, detail=1)
            ocr_proc = reader.readtext(processed, detail=1) if processed is not None else []
            
            print(f'  OCR on raw crop ({crop.shape}): {[(t[1],round(t[2],2)) for t in ocr_raw]}')
            print(f'  OCR on processed: {[(t[1],round(t[2],2)) for t in ocr_proc]}')
            
            all_texts = ocr_raw + ocr_proc
            for t in all_texts:
                raw = re.sub(r'[^A-Z0-9]', '', t[1].upper())
                print(f'    cleaned: "{raw}"')
                for p in patterns:
                    m = re.findall(p, raw)
                    if m:
                        print(f'    >>> PATTERN MATCH: {m[0]}')

cap.release()
print('Done')