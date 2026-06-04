import re
import cv2
import numpy as np
import easyocr
from config.settings import OCR_REGIONS


def _imread(path: str) -> np.ndarray:
    """cv2.imread workaround for Unicode/CJK paths on Windows."""
    stream = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(stream, cv2.IMREAD_COLOR)


class OCRHelper:

    def __init__(self):
        self._reader = easyocr.Reader(['en'], gpu=False, verbose=False)

    def _crop_region(self, img: np.ndarray, region_key: str) -> np.ndarray:
        x1r, y1r, x2r, y2r = OCR_REGIONS[region_key]
        h, w = img.shape[:2]
        return img[int(h * y1r):int(h * y2r), int(w * x1r):int(w * x2r)]

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        scale = 4
        h, w = crop.shape[:2]
        resized = cv2.resize(crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # 遊戲 UI 為白字深底；反轉成黑字白底讓 EasyOCR 讀取更準確
        # 同時小數點在淺色背景下更容易被偵測到
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # 輕微膨脹讓小數點與細線更清晰
        kernel = np.ones((2, 2), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)
        return thresh

    def read_value(self, screenshot_path: str, region_key: str) -> float:
        img = _imread(screenshot_path)
        crop = self._crop_region(img, region_key)
        processed = self._preprocess(crop)
        results = self._reader.readtext(processed, allowlist='0123456789.,')
        text = ''.join(r[1] for r in results).replace(',', '')
        print(f"  [OCR DEBUG] {region_key}: raw={text!r}")
        match = re.search(r'\d+\.?\d*', text)
        if not match:
            raise ValueError(f"OCR 無法從 [{region_key}] 辨識數字，原始讀取：{text!r}")
        raw_str = match.group()
        value = float(raw_str)
        # 遊戲數值固定顯示兩位小數。若 OCR 漏讀小數點導致數值異常大，補回小數位
        if '.' not in raw_str and value > 9999:
            value = round(value / 100, 2)
            print(f"  [OCR DEBUG] {region_key}: 補小數點 → {value}")
        print(f"  [OCR DEBUG] {region_key}: parsed={value}")
        return value
