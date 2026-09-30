import sys
print(f'Python: {sys.version}')

print('\n--- Checking packages ---')
try:
    import cv2
    print(f'OpenCV: {cv2.__version__}')
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    print(f'Camera index 0: ret={ret}, frame shape={frame.shape if ret and frame is not None else "None"}')
except Exception as e:
    print(f'OpenCV/Camera ERROR: {e}')

print()
try:
    from ultralytics import YOLO
    import os
    model_path = r'e:\Rohit\Projects\Parking Lot Management\parkinglotsystem\best.pt'
    print(f'best.pt exists: {os.path.exists(model_path)}, size: {os.path.getsize(model_path)} bytes')
    model = YOLO(model_path)
    print(f'YOLO model loaded. Task: {model.task}')
    # Check what classes the model detects
    print(f'Model classes: {model.names}')
except Exception as e:
    print(f'YOLO ERROR: {e}')

print()
try:
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False)
    print('EasyOCR Reader loaded (CPU mode)')
    # Test OCR on a small blank image
    import numpy as np
    blank = np.ones((60,200,3), dtype=np.uint8)*200
    result = reader.readtext(blank)
    print(f'EasyOCR test on blank image: {result}')
except Exception as e:
    print(f'EasyOCR ERROR: {e}')