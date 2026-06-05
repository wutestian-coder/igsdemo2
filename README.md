# Slot 遊戲自動化金流測試

針對 H5 老虎機遊戲的自動化測試框架，透過 **Selenium** 操作遊戲、**OpenCV** 偵測轉輪停止、**EasyOCR** 辨識畫面數值，自動執行連續 Spin 並驗證每一輪的金流計算是否正確，最後輸出含截圖的 Excel 報告。

由於遊戲畫面是 `<canvas>` 渲染（無 DOM 元素可定位），所有互動皆採「比例座標點擊 + 影像辨識」的方式完成。

---

## 測試案例：TC_SLOT_001

> Slot 遊戲連續 10 次執行金流驗證

**驗證公式：**

```
玩家資產(後) == 玩家資產(前) − 押注 + 遊戲贏分
```

每一輪 Spin 都會讀取上述四個數值並比對，誤差在 ±0.5 內視為 `PASS`。

**測試流程：**

1. 將押注金額調整至 `test_data.json` 指定值（自動點擊 +/− 並以 OCR 確認）
2. 記錄 Spin 前玩家資產
3. 點擊 Spin 按鈕
4. 以 OpenCV 畫面比對等待轉輪停止
5. 偵測並關閉「連線異常」等對話框
6. 記錄 Spin 後贏分與資產
7. 驗證金流公式
8. 重複 10 次並輸出 Excel 報告（含每輪截圖）

---

## 環境需求

- Python 3.8+
- Google Chrome（Selenium 4 內建 driver 自動管理）

## 安裝

```bash
pip install -r requirements.txt
```

主要相依套件：

| 套件 | 用途 |
| --- | --- |
| `selenium` | 瀏覽器自動化、canvas 座標點擊 |
| `opencv-python` | 轉輪停止偵測、對話框偵測、影像前處理 |
| `easyocr` | 辨識資產／押注／贏分數值 |
| `openpyxl` | 產出 Excel 報告（含內嵌截圖） |
| `pytest` | 測試執行框架 |

## 執行

```bash
pytest tests/test_slot.py -s
```

> ⚠️ 必須加上 `-s`，因為測試開始時需要**手動登入**（含圖形驗證碼與簡訊 OTP），程式會暫停並等待你按 Enter。

執行步驟：

1. 程式自動開啟瀏覽器並導向遊戲頁
2. 依畫面提示**手動完成登入**並進入老虎機畫面
3. 確認畫面停在有轉輪的遊戲頁後，按 **Enter** 繼續
4. 程式自動設定押注、連續 Spin 並驗證金流
5. 結束後於 `reports/` 取得 Excel 報告

## 輸出

| 目錄 | 內容 |
| --- | --- |
| `screenshots/` | 各輪 Spin 前後截圖、轉輪偵測影格、校正圖 |
| `reports/` | `slot_test_YYYYMMDD_HHMMSS.xlsx` 金流驗證報告（PASS 綠／FAIL 紅，內嵌截圖） |

兩個目錄皆已列入 `.gitignore`，不會進版控。

---

## 專案結構

```
.
├── conftest.py            # pytest fixtures：driver 啟動、手動登入引導
├── calibrate.py           # 座標校正工具，在截圖上畫出 OCR 區域與點擊點
├── requirements.txt
├── config/
│   └── settings.py        # 遊戲 URL、比例座標、OCR 區域、偵測參數
├── data/
│   └── test_data.json     # 目標押注、執行次數、Spin 間隔
├── pages/
│   └── slot_page.py       # Page Object：點擊、讀值、設定押注、關閉對話框
├── tests/
│   └── test_slot.py       # TC_SLOT_001 主測試
└── utils/
    ├── cv_helper.py       # OpenCV 轉輪停止偵測
    ├── ocr_helper.py      # EasyOCR 數值辨識與前處理
    └── report_helper.py   # 金流驗證與 Excel 報告產出
```

## 設定說明

### `data/test_data.json`

```json
{
    "target_bet": 100.0,       // 目標押注金額
    "test_iterations": 10,     // Spin 次數
    "spin_delay_min": 3.0,     // 每輪前隨機延遲下限（秒）
    "spin_delay_max": 6.0      // 每輪前隨機延遲上限（秒）
}
```

### `config/settings.py`

所有座標皆以 **canvas 寬／高比例**（0.0~1.0）表示，與解析度無關：

- `SPIN_BUTTON_POS` / `BET_PLUS_POS` / `BET_MINUS_POS`：按鈕點擊座標
- `OCR_REGIONS`：資產／贏分／押注的辨識區域
- `REEL_REGION`：轉輪比對區域（已排除頂部 Jackpot 動畫與底部 UI）
- `SPIN_STABLE_THRESHOLD` / `SPIN_STABLE_CONSECUTIVE`：判定轉輪停止的相似度門檻與連續影格數

## 座標校正

若遊戲版面更動導致點擊或辨識失準，可用校正工具確認座標：

```bash
python calibrate.py
```

會讀取 `screenshots/bet_check_0.png`，在上面畫出目前設定的 OCR 區域（彩色框）與點擊座標（十字標記），輸出至 `screenshots/debug_regions.png`，據此回頭調整 `config/settings.py` 即可。

---

## 設計重點

- **Canvas 影像辨識**：遊戲無 DOM 可定位，改以比例座標點擊搭配 OCR／OpenCV 讀畫面。
- **轉輪停止偵測**：先固定等待 3 秒確保數值落定，再用像素差異比對連續影格確認靜止；中獎動畫會無限循環，逾時則直接以最後影格讀值（此時數值已正確）。
- **對話框處理**：偵測「連線異常」等對話框的綠色確認鈕並自動關閉，重置比對基準後續測。
- **斷線容錯**：瀏覽器 session 失效時中止後續輪次並將剩餘項次標記為 FAIL，仍會產出報告。
- **OCR 強健性**：4 倍放大 + Otsu 反相二值化 + 膨脹提升辨識率；偵測到漏讀小數點時自動補回兩位小數。
- **CJK 路徑相容**：以 `np.fromfile` + `cv2.imdecode` 取代 `cv2.imread`，避免中文路徑讀檔失敗。
