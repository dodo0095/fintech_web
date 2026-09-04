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

## 八、追加查核：站台導覽列整合（決策書 T4）

L1 複查發現：既有 7 個頁面（bot / botAbout / botBasicHistory / botTechnicHistory /
watchCenter / index / botBlog）的站台導覽列**皆未加入「消息面 → news.html」連結**，
與決策書 T4「併入站台導覽列 / 既有頁面導覽列加『消息面』連結」不一致。

- news.html **自身已具備**「← 回 StarkLab 首頁」回連（`news.html:37`），reciprocal 導覽無缺。
- 站台既有導覽列存在**兩種並存設計**（舊版 icon 式 5 頁、新版純文字 2 頁），
  且彼此連結集合已不一致（處於改版過渡）。
- **老闆裁示（2026-09-04）**：news.html 與其他頁面之間的導覽互連 **暫緩不做**。

> 據此，T4「站台導覽列整合」列為**老闆明確暫緩項（deferred）**，非缺陷、**不計入本 Gate**。
> news.html 目前以直達網址（/news.html）與自身回首頁連結運作，功能完整。

## 九、PM 審核（6 項 checklist）

> ⚠️ 流程註記：本環境 `product-manager` agent 無法連線，經**老闆授權由 L1 代行 PM 審核**。
> 待 PM 上線後可複核本節。

| # | 檢查項 | L1 代行結論 |
|---|--------|------------|
| 1 | 交付物完整性 | ✅ models / fetchers / `update_news` / DRF views·urls / admin / 前端 news.html / 排程腳本（`register_news_tasks.ps1`+`update_news.ps1`）/ 測試 / README 皆齊全 |
| 2 | 數據正確性 | ✅ 15 tests OK（實跑）、news/urls.py 實測 13 路由、system check 0 issues，報告數字與實際一致 |
| 3 | 驗收標準對照 | ✅ T1 models／T2 fetchers+command／T3 DRF／T4 前端頁面（導覽互連除外，已暫緩）／T5 排程／T6 Review 皆達成 |
| 4 | 流程合規 | ✅ 0 Blocker/Major 才提 Gate；PM 步驟因 agent 不可達由老闆授權 L1 代行，已註記 |
| 5 | 計畫書紀錄 | ⚠️ 本 worktree 無 sprint 開發計畫書，改以本審查記錄（`docs/reviews/`）留存備查 |
| 6 | 附帶問題 | ✅ M1 已修（commit a4d7f1a）；M2/M3 登 backlog；T4 導覽互連經老闆裁示暫緩 |

**PM（L1 代行）建議**：**通過**。

## 十、Gate 判定

- 範圍內 0 🔴 Blocker + 0 🟠 Major → **Code Review 通過**，Gate G2 **通過**。
- 測試全綠、覆蓋核心邏輯與 API 邊界 → 同時滿足 G3 測試驗收要件。
- M1 已修；M2/M3 為專案既有遺留登 backlog；T4 導覽互連為老闆暫緩項 —— 皆不阻斷本 Gate。

**L1 最終結論**：✅ **Gate G2 通過**（PM 由 L1 代行審核並建議通過，老闆授權在案）。
