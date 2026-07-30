# news app — 消息面收集平台（掛載於 stark_lab Django）

由獨立專案 `news_platform`（純靜態頁 + Python 抓取 + Windows 排程）整合而來。
架構決策見 `docs/decisions/news-platform-integration.md`。

## 一句話

市場總覽、重大新聞、本益比/淨值比河流圖、消息面熱度，自動更新、一站呈現。
分頁網址：`/news.html`；資料 API：`/api/news/*`。

## 資料流

```
Windows 工作排程（04:00/08:00/14:00/20:00）
  → scripts\update_news.ps1 → python manage.py update_news
    → news/fetchers/*（yfinance + Google/鉅亨 RSS）
      → news/store.py 寫入 DB（models）
        → DRF /api/news/*（鏡射原 data/*.json，逐欄位一致）
          → frontend/build/news.html + /static/news/app.js（ECharts 繪製）
```

## 元件

| 檔案 | 說明 |
|------|------|
| `models.py` | Snapshot（market/heat/status/summary/各 meta）、NewsItem、MarketEvent、WatchlistItem、Valuation |
| `store.py` | payload ↔ DB 讀寫層；reader 負責重建與原 JSON 逐欄位一致的輸出（含整數保真） |
| `fetchers/` | 自 `news_platform/scripts/` 移植，各 `build()` 回傳 payload（不再寫檔） |
| `views.py` + `urls.py` | DRF 端點，掛在 `/api/news/`，不套公司信封層（比照 apiserver、鏡射原 JSON） |
| `management/commands/update_news.py` | 即時抓取寫 DB（排程呼叫）；`--only` 可指定來源 |
| `management/commands/import_news_json.py` | 從既有 `news_platform/data/*.json` 種子匯入（一次性 bootstrap） |

## API 端點

| 路徑 | 對應原 JSON |
|------|-------------|
| `GET /api/news/market` | market.json |
| `GET /api/news/headlines` | news.json |
| `GET /api/news/tsmc` | tsmc_news.json |
| `GET /api/news/fed` | fed.json |
| `GET /api/news/heat` | heat.json |
| `GET /api/news/events` | events.json |
| `GET /api/news/watchlist` | watchlist.json |
| `GET /api/news/summary` | summary.json |
| `GET /api/news/status` | status.json |
| `GET /api/news/valuation` | valuation.json（預設檔） |
| `GET /api/news/valuation/<code>` | valuation_{code}.json |

## 首次啟用（bootstrap）

```bash
python manage.py migrate news
python manage.py import_news_json          # 匯入既有真實資料（預設讀 news_platform/data）
# 或指定路徑： python manage.py import_news_json --data-dir "D:/path/to/news_platform/data"
```

## 手動更新（即時抓取）

```bash
python manage.py update_news               # 全部來源
python manage.py update_news --only market # 只更新市場
```

## 排程自動更新（Windows）

1. 編輯 `scripts\update_news.ps1`，或設環境變數 `STARKLAB_PYTHON` 指向專案 Python（含 django/yfinance）。
2. 以系統管理員 PowerShell 執行：
   ```
   powershell -ExecutionPolicy Bypass -File scripts\register_news_tasks.ps1
   ```
   會註冊 4 個工作 `StarkLabNews_0400/0800/1400/2000`，每日更新並寫 `logs\news-update-YYYY-MM-DD.log`。

## 部署注意

- **靜態檔**：news 資產在 `frontend/build/static/news/`，屬 `STATICFILES_DIRS`，`collectstatic` 會收進 `STATIC_ROOT`，由 Caddy 服務。部署後記得 `python manage.py collectstatic`。
- **CDN**：頁面用 jsdelivr 的 pico.css 與 echarts（與原站一致），部署機需可連外。
- **DB**：SQLite（`db.sqlite3`），與既有 apiserver 共用同一庫。

## 踩坑紀錄

| 問題 | 原因 | 解法 |
|------|------|------|
| 本機 Django 5.2 跑不起現有站 | `stark_lab/urls.py` 用 Django 4.0 已移除的 `from django.conf.urls import url` | 對齊正式機建 py38 + Django 3.0.3 環境（見決策文件） |
| Django 3.0 無原生 JSONField | 3.1 才有 sqlite JSONField | 用第三方 `jsonfield`（requirements 已有 3.1.0） |
| `import yfinance` 在 py38 TypeError | 依賴 `multitasking` 0.0.13+ 用 `type[...]` 語法需 3.9+ | 釘 `multitasking==0.0.11` |
| runserver 靜態 404 | `DEBUG=False` 時 runserver 不服務靜態 | 本機測試用 `runserver --insecure`；正式走 collectstatic + Caddy |
| yfinance `^TWOII`（櫃買）抓不到 | 該指數符號在 yfinance 常無資料 | 程式已優雅降級（partial_errors，不中斷），與原腳本一致 |

## 保真驗證

11 個端點回傳與原 `data/*.json` **逐欄位相等**（含 events `forecast:175000` 保持 int）；
即時 `update_news` 實測 yfinance 拉到真實報價、寫入 DB、API 反映成功。
