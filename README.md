# Slot 游戏自动化金流测试

针对 H5 老虎机游戏的自动化测试框架，通过 **Selenium** 操作游戏、**OpenCV** 检测转轮停止、**EasyOCR** 识别画面数值，自动执行连续 Spin 并验证每一轮的金流计算是否正确，最后输出含截图的 Excel 报告。

由于游戏画面是 `<canvas>` 渲染（无 DOM 元素可定位），所有交互均采用「比例坐标点击 + 图像识别」的方式完成。

---

## 测试用例：TC_SLOT_001

> Slot 游戏连续 10 次执行金流验证

**验证公式：**

```
玩家资产(后) == 玩家资产(前) − 押注 + 游戏赢分
```

每一轮 Spin 都会读取上述四个数值并比对，误差在 ±0.5 内视为 `PASS`。

**测试流程：**

1. 将押注金额调整至 `test_data.json` 指定值（自动点击 +/− 并以 OCR 确认）
2. 记录 Spin 前玩家资产
3. 点击 Spin 按钮
4. 以 OpenCV 画面比对等待转轮停止
5. 检测并关闭「连接异常」等对话框
6. 记录 Spin 后赢分与资产
7. 验证金流公式
8. 重复 10 次并输出 Excel 报告（含每轮截图）

---

## 环境需求

- Python 3.8+
- Google Chrome（Selenium 4 内置 driver 自动管理）

## 安装

```bash
pip install -r requirements.txt
```

主要依赖：

| 套件 | 用途 |
| --- | --- |
| `selenium` | 浏览器自动化、canvas 坐标点击 |
| `opencv-python` | 转轮停止检测、对话框检测、图像预处理 |
| `easyocr` | 识别资产／押注／赢分数值 |
| `openpyxl` | 生成 Excel 报告（含内嵌截图） |
| `pytest` | 测试执行框架 |

## 运行

```bash
pytest tests/test_slot.py -s
```

> ⚠️ 必须加上 `-s`，因为测试开始时需要**手动登录**（含图形验证码与短信 OTP），程序会暂停并等待你按 Enter。

运行步骤：

1. 程序自动打开浏览器并跳转游戏页
2. 按画面提示**手动完成登录**并进入老虎机画面
3. 确认画面停在有转轮的游戏页后，按 **Enter** 继续
4. 程序自动设置押注、连续 Spin 并验证金流
5. 结束后于 `reports/` 获取 Excel 报告

## 输出

| 目录 | 内容 |
| --- | --- |
| `screenshots/` | 各轮 Spin 前后截图、转轮检测帧、校准图 |
| `reports/` | `slot_test_YYYYMMDD_HHMMSS.xlsx` 金流验证报告（PASS 绿／FAIL 红，内嵌截图） |

两个目录均已列入 `.gitignore`，不会进版本控制。

---

## 项目结构

```
.
├── conftest.py            # pytest fixtures：driver 启动、手动登录引导
├── calibrate.py           # 坐标校准工具，在截图上画出 OCR 区域与点击点
├── requirements.txt
├── config/
│   └── settings.py        # 游戏 URL、比例坐标、OCR 区域、检测参数
├── data/
│   └── test_data.json     # 目标押注、执行次数、Spin 间隔
├── pages/
│   └── slot_page.py       # Page Object：点击、读值、设置押注、关闭对话框
├── tests/
│   └── test_slot.py       # TC_SLOT_001 主测试
└── utils/
    ├── cv_helper.py       # OpenCV 转轮停止检测
    ├── ocr_helper.py      # EasyOCR 数值识别与预处理
    └── report_helper.py   # 金流验证与 Excel 报告生成
```

## 配置说明

### `data/test_data.json`

```json
{
    "target_bet": 100.0,       // 目标押注金额
    "test_iterations": 10,     // Spin 次数
    "spin_delay_min": 3.0,     // 每轮前随机延迟下限（秒）
    "spin_delay_max": 6.0      // 每轮前随机延迟上限（秒）
}
```

### `config/settings.py`

所有坐标均以 **canvas 宽／高比例**（0.0~1.0）表示，与分辨率无关：

- `SPIN_BUTTON_POS` / `BET_PLUS_POS` / `BET_MINUS_POS`：按钮点击坐标
- `OCR_REGIONS`：资产／赢分／押注的识别区域
- `REEL_REGION`：转轮比对区域（已排除顶部 Jackpot 动画与底部 UI）
- `SPIN_STABLE_THRESHOLD` / `SPIN_STABLE_CONSECUTIVE`：判定转轮停止的相似度阈值与连续帧数

## 坐标校准

若游戏版面变动导致点击或识别失准，可用校准工具确认坐标：

```bash
python calibrate.py
```

会读取 `screenshots/bet_check_0.png`，在上面画出当前设置的 OCR 区域（彩色框）与点击坐标（十字标记），输出至 `screenshots/debug_regions.png`，据此回头调整 `config/settings.py` 即可。

---

## 设计要点

- **Canvas 图像识别**：游戏无 DOM 可定位，改以比例坐标点击搭配 OCR／OpenCV 读画面。
- **转轮停止检测**：先固定等待 3 秒确保数值落定，再用像素差异比对连续帧确认静止；中奖动画会无限循环，超时则直接以最后一帧读值（此时数值已正确）。
- **对话框处理**：检测「连接异常」等对话框的绿色确认按钮并自动关闭，重置比对基准后继续测试。
- **断线容错**：浏览器 session 失效时中止后续轮次并将剩余项标记为 FAIL，仍会生成报告。
- **OCR 健壮性**：4 倍放大 + Otsu 反相二值化 + 膨胀提升识别率；检测到漏读小数点时自动补回两位小数。
- **CJK 路径兼容**：以 `np.fromfile` + `cv2.imdecode` 取代 `cv2.imread`，避免中文路径读取失败。
