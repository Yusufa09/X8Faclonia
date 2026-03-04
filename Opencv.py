import cv2
import numpy as np

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

# Higher varThreshold = Less sensitive to false 'gas' noise
fgbg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=80, detectShadows=False)

print("Detection calibrated. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret: break

    # 1. CLEAN THE IMAGE (Removes camera 'static' noise)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0) # Heavier blur reduces false pebbles

    # --- PART A: RELIABLE GAS/SMOKE ---
    fgmask = fgbg.apply(frame)
    # Remove tiny flickering 'ghosts' using a kernel filter
    kernel = np.ones((5,5), np.uint8)
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel) 
    
    gas_contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in gas_contours:
        area = cv2.contourArea(cnt)
        if area > 1500: # Increase this to ignore small movements
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, "GAS/SMOKE", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # --- PART B: RELIABLE PEBBLES ---
    # Detect only high-contrast solid edges
    edges = cv2.Canny(blurred, 100, 200) # Increased thresholds = less sensitive
    pebble_contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in pebble_contours:
        area = cv2.contourArea(cnt)
        # 1. Size Filter: Ignore tiny dust (must be between 150 and 1000 pixels)
        if 150 < area < 1000:
            # 2. Shape Filter: Check if it's actually a 'solid' chunk (Circular/Square)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            
            # Pebbles are usually between 0.4 and 0.9 circularity
            if 0.3 < circularity < 1.0:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "PEBBLE", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    cv2.imshow('Refined Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
