import os
import time
import cv2
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from config.settings import LOGIN_TIMEOUT, SPIN_BUTTON_POS, BET_PLUS_POS, BET_MINUS_POS, SCREENSHOT_DIR
from utils.cv_helper import CVHelper
from utils.ocr_helper import OCRHelper


class SlotPage:
    _IFRAME = (By.CSS_SELECTOR, "iframe.game-iframe")
    _CANVAS = (By.ID, "GameCanvas")

    def __init__(self, driver):
        self.driver = driver
        self.canvas = None
        self._cv = CVHelper()
        self._ocr = OCRHelper()

    def wait_for_game_loaded(self):
        wait = WebDriverWait(self.driver, LOGIN_TIMEOUT)
        iframe = wait.until(EC.presence_of_element_located(self._IFRAME))
        self.driver.switch_to.frame(iframe)
        self.canvas = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located(self._CANVAS)
        )

    def _ensure_canvas(self):
        """若 canvas 參考已失效（連線異常後 iframe 重載），重新切入 iframe 並取得 canvas。"""
        from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
        try:
            _ = self.canvas.size  # 測試參考是否仍有效
            return
        except (StaleElementReferenceException, NoSuchElementException):
            pass
        try:
            self.driver.switch_to.default_content()
            iframe = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(self._IFRAME)
            )
            self.driver.switch_to.frame(iframe)
            self.canvas = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(self._CANVAS)
            )
        except Exception as e:
            raise RuntimeError(f"無法重新取得遊戲 Canvas（可能需要重新登入）：{e}")

    def take_screenshot(self, path: str):
        self._ensure_canvas()
        self.canvas.screenshot(path)

    def read_balance(self, screenshot_path: str) -> float:
        return self._ocr.read_value(screenshot_path, "balance")

    def read_win(self, screenshot_path: str) -> float:
        return self._ocr.read_value(screenshot_path, "win")

    def read_bet(self, screenshot_path: str) -> float:
        return self._ocr.read_value(screenshot_path, "bet")

    def click_spin(self):
        self._click_at(*SPIN_BUTTON_POS)

    def click_bet_plus(self):
        self._click_at(*BET_PLUS_POS)

    def click_bet_minus(self):
        self._click_at(*BET_MINUS_POS)

    def set_bet(self, target_bet: float, screenshot_dir: str, max_steps: int = 100) -> float:
        """自動點擊 +/- 將押注調整至 target_bet，以 OCR 確認每次結果。"""
        for step in range(max_steps):
            shot = os.path.join(screenshot_dir, f"bet_check_{step}.png")
            self.take_screenshot(shot)
            current = self.read_bet(shot)
            if abs(current - target_bet) <= 0.5:
                return current
            if current < target_bet:
                self.click_bet_plus()
            else:
                self.click_bet_minus()
            time.sleep(0.3)
        raise RuntimeError(
            f"set_bet 失敗：{max_steps} 步內無法達到目標 {target_bet}，最後讀值 {current}"
        )

    def verify_bet(self, target_bet: float, screenshot_dir: str) -> float:
        """讀取當前押注並驗證（已由 set_bet 調整完成後的二次確認）。"""
        shot = os.path.join(screenshot_dir, "bet_verify.png")
        self.take_screenshot(shot)
        current = self.read_bet(shot)
        if abs(current - target_bet) > 0.5:
            raise RuntimeError(
                f"押注金額不符：OCR 讀到 {current}，預期 {target_bet}。"
            )
        return current

    def dismiss_dialog_if_any(self, screenshot_path: str) -> bool:
        """
        偵測並關閉遊戲對話框（如「連線異常 #990」）。
        掃描對話框 ✓ 按鈕所在的綠色像素區域（y=0.62~0.70），實際按鈕在 y≈0.66。
        """
        stream = np.fromfile(screenshot_path, dtype=np.uint8)
        img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        x1, x2 = int(w * 0.46), int(w * 0.54)
        y1, y2 = int(h * 0.62), int(h * 0.70)
        region = img[y1:y2, x1:x2]
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 80, 80]), np.array([90, 255, 255]))
        if np.count_nonzero(mask) / mask.size > 0.05:
            self._click_at(0.50, 0.66)
            time.sleep(1.5)
            return True
        return False

    def wait_for_spin_to_stop(self, screenshot_dir: str, spin_index: int) -> str:
        return self._cv.wait_for_spin_stop(self, screenshot_dir, spin_index)

    def _click_at(self, x_ratio: float, y_ratio: float):
        self._ensure_canvas()
        size = self.canvas.size
        x_offset = int(size['width'] * x_ratio) - size['width'] // 2
        y_offset = int(size['height'] * y_ratio) - size['height'] // 2
        ActionChains(self.driver)\
            .move_to_element_with_offset(self.canvas, x_offset, y_offset)\
            .click()\
            .perform()
