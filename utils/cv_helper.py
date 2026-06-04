import os
import time
import cv2
import numpy as np
from config.settings import (
    SPIN_TIMEOUT, SPIN_POLL_INTERVAL,
    SPIN_STABLE_THRESHOLD, SPIN_STABLE_CONSECUTIVE, REEL_REGION
)


def _imread(path: str) -> np.ndarray:
    """cv2.imread workaround for Unicode/CJK paths on Windows."""
    stream = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(stream, cv2.IMREAD_COLOR)


class CVHelper:

    def _crop_reel(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        x1, y1 = int(w * REEL_REGION[0]), int(h * REEL_REGION[1])
        x2, y2 = int(w * REEL_REGION[2]), int(h * REEL_REGION[3])
        return img[y1:y2, x1:x2]

    def _similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        if img1.shape != img2.shape:
            h = min(img1.shape[0], img2.shape[0])
            w = min(img1.shape[1], img2.shape[1])
            img1 = cv2.resize(img1, (w, h))
            img2 = cv2.resize(img2, (w, h))
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        # 只計算差異 > 10 的像素，濾除壓縮偽影與微小動畫噪點
        significant = np.count_nonzero(diff > 10)
        return 1.0 - significant / gray1.size

    def wait_for_spin_stop(self, page, screenshot_dir: str, spin_index: int) -> str:
        """Poll canvas reel area until consecutive frames are visually identical.

        Strategy:
        - Initial 3s wait guarantees reels have physically stopped (values settled).
        - Then pixel-detection confirms visual stability (catches no-win quickly).
        - On timeout (win animation loops forever), returns last frame instead of
          raising — OCR values are already correct by this point.
        - Handles 連線異常 dialogs inline with correct y-position.
        """
        # 轉輪固定在 3s 內停止；此等待確保資產/贏分數值已更新完畢
        time.sleep(3.0)

        stable_count = 0
        prev_reel = None
        deadline = time.time() + SPIN_TIMEOUT
        frame = 0
        last_path = None

        while time.time() < deadline:
            path = os.path.join(screenshot_dir, f"spin_{spin_index}_frame_{frame}.png")
            page.take_screenshot(path)
            last_path = path

            # 連線異常對話框：關閉後重置比對基準
            if page.dismiss_dialog_if_any(path):
                stable_count = 0
                prev_reel = None
                frame += 1
                time.sleep(1.5)
                continue

            curr_reel = self._crop_reel(_imread(path))

            if prev_reel is not None:
                sim = self._similarity(prev_reel, curr_reel)
                if sim >= SPIN_STABLE_THRESHOLD:
                    stable_count += 1
                    if stable_count >= SPIN_STABLE_CONSECUTIVE:
                        return last_path
                else:
                    stable_count = 0

            prev_reel = curr_reel
            frame += 1
            time.sleep(SPIN_POLL_INTERVAL)

        # 贏錢動畫會無限循環，但數值在 3s 初始等待後已確定；直接以最後截圖讀值
        print(f"  [WARN] Spin {spin_index} 贏錢動畫持續，以最後截圖讀取結果")
        return last_path

    def wait_for_canvas_change(self, page, screenshot_dir: str, index: int):
        """Wait until canvas content visibly changes (e.g. after bet +/- click)."""
        ref_path = os.path.join(screenshot_dir, f"bet_ref_{index}.png")
        page.take_screenshot(ref_path)
        ref_img = _imread(ref_path)

        deadline = time.time() + 5
        check = 0
        while time.time() < deadline:
            curr_path = os.path.join(screenshot_dir, f"bet_curr_{index}_{check}.png")
            page.take_screenshot(curr_path)
            curr_img = _imread(curr_path)
            if self._similarity(ref_img, curr_img) < 0.99:
                return
            check += 1
            time.sleep(0.1)
