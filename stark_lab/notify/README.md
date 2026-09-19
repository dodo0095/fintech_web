# notify app — 每日盤勢通報系統

每個時點掃描全部啟用標的，抓日線 → 用 8 個技術指標判定多空訊號 → 防抖動去重 →
組訊息 → 推 Discord。核心流程在 `runner.run_market`，指標判定在 `indicators.evaluate`，
訊息組裝在 `messaging.py`，文案與參數集中在 `constants.py`。

本文件說明**訊號策略規則**（8 指標意義、盤整過濾、衝突明示與可調參數）。
文件與程式碼必須一致；改參數/規則時請同步更新此檔。

---

## 一、8 個技術指標

每個指標**獨立判定、不做綜合**。交叉類以最近兩根 K 線判定（前根未成立、當根成立），
避免持續狀態重複觸發。判定邏輯見 `indicators.evaluate()`，參數見 `constants.py`。

| 代碼 | 名稱 | 類型 | 多方觸發 | 空方觸發 |
|------|------|------|----------|----------|
| `ma` | 均線交叉 | 交叉/趨勢 | MA5 上穿 MA20（黃金交叉） | MA5 下穿 MA20（死亡交叉） |
| `ema` | 指數均線交叉 | 交叉/趨勢 | EMA12 上穿 EMA26 | EMA12 下穿 EMA26 |
| `macd` | MACD 柱狀圖 | 交叉/趨勢 | 柱狀圖由負轉正 | 柱狀圖由正轉負 |
| `kd` | KD 隨機指標 | 交叉/趨勢 | 低檔(<20) K 上穿 D | 高檔(>80) K 下穿 D |
| `tower` | 寶塔線 | 交叉/趨勢 | 翻紅（突破前 N 根收盤高點） | 翻黑（跌破前 N 根收盤低點） |
| `rsi` | 相對強弱 | 均值回歸 | RSI < 30（超賣） | RSI > 70（超買） |
| `bias` | 乖離率 | 均值回歸 | BIAS(10) ≤ −5%（跌深） | BIAS(10) ≥ +5%（漲多） |
| `bollinger` | 布林通道 | 均值回歸 | 收盤觸及/跌破下軌(−2σ) | 收盤觸及/突破上軌(+2σ) |

- **交叉/趨勢型**（`ma, ema, macd, kd, tower`）：偵測方向轉折，趨勢明確時準確、盤整時易來回假訊號。
- **均值回歸型**（`rsi, bias, bollinger`）：偵測價格偏離均值的極端，盤整時仍具參考價值。

---

## 二、A. 盤整過濾（ADX trend filter）

**問題**：盤整（無趨勢）時，交叉類指標會來回假訊號（whipsaw）——前一日喊買、隔日喊賣，自相矛盾。

**做法**：用 ADX(14) 判斷是否處於盤整。

- **ADX 演算法**（Wilder 標準，`indicators.compute_adx`）：
  - `TR = max(high−low, |high−prev_close|, |low−prev_close|)`
  - `+DM / −DM` 標準定義；以 Wilder 平滑（EMA `alpha=1/period, adjust=False`）得 ATR、+DI、−DI
  - `DX = 100 × |(+DI)−(−DI)| / ((+DI)+(−DI))`；`ADX = Wilder 平滑(DX)`
  - 回傳最後一根 ADX。**趨勢明確時 ADX 高、盤整時 ADX 低。**
- **過濾規則**：當 `ADX < ADX_RANGING_THRESHOLD`（預設 25，視為盤整）時，
  **壓制交叉/趨勢型訊號**（`ma, ema, macd, kd, tower`），
  **保留均值回歸型**（`rsi, bias, bollinger`）。
- **安全降級**：ADX 無法計算（資料不足、或完全無波動導致除零）時回 `None`，**不啟用過濾**（回傳全部訊號）。
- **開關**：由 `settings.RANGING_FILTER_ENABLED` 控制（預設啟用）。
  `indicators.evaluate()` 不依賴 Django settings、可獨立測試；`runner` 從 settings 讀
  `RANGING_FILTER_ENABLED` 與 `ADX_RANGING_THRESHOLD` 後傳入
  `evaluate(df, ranging_filter=..., adx_threshold=...)`。

