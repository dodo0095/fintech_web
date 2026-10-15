# notify app — 每日盤勢通報系統

每個時點掃描全部啟用標的，抓日線 → 用 8 個技術指標判定多空訊號 → 防抖動去重 →
組訊息 → 推 Discord。核心流程在 `runner.run_market`，指標判定在 `indicators.evaluate`，
訊息組裝在 `messaging.py`，文案與參數集中在 `constants.py`。

本文件說明**訊號策略規則**（8 指標意義、盤整標註/過濾、衝突明示與可調參數）。
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

- **交叉/趨勢型**（`ma, ema, macd, kd, tower`）：偵測方向轉折，趨勢明確時準確、盤整時易來回假訊號
  （盤整時預設照推但標註「盤整中・僅供參考」，見下節）。
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
- **盤整判定**：`RANGING_FILTER_ENABLED=true` 且 ADX 可算出且 `ADX < ADX_RANGING_THRESHOLD`
  （預設 25）時視為盤整。均值回歸型（`rsi, bias, bollinger`）**一律不受影響**。
- **盤整時的處理**（`RANGING_FILTER_MODE`，只影響交叉/趨勢型 `ma, ema, macd, kd, tower`）：
  - **`tag`（預設，降級標註）**：訊號**照推**，`Signal.ranging=True`（`detail` 不變）。訊息中該行
    白話主標後加 `constants.RANGING_TAG`（` （盤整中・僅供參考）`）；若該標的**全部**訊號都是
    盤整標註，區塊尾再加 `constants.RANGING_NOTE`
    （`ℹ️ 目前趨勢不明顯（盤整），交叉類訊號容易反覆，僅供參考`），
    且「今日訊號摘要」方向後加 `constants.SUMMARY_RANGING_SUFFIX`（例：`偏空・參考`）。
  - **`suppress`（直接刪除）**：舊行為，盤整時這些訊號整筆移除、不推也不記 SignalLog。
- **為何預設改為 tag**：ADX 長期偏低的行情（例如 S&P 500 ADX 約 9~13）下，`suppress` 會把
  多數交叉訊號砍掉，使用者連日只收到「今日無指標訊號」；`tag` 保留資訊、交由使用者判讀。
- **安全降級**：ADX 無法計算（資料不足、或完全無波動導致除零）時回 `None`，**不判盤整**
  （回傳全部訊號、不標註）。
- **三種組合**：

  | 設定 | 盤整時交叉類訊號 |
  |------|------------------|
  | `RANGING_FILTER_ENABLED=true`＋`RANGING_FILTER_MODE=tag`（預設） | 照推＋標註「盤整中・僅供參考」 |
  | `RANGING_FILTER_ENABLED=true`＋`RANGING_FILTER_MODE=suppress` | 直接刪除（最保守、訊號最少） |
  | `RANGING_FILTER_ENABLED=false` | 完全不判盤整，照推且不標註（原始行為；MODE 與閾值失效） |

- **實作分工**：`indicators.evaluate()` 不依賴 Django settings、可獨立測試；`runner` 從 settings 讀
  `RANGING_FILTER_ENABLED`、`ADX_RANGING_THRESHOLD`、`RANGING_FILTER_MODE` 後傳入
  `evaluate(df, ranging_filter=..., adx_threshold=..., ranging_mode=...)`；
  `ranging_mode` 只接受 `"tag"`/`"suppress"`，其他值拋 `ValueError`（settings 端已把非法值回落 `tag`）。

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
| `ADX_RANGING_THRESHOLD` | `constants.py` / `settings.py` | 25 | ADX 低於此值視為盤整 |
| `TREND_INDICATORS` | `constants.py` | `{ma, ema, macd, kd, tower}` | 盤整時被標註/壓制的交叉/趨勢型指標集合 |
| `RANGING_FILTER_ENABLED` | `settings.py`（env） | `True` | 盤整判定總開關；`False`＝完全不判盤整 |
| `RANGING_FILTER_MODE` | `settings.py`（env） | `tag` | 盤整時處理方式：`tag` 標註照推／`suppress` 刪除 |
| `RANGING_TAG` / `RANGING_NOTE` | `constants.py` | — | 盤整標註的行內加註／區塊尾說明文案 |
| `SUMMARY_RANGING_SUFFIX` | `constants.py` | `・參考` | 該檔訊號全為盤整標註時，摘要方向的後綴 |
| `CONFLICT_NOTE` | `constants.py` | — | 多空並存時的加註文案 |

