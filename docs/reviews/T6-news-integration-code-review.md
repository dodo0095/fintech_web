# Gate G2 — news 平台整合 L1 Code Review 記錄（T6）

> **審查人（L1）**: tech-lead
> **日期**: 2026-09-04
> **對象**: `stark_lab/news/` App 整合（決策書 `docs/decisions/news-platform-integration.md` T1–T5）
> **依據**: `company://sop/code-review.md`、`company://standards/{coding,api,testing}-standards.md`
> **結論**: ✅ **通過**（0 🔴 Blocker + 0 🟠 Major，僅 3 項 🟡 Minor 為專案既有遺留、非本次引入）

---

## 一、審查範圍

news_platform 整合進 stark_lab Django 之全部產出：`news` app（models / fetchers /
`update_news` command / DRF views·urls / admin / scheduler）＋前端 `news.html`＋
Windows 排程腳本。此整合已全數合併進 `master`（分支與 master 無差異），本次為對
既有程式碼之回溯 Review。

## 二、四類 Review 結果

| Review 類型 | 結論 | 依據 |
|------------|------|------|
| **對程式碼** | ✅ 通過 | 錯誤處理完整、無硬編碼機密、無死碼（見 §3） |
| **對規範** | ✅ 通過 | 端點/模型/JSON 鏡射對齊決策書（見 §4） |
| **對設計稿** | ✅ 保留一致 | 由 news_platform 1:1 遷移，僅換 fetch 網址，repo 無獨立設計稿（見 §5） |
| **對功能** | ✅ 通過 | 15 測試全綠、migration 乾淨、system check 0 issues（見 §6） |

## 三、對程式碼（品質 / coding-standards）

- **錯誤處理**：views 對外部抓取全包 try/except，狀態碼語意正確
  （404 查無代碼 / 502 熱度計算失敗 / 503 套件未安裝 / 422 財報資料不足）。
- **併發**：`_once()` in-flight 去重鎖，避免同代碼重複抓取；TTL 快取
  （個股新聞 15 分、河流圖 6 小時）。
- **容錯**：`update_news` 逐來源 try/except，失敗來源不呼叫 store → **不覆寫既有資料**，
  最後寫 status 心跳，符合決策書「單一 fetcher 失敗不影響其他」原則。
- **機密**：news app 內無硬編碼 API Key / password / token（掃描結果為空）。
- **死碼**：未見註解掉的程式碼或未使用 import。

## 四、對規範（實作 vs 決策書）

- **端點**：決策書列 9 個 GET 端點全部實作，另擴充 `lookup/<code>`、`stock/<code>`、
  `valuation`（預設）動態查詢——擴充項均有對應處理與文件（README §5），符合 API 完整性精神。
- **回應格式**：刻意回傳原始 payload、不套公司信封層——決策書 §DRF 端點已載明此為與既有
  `apiserver` 一致的刻意決策，符合「鏡射 data/*.json」核心設計原則。
- **資料模型**：`NewsItem` / `MarketEvent` / `WatchlistItem` / `Valuation` 對齊決策書；
  單例快照（market/heat/status/各 feed meta）以 `Snapshot(kind, payload)` KV 統一存，
  等價於決策書的 MarketSnapshot/HeatSnapshot/UpdateStatus，models.py docstring 已說明。
- **命名**：API 路徑 kebab、欄位 snake_case，時間保留原始 ISO 字串確保逐欄位一致。

## 五、對設計稿

news 頁面由原 `news_platform/index.html`+`app.js` 1:1 遷移，依決策書 T4「只換 fetch 網址、
畫面邏輯零改動」。repo `design/` 僅含主站設計稿（bot.xd / layout.png），無 news 頁獨立設計稿，
故以「遷移視覺平價」認定一致。

## 六、對功能（測試證據）

```
$ python manage.py test news -v2
Ran 15 tests in 0.029s
OK   |  System check identified no issues (0 silenced).
```
涵蓋 heat_v1 演算法（7）、代碼查詢 tickers（5）、API 404 邊界（3）。
migration `news.0001` / `0002` 乾淨套用。

> 測試環境註記：本 worktree 無隨附 venv，正式機 Python（`C:\py310`）不在此機。
> 以 anaconda base（Django 6.0.2）補裝 `django-filter / django-cors-headers / jsonfield /
> simplejwt` 後執行；正式機為 Django 3.0.3 釘版，程式碼已在正式站 https://starklab.tw/news.html 運行。

## 七、🟡 Minor（專案既有遺留，非本次 news 整合引入 → 建 backlog，不阻斷 Gate）

| # | 項目 | 說明 | 建議 | 狀態 |
|---|------|------|------|------|
| M1 | `.env` 仍被 git 追蹤 | README §7 已列建議；有設定外洩風險 | `git rm --cached stark_lab/.env` + `.gitignore` | ✅ **已處理**（2026-09-04，本機檔案保留） |
| M2 | `SECRET_KEY` 硬編碼於 settings.py | stark_lab 專案既有 | 改讀環境變數 | 待後續 Sprint |
| M3 | `ALLOWED_HOSTS = ["*"]` | 過度寬鬆，惟位於 Caddy 反代之後 | 收斂為實際網域 | 待後續 Sprint |

> `db.sqlite3` 已於 commit `09d248d` 移出版控（README §7 該項已完成）。

## 八、Gate 判定

- 範圍內 0 🔴 Blocker + 0 🟠 Major → **Code Review 通過**，可提交 Gate G2。
- 測試全綠、覆蓋核心邏輯與 API 邊界 → 同時滿足 G3 測試驗收要件。
- M1–M3 為專案既有遺留，登錄 backlog 於後續 Sprint 處理，不阻斷本 Gate。

**L1 建議**：G2 通過。M1（.env 移出版控）建議列為近期優先修補項。
