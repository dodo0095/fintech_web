# 策略回測實驗室（/backtest/）— 規劃與現況

> 負責：project-lead　建立：2026-09-27
> 取代舊版 `twbacktest`（依賴外部 `snr_backtest` 資料夾與寫死的 AUSER 路徑，正式站無法運作，已移除）。

## 目標

讓使用者**自己選台股／ETF、自己組進出場規則**，免寫程式即可在 starklab.tw 回測歷史績效。

## 已交付（Phase 1 MVP）

| 項目 | 位置 |
|------|------|
| 回測引擎（純函式、可單測） | `stark_lab/backtest/engine/`（indicators / rules / simulator / metrics） |
| 行情層：yfinance 還原權息 + SQLite 快取（6 小時） | `stark_lab/backtest/prices.py`、`models.PriceCache` |
| API：頁面、股票搜尋、執行回測 | `stark_lab/backtest/views.py`、`urls.py` |
| 策略範本 6 組 | `stark_lab/backtest/presets.py` |
| 前端（主站色票、echarts） | `backtest/templates/backtest/index.html`、`frontend/build/static/backtest/` |
| ETF 名單（原公司清單沒有 ETF） | `公司/ETF上市.csv`、`公司/ETF上櫃.csv`，`python manage.py refresh_etf_list` 更新 |
| 測試 | `backtest/tests/test_engine.py`（pytest 14 項）、`test_api.py`（Django 15 項） |

### 設計決策

- **策略 = JSON 規則積木**，後端白名單驗證（指標、運算子、參數範圍），不執行任何使用者程式碼。
- **撮合**：T 日收盤確認訊號 → T+1 開盤成交；停損／停利盤中觸價（跳空以開盤價）；同日同時觸及時保守先算停損；一字漲停買不到、一字跌停賣不掉。
- **成本**：手續費 0.1425% × 折扣（最低 20 元）、證交稅 股票 0.3%／ETF 0.1%、單邊滑價（預設 0.1%）。
- **比較基準**：同檔買進持有 + 0050。
- **防護**：CSRF、每 IP 10 分鐘 30 次、同時最多 3 個回測（waitress 12 threads）、請求 32KB 上限、回測區間 ≥ 2 個月。
- **分享**：策略與設定編碼在網址 `#r=...`，開啟即重現結果。

### 已知限制（對使用者揭露於頁尾）

- Yahoo 資料可能延遲或有誤；未考慮處置股、流動性不足。
- 只有「單一標的、全進全出、只做多」。
- 倖存者偏差：已下市股票不在清單內。

## 後續規劃

| 階段 | 內容 | 優先 |
|------|------|------|
| Phase 2 | 多檔投組回測（等權、持股上限）、做空／融資、定期定額比較 | 高 |
| Phase 2 | 指標擴充：乖離率、ATR 停損、週線/月線條件、法人買賣超（需 TWSE 資料源） | 中 |
| Phase 2 | 行情改由每日排程預抓熱門股（降低 Yahoo 依賴），加 TWSE/TPEX 官方價比對 | 中 |
| Phase 3 | 會員：儲存策略、歷史紀錄、分級次數 | 視商業需求 |
| Phase 3 | 參數最佳化 + walk-forward 驗證與過度擬合警示 | 視商業需求 |

## 部署步驟（正式站）

1. **先備份 caddy.exe**，再 pull：之後一律用 repo 根目錄 `safe-pull.bat`（見該檔說明）。
2. `pip install -r stark_lab/requirements.txt`（本次無新增套件）。
3. 重啟 `serve.py`（會自動 `migrate`＋`collectstatic`，建立 `backtest_pricecache` 表、發布 `static/backtest/`）。
4. 開 https://starklab.tw/backtest/ 跑一次預設策略確認。
