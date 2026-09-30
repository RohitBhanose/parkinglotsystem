import cv2
from ultralytics import YOLO

model_path = r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\best.pt'
model = YOLO(model_path)

print('Opening camera for 10 frames at very low confidence (0.05)...')
cap = cv2.VideoCapture(0)
any_detect = False
for i in range(10):
    ret, frame = cap.read()
    if not ret: break
    # Save a raw frame for inspection
    if i == 0:
        cv2.imwrite(r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\database\raw_frame.jpg', frame)
        print(f'Raw frame saved, shape={frame.shape}')
    results = model(frame, conf=0.05, verbose=False)
    for r in results:
        if r.boxes is not None and len(r.boxes) > 0:
            confs = r.boxes.conf.tolist()
            print(f'Frame {i}: {len(r.boxes)} detections at conf>=0.05: {[f"{c:.3f}" for c in confs]}')
            any_detect = True
cap.release()
if not any_detect:
    print('No detections at conf=0.05 either. Either no plate in view OR YOLO model issue.')
    print('The raw_frame.jpg has been saved - check if the camera sees a plate.')