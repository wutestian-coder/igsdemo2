"""
執行這個腳本會在 screenshots/ 產生 debug_regions.png
在截圖上畫出目前設定的 OCR 區域與點擊座標，方便確認是否正確
"""
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from config.settings import OCR_REGIONS, SPIN_BUTTON_POS, BET_PLUS_POS, BET_MINUS_POS, SCREENSHOT_DIR

CALIBRATION_IMG = os.path.join(SCREENSHOT_DIR, "bet_check_0.png")
OUTPUT_IMG = os.path.join(SCREENSHOT_DIR, "debug_regions.png")

stream = np.fromfile(CALIBRATION_IMG, dtype=np.uint8)
img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
h, w = img.shape[:2]
print(f"Canvas size: {w} x {h}")

colors = {
    "balance": (0, 255, 0),
    "win":     (255, 165, 0),
    "bet":     (0, 0, 255),
}

for key, (x1r, y1r, x2r, y2r) in OCR_REGIONS.items():
    x1, y1, x2, y2 = int(w*x1r), int(h*y1r), int(w*x2r), int(h*y2r)
    cv2.rectangle(img, (x1, y1), (x2, y2), colors[key], 2)
    cv2.putText(img, key, (x1+2, y1+14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, colors[key], 1)

for label, (xr, yr) in [("SPIN", SPIN_BUTTON_POS), ("BET+", BET_PLUS_POS), ("BET-", BET_MINUS_POS)]:
    cx, cy = int(w * xr), int(h * yr)
    cv2.drawMarker(img, (cx, cy), (0, 255, 255), cv2.MARKER_CROSS, 20, 2)
    cv2.putText(img, label, (cx+8, cy-8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

cv2.imencode('.png', img)[1].tofile(OUTPUT_IMG)
print(f"Debug 截圖已儲存：{OUTPUT_IMG}")
print("請打開該圖確認框的位置，再調整 config/settings.py")
