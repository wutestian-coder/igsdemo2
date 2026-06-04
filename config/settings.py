from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

GAME_URL = "https://h5.goodluck777.com/"
LOGIN_TIMEOUT = 180
SPIN_TIMEOUT = 10
SPIN_POLL_INTERVAL = 0.5
SPIN_STABLE_THRESHOLD = 0.88
SPIN_STABLE_CONSECUTIVE = 3

SCREENSHOT_DIR = str(BASE_DIR / "screenshots")
REPORT_DIR = str(BASE_DIR / "reports")

# Canvas 為橫向 1920×870，遊戲直式內容置中於 x=0.384~0.623 之間
# 以下座標皆以 canvas 寬/高比例表示，已根據實際像素掃描校正

# 點擊座標
SPIN_BUTTON_POS = (0.50,  0.91)   # Spin 大圓圈按鈕（中央偏下）
BET_PLUS_POS    = (0.616, 0.81)   # + 按鈕（押注右側，x=0.608~0.624 中心）
BET_MINUS_POS   = (0.554, 0.81)   # - 按鈕（押注左側，x=0.546~0.562 中心）

# OCR 讀取區域 (x1, y1, x2, y2)
# 只取數字行（y=0.800~0.835），排除中文標籤行與 +/- 按鈕
OCR_REGIONS = {
    "balance": (0.380, 0.800, 0.455, 0.835),   # 資産 940.00
    "win":     (0.455, 0.800, 0.535, 0.835),   # 贏分 0.00
    "bet":     (0.562, 0.800, 0.608, 0.835),   # 押注 100.00（排除 +/- 按鈕）
}

# 轉輪偵測區域：排除頂部 Jackpot 動態數字（y<0.15）與底部 UI（y>0.78）
# 只比對轉輪符號格（含佛像背景靜態區），避免動態元素干擾偵測
REEL_REGION = (0.38, 0.15, 0.63, 0.78)