---

## 三、D. 衝突明示

同一標的本次**同時出現多方與空方新訊號**時（買/賣分組皆非空），
在該標的訊息區塊尾端加註提醒（`constants.CONFLICT_NOTE`：`⚠️ 盤整訊號分歧，建議觀望`）。
實作於 `messaging.build_message`。**加註不取代原本的買進/賣出分組顯示**，僅附加一行提醒。

---

## 四、可調參數

| 參數 | 位置 | 預設 | 說明 |
|------|------|------|------|
| `ADX_PERIOD` | `constants.py` | 14 | ADX 計算週期（Wilder） |
| `ADX_RANGING_THRESHOLD` | `constants.py` / `settings.py` | 25 | ADX 低於此值視為盤整、啟動交叉類過濾 |
| `TREND_INDICATORS` | `constants.py` | `{ma, ema, macd, kd, tower}` | 盤整時被壓制的交叉/趨勢型指標集合 |
| `RANGING_FILTER_ENABLED` | `settings.py`（env） | `True` | 盤整過濾總開關 |
| `CONFLICT_NOTE` | `constants.py` | — | 多空並存時的加註文案 |

環境變數（`.env` 或系統環境變數）：
- `RANGING_FILTER_ENABLED`：`1/true/yes/on` 開，其餘關（預設開）。
- `ADX_RANGING_THRESHOLD`：浮點數，覆寫盤整閾值（預設 25）。

其餘既有指標參數（`MA_FAST`、`RSI_PERIOD`、`KD_PERIOD` 等）見 `constants.py` 開頭「指標參數」段。

### 實務調參指南

盤整過濾預設就是開的（`RANGING_FILTER_ENABLED=true`、閾值 25），一般不用動。
上線觀察幾天後，再依實際感受微調——**改 `.env` 後重啟排程器即生效**。

**`ADX_RANGING_THRESHOLD`（盤整判定門檻）**——關鍵在「數字越高＝越容易被判為盤整＝過濾越多交叉類訊號」：

| 情境 | 怎麼調 | 效果 |
|------|--------|------|
| 覺得「多空還是常常打架、假訊號多」 | **調高**，如 `30`、`35` | 更多時候被視為盤整 → 壓掉更多交叉類訊號 → 通知更保守、更少 |
| 覺得「訊號變太少、常常整天沒動靜」 | **調低**，如 `20`、`15` | 更少被視為盤整 → 保留更多交叉類訊號 → 通知更靈敏、更多 |
| 完全不想要盤整過濾（回到原始行為，8 指標照跑） | `RANGING_FILTER_ENABLED=false` | 關閉過濾，`ADX_RANGING_THRESHOLD` 失效 |

> 記憶法：**門檻越低 → 過濾越少 → 訊號越多**；**門檻越高 → 過濾越多 → 訊號越少**。
> 25 是業界通用的「有無趨勢」分界，建議以此為基準小幅增減（±5），不要一次調太大。

`.env` 範例：
```
# 想更保守（過濾更多假訊號）
ADX_RANGING_THRESHOLD=30

# 想更靈敏（保留更多交叉訊號）
ADX_RANGING_THRESHOLD=20

# 完全關閉盤整過濾
RANGING_FILTER_ENABLED=false
```

---

## 五、測試

pytest-style（需 `pytest-django`）。設定環境變數後執行：

```bash
export SECRET_KEY=temp-verify-key
export DJANGO_SETTINGS_MODULE=stark_lab.settings
python -m pytest notify/tests/ -q
```

> 註：notify 測試為 pytest 函式風格（非 `unittest.TestCase`），且 `conftest.py` 使用
> pytest-django 的 `settings` fixture 與 `django_db` marker，故 `python manage.py test notify`
> 會回報「0 tests」（Django 內建 runner 只收集 TestCase）。請用 `pytest` 執行。

相關測試：`test_indicators.py`（ADX 計算、盤整過濾）、`test_messaging.py`（衝突明示）。
