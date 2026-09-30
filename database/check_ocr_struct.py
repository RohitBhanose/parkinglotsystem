import easyocr
import numpy as np
import cv2

# Create a synthetic plate image with text
img = np.ones((60,200,3), dtype=np.uint8)*220
cv2.putText(img, 'MH12AB1234', (10,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,0), 2)

reader = easyocr.Reader(['en'], gpu=False)
results = reader.readtext(img)

print(f'readtext() returns {len(results)} result(s)')
for i, r in enumerate(results):
    print(f'  result[{i}]:')
    print(f'    type: {type(r)}, len: {len(r)}')
    print(f'    [0] bbox:    {r[0]}')
    print(f'    [1] text:    {r[1]}')
    print(f'    [2] conf:    {r[2]}')
    print(f'    [-2] = r[1]: {r[-2]}  <-- this is the TEXT field')
    print(f'    [-1] = r[2]: {r[-1]}  <-- this is the CONF field')

print()
print('EasyOCR result structure: (bbox, text, confidence)')
print('r[1] or r[-2] both access text - this is CORRECT')