"""
Test ID:    TC_SLOT_001
Test Title: Slot 遊戲連續 10 次執行金流驗證
Test Steps:
    1. 設定押注金額至 test_data.json 指定值
    2. 記錄 Spin 前玩家資產
    3. 點擊 Spin 按鈕
    4. 以 OpenCV 畫面比對等待轉輪停止
    5. 偵測並關閉連線異常等對話框
    6. 記錄 Spin 後贏分與資產
    7. 驗證金流：資產(後) == 資產(前) - 押注 + 贏分
    8. 重複 10 次並輸出 Excel 報告（含截圖）
Expected Result:
    每次金流驗證結果為 PASS，最終輸出完整 Excel 報告
"""
import json
import os
import time
import random
from datetime import datetime
from pathlib import Path

import pytest
from selenium.common.exceptions import InvalidSessionIdException

from config.settings import SCREENSHOT_DIR
from utils.report_helper import SpinRecord, CashFlowResult, verify_cashflow, generate_excel_report

DATA_PATH = Path(__file__).parent.parent / "data" / "test_data.json"


@pytest.fixture(scope="module")
def test_config():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_slot_cashflow(slot_page, test_config):
    target_bet = test_config["target_bet"]
    iterations = test_config["test_iterations"]
    records = []

    bet_actual = slot_page.set_bet(target_bet, SCREENSHOT_DIR)
    print(f"✅ 押注已設定為 {bet_actual}")

    for i in range(1, iterations + 1):
        delay_min = test_config.get("spin_delay_min", 2.0)
        delay_max = test_config.get("spin_delay_max", 4.0)
        time.sleep(random.uniform(delay_min, delay_max))  # 隨機延遲，模擬人工操作節奏
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        shot_before = os.path.join(SCREENSHOT_DIR, f"spin_{i}_before.png")
        shot_after = shot_before  # 預設截圖路徑，例外時仍可用

        # 在 try 外初始化，讓例外時能保留已讀到的值
        balance_before, bet, win, balance_after = 0.0, 0.0, 0.0, 0.0
        failure_reason = ""

        try:
            slot_page.take_screenshot(shot_before)
            balance_before = slot_page.read_balance(shot_before)

            # OCR 讀取押注，若讀值明顯偏低則以 target_bet 為準
            bet_ocr = slot_page.read_bet(shot_before)
            bet = target_bet if bet_ocr > 0 and abs(bet_ocr - target_bet) / target_bet > 0.5 else bet_ocr

            slot_page.click_spin()
            shot_after = slot_page.wait_for_spin_to_stop(SCREENSHOT_DIR, i)

            # 轉輪停止後，先關閉可能出現的對話框再讀值
            slot_page.dismiss_dialog_if_any(shot_after)

            win = slot_page.read_win(shot_after)
            balance_after = slot_page.read_balance(shot_after)

            record = SpinRecord(
                index=i,
                timestamp=timestamp,
                balance_before=balance_before,
                bet=bet,
                win=win,
                balance_after=balance_after,
                result=CashFlowResult.PASS,
                screenshot_path=shot_after,
            )
            record.result = verify_cashflow(record)

        except InvalidSessionIdException as e:
            # 瀏覽器 session 已失效（遊戲斷線後 Chrome 被踢出），中止後續輪次
            failure_reason = f"瀏覽器連線中斷，後續輪次無法繼續：{type(e).__name__}"
            record = SpinRecord(
                index=i, timestamp=timestamp,
                balance_before=balance_before, bet=bet,
                win=win, balance_after=balance_after,
                result=CashFlowResult.FAIL,
                screenshot_path=shot_before,
                failure_reason=failure_reason,
            )
            records.append(record)
            # 補記剩餘輪次為 FAIL
            for j in range(i + 1, iterations + 1):
                records.append(SpinRecord(
                    index=j, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    balance_before=0, bet=0, win=0, balance_after=0,
                    result=CashFlowResult.FAIL,
                    failure_reason="瀏覽器已斷線，跳過",
                ))
            print(f"❌ [{i:02d}] {failure_reason}，中止測試")
            break

        except Exception as e:
            failure_reason = str(e)
            record = SpinRecord(
                index=i, timestamp=timestamp,
                balance_before=balance_before, bet=bet,
                win=win, balance_after=balance_after,
                result=CashFlowResult.FAIL,
                screenshot_path=shot_before,
                failure_reason=failure_reason,
            )

        records.append(record)
        status = "✅" if record.result == CashFlowResult.PASS else "❌"
        print(
            f"{status} [{i:02d}] {timestamp} | "
            f"資產前:{record.balance_before:.2f} | 押注:{record.bet:.2f} | "
            f"贏分:{record.win:.2f} | 資產後:{record.balance_after:.2f} | "
            f"{record.result.value}"
            + (f" ({failure_reason})" if failure_reason else "")
        )

    report_path = generate_excel_report(records)
    print(f"\n📊 報告已儲存：{report_path}")

    failed = [r for r in records if r.result == CashFlowResult.FAIL]
    assert not failed, (
        f"{len(failed)}/{iterations} 次金流驗證失敗，"
        f"失敗項次：{[r.index for r in failed]}"
    )
