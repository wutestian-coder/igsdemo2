import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from config.settings import GAME_URL, SCREENSHOT_DIR, REPORT_DIR
from pages.slot_page import SlotPage


def pytest_configure(config):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)


@pytest.fixture(scope="session")
def driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    d = webdriver.Chrome(options=options)
    yield d
    d.quit()


@pytest.fixture(scope="session")
def slot_page(driver):
    driver.get(GAME_URL)

    # 儲存校正截圖，方便確認座標是否正確
    calibration_shot = os.path.join(SCREENSHOT_DIR, "calibration_login_page.png")
    driver.save_screenshot(calibration_shot)

    print("\n" + "=" * 55)
    print("瀏覽器已開啟，請完成以下步驟：")
    print("  1. 手動登入帳號（含圖片驗證碼與簡訊 OTP）")
    print("  2. 進入老虎機遊戲畫面（有轉輪那個）")
    print("  3. 確認押注金額已設定為 100.00")
    print("  ⚠️  程式不會自動調整押注，請手動確認")
    print("=" * 55)
    input(">>> 確認已在遊戲畫面且押注為 100 後，按 Enter 繼續...\n")

    page = SlotPage(driver)
    page.wait_for_game_loaded()

    # 儲存進入遊戲後的校正截圖，確認座標設定是否正確
    calibration_game_shot = os.path.join(SCREENSHOT_DIR, "calibration_game.png")
    page.take_screenshot(calibration_game_shot)
    print(f"✅ 校正截圖已儲存：{calibration_game_shot}")
    print("   請確認截圖內容正確後再繼續\n")

    return page
