# news app — 消息面收集平台

掛在 stark_lab Django 上的分頁 `/news.html`，資料來自 `/api/news/*`。
由獨立專案 `news_platform` 整合而來，架構決策見 `docs/decisions/news-platform-integration.md`。

- **正式站**：https://starklab.tw/news.html
- **部署機路徑**：`C:\server website\fintech_web`（Caddyfile 在此）、`C:\server website\fintech_web\stark_lab`（Django）
- **部署機 Python**：`C:\py310\python.exe`

---

## 一、這是什麼（資料流）

```
Windows 工作排程（每天 04:00 / 08:00 / 14:00 / 20:00）
  → scripts\update_news.ps1 → python manage.py update_news
    → news\fetchers\*（yfinance 報價 + 鉅亨/Google RSS 新聞 + 自動摘要）
      → 寫入 DB（news app models）
        → DRF /api/news/*（回傳 JSON）
          → /news.html + /static/news/app.js（ECharts 繪製儀表板）
```

自動更新的 8 個來源：market（市場）、headlines（美股新聞）、tsmc（台積電新聞）、
fed（聯準會）、valuation（河流圖 4 檔）、events（關注事件）、heat（消息面熱度）、
summary（一早摘要/今日盤勢，依市場數據自動生成）。

> ⚠️ 新聞類（headlines/tsmc/fed）靠外部 RSS，偶爾抓不到會保留上次資料、不中斷；
> market/valuation/events/heat/summary 只要 yfinance 正常就一定有。

---

## 二、每次要做的事（日常操作）⭐

### A. 只是想「更新資料」（不改程式）
平常交給排程自動跑。要手動立即更新：
```bat
cd "C:\server website\fintech_web\stark_lab"
C:\py310\python.exe manage.py update_news
```
看到 `=== done: ?/8 ok ===` 即完成（新聞來源偶爾失敗屬正常）。

### B. 改了程式碼、要「部署上線」
```bat
cd "C:\server website\fintech_web"
git pull                                        :: 1) 取最新程式

cd stark_lab
C:\py310\python.exe manage.py migrate           :: 2) 有改 models 才需要，沒改也無妨
C:\py310\python.exe manage.py collectstatic --noinput   :: 3) 有改 css/js/圖 才需要（改前端一定要跑）

:: 4) 重啟 Django（服務 :8000 的 waitress），讓新程式生效

:: 5) 有改 Caddyfile 才需要：
cd "C:\server website\fintech_web"
caddy reload --config Caddyfile
```
> 判斷口訣：**改前端(css/js/html) → 一定要 collectstatic**；**改 Caddyfile → 一定要 caddy reload**；
> **改任何 .py → 一定要重啟 Django**。

### C. 瀏覽器看不到最新畫面
按 **Ctrl+F5** 強制重載（清快取）。

---

## 三、自動排程（一次性設定）⭐

讓系統每天 4 次自動更新資料。**只需設定一次**。

```bat
:: 以「系統管理員」開 PowerShell，在 stark_lab 目錄執行：
cd "C:\server website\fintech_web\stark_lab"
powershell -ExecutionPolicy Bypass -File scripts\register_news_tasks.ps1
```

會建立 4 個 Windows 工作：`StarkLabNews_0400 / 0800 / 1400 / 2000`，
每次呼叫 `scripts\update_news.ps1` → `manage.py update_news`，
並把輸出寫入 `logs\news-update-YYYY-MM-DD.log`。

- 更新腳本會自動用 `C:\py310\python.exe`（`scripts\update_news.ps1` 已內建偵測；
  若你的 Python 在別處，設環境變數 `STARKLAB_PYTHON` 指定）。
- **時段意義**：04:00 美股收盤後 / 08:00 台股開盤前 / 14:00 台股收盤後 / 20:00 美股開盤前。

### 排程驗證 / 管理
```bat
:: 手動測跑一次（等同排程會做的事）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\update_news.ps1
type logs\news-update-%date:~0,4%-%date:~5,2%-%date:~8,2%.log   :: 看當天 log

:: 查看 4 個工作狀態
schtasks /Query /TN StarkLabNews_0400
schtasks /Query /TN StarkLabNews_0800
schtasks /Query /TN StarkLabNews_1400
schtasks /Query /TN StarkLabNews_2000

:: 立即觸發其中一個（測試）
schtasks /Run /TN StarkLabNews_0800

:: 移除全部（如需停用）
schtasks /Delete /TN StarkLabNews_0400 /F  （其餘同理）
```

---

## 四、首次啟用 / 資料是空的時候

news 資料表若為空（例如剛換 DB），跑一次即可灌滿：
```bat
cd "C:\server website\fintech_web\stark_lab"
C:\py310\python.exe manage.py update_news
```
（不需要 `import_news_json`——那只給有舊 `news_platform/data` JSON 的開發機用。）

---

## 五、API 端點

| 路徑 | 內容 |
|------|------|
| `GET /api/news/market` | 市場總覽（美股+台股+ADR 溢價） |
| `GET /api/news/headlines` | 美股重大新聞前五 |
| `GET /api/news/tsmc` | 台積電新聞 |
| `GET /api/news/fed` | 聯準會發言（含鷹/鴿） |
| `GET /api/news/heat` | 消息面熱度 |
| `GET /api/news/events` | 關注事件（非農等） |
| `GET /api/news/watchlist` | 河流圖觀察名單 |
| `GET /api/news/summary` | 一早摘要 / 今日盤勢（自動生成） |
| `GET /api/news/status` | 排程心跳（各來源成敗、最後更新） |
| `GET /api/news/valuation` | 預設河流圖（2330） |
| `GET /api/news/valuation/<code>` | 指定代碼河流圖（2330/2317/2454/2308） |

---

## 六、部署踩坑紀錄（重要）

| 問題 | 原因 | 解法 |
|------|------|------|
| `/news.html` 與 `/api/news/*` 全部 404 | Caddy `@dirScan` 反掃描規則把 "news" 當 "new" 命中 → 直接擋掉 | Caddyfile 規則字尾 `\/?` 改 `(\/|$)`（已修，4 個站台區塊都改）；改完 `caddy reload` |
| CSS/JS 掛掉（`/static/news/*` 404） | 沒跑 collectstatic，靜態檔不在 Caddy 服務目錄 | `python manage.py collectstatic --noinput` |
| 「一早摘要/今日盤勢」空白 | 原為人工維護內容，遷移後無來源 | 改由 summary 產生器依市場數據自動生成（已納入 update_news） |
| 新聞 3 來源失敗 `ASN1 NOT_ENOUGH_DATA` | RSS over HTTPS 抓取受環境影響 | 容錯保留舊資料、不中斷；換網路/重試即可 |
| `import yfinance` 在 py38 報 TypeError | `multitasking` 0.0.13+ 需 Python 3.9+ | 釘 `multitasking==0.0.11`（僅 py38 環境需要） |

## 七、強烈建議：db.sqlite3 / .env 移出版控

目前 `db.sqlite3` 與 `.env` 都被 commit 進 repo，導致兩台機器互相覆蓋資料、
且 `.env`（含設定）有外洩風險。建議：
```bat
git rm --cached stark_lab/db.sqlite3 stark_lab/.env
:: 並在 .gitignore 加入：
::   stark_lab/db.sqlite3
::   stark_lab/.env
```
之後兩台機器各自維護 DB 與環境設定，不再互相覆蓋。