環境變數（`.env` 或系統環境變數）：
- `RANGING_FILTER_ENABLED`：`1/true/yes/on` 開，其餘關（預設開）。
- `ADX_RANGING_THRESHOLD`：浮點數，覆寫盤整閾值（預設 25）。
- `RANGING_FILTER_MODE`：`tag`（預設）或 `suppress`，不分大小寫；其他值回落 `tag`。

其餘既有指標參數（`MA_FAST`、`RSI_PERIOD`、`KD_PERIOD` 等）見 `constants.py` 開頭「指標參數」段。

### 實務調參指南

預設為「盤整判定開、標註模式」（`RANGING_FILTER_ENABLED=true`、`RANGING_FILTER_MODE=tag`、閾值 25）：
盤整時交叉類訊號**照推但標註「盤整中・僅供參考」**，不會再整天只收到「今日無指標訊號」。
上線觀察幾天後，再依實際感受微調——**改 `.env` 後重啟排程器即生效**。

**先選模式（`RANGING_FILTER_MODE` / `RANGING_FILTER_ENABLED`）**：

| 情境 | 怎麼設 | 效果 |
|------|--------|------|
| 想看到所有訊號，但知道哪些是盤整中的（建議） | `RANGING_FILTER_MODE=tag`（預設） | 交叉類照推，盤整時加註「僅供參考」；摘要方向標「・參考」 |
| 覺得「盤整時的交叉訊號太吵、寧可少收」 | `RANGING_FILTER_MODE=suppress` | 盤整時交叉類直接刪除 → 通知最保守、最少（ADX 長期偏低時可能連日無訊號） |
| 完全不想判盤整（回到原始行為，8 指標照跑、不標註） | `RANGING_FILTER_ENABLED=false` | 不算 ADX、不標註也不刪除，`MODE` 與 `ADX_RANGING_THRESHOLD` 失效 |

**再調門檻（`ADX_RANGING_THRESHOLD`）**——數字越高＝越容易被判為盤整：

| 情境 | 怎麼調 | 效果（tag 模式／suppress 模式） |
|------|--------|------|
| 覺得「多空還是常常打架、假訊號多」 | **調高**，如 `30`、`35` | 更多交叉類被標註為參考／被刪除 → 更保守 |
| 覺得「盤整標註太多」或（suppress 下）「訊號太少」 | **調低**，如 `20`、`15` | 更少被視為盤整 → 更多交叉類以正常訊號呈現 |

> 記憶法：**門檻越高 → 越常被判盤整**（tag：標註越多；suppress：訊號越少）。
> 25 是業界通用的「有無趨勢」分界，建議以此為基準小幅增減（±5），不要一次調太大。

`.env` 範例：
```
# 預設：盤整時照推但標註僅供參考
RANGING_FILTER_MODE=tag

# 想更保守：盤整時直接刪除交叉類訊號
RANGING_FILTER_MODE=suppress

# 調整盤整判定門檻（越高越常被判為盤整）
ADX_RANGING_THRESHOLD=30

# 完全關閉盤整判定（原始行為）
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

相關測試：`test_indicators.py`（ADX 計算、盤整標註/過濾）、`test_messaging.py`（衝突明示、
盤整標註文案）、`test_run_notify.py`（摘要「・參考」標註）。
