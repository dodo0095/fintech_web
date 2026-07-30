# 技術決策: 將 news_platform 整合進 stark_lab Django

> **提案人**: tech-lead
> **日期**: 2026-07-30
> **狀態**: 已定案（老闆已於需求對話拍板兩大方向）

---

## 背景

`news_platform`（消息面收集平台，原路徑 `C:\Users\Bandai\Desktop\Dream_project\news_platform`）
目前是「純靜態頁 + Python 抓取腳本產 JSON + Windows 排程」的獨立專案：

- 前端：`index.html` + `css/style.css` + `js/app.js`，讀 `data/*.json` 繪製
- 資料：`scripts/fetch_*.py`（yfinance + Google 新聞 RSS）產出 9 支 JSON
- 自動更新：Windows 工作排程器一天 4 次（04:00 / 08:00 / 14:00 / 20:00）跑 PowerShell → Python

需求：掛進 `stark_lab`（Django + DRF）當一個新分頁 / App，並保留自動更新。

## 老闆已拍板的兩大方向

| 決策 | 選擇 |
|------|------|
| 整合深度 | **完整 Django App** — JSON 遷入 models/DB，腳本改寫成 management command，前端改打 DRF |
| 自動更新機制 | **Windows 工作排程器** — 一天 4 次呼叫 `python manage.py update_news` |

## 架構定案

```
Windows 工作排程器 (04/08/14/20 時)
        ↓  python manage.py update_news
   news app fetchers (yfinance / RSS)  ← 由原 scripts/fetch_*.py 改寫
        ↓  寫入
   Django models (SQLite db.sqlite3)
        ↓  DRF /api/news/*
   frontend/build/news.html + js  ← 由原 index.html/app.js 改寫，只換 fetch 網址
```

### 核心設計原則（降低風險）

> **DRF 端點回傳的 JSON 形狀，必須與現有 `data/*.json` 完全一致。**
> 這樣前端只需把 `fetch('data/market.json')` 換成 `fetch('/api/news/market')`，畫面邏輯零改動。

### Django App：`news`（置於 `stark_lab/news/`，比照現有 `apiserver` 慣例）

### 資料模型（🔴 規範，最終版由 backend-architect 落在 data-model）

| 來源 JSON | 模型 | 儲存策略 |
|-----------|------|---------|
| `market.json` | `MarketSnapshot` | 單例 row：`updated_at`, `session`, `payload`(JSONField 完整鏡射) |
| `news.json` / `tsmc_news.json` / `fed.json` | `NewsItem` | 逐則 row：`category`(headline/tsmc/fed), `rank`, `title`, `summary`, `source`, `url`, `time`, `tags`(JSON), `stance`(nullable) |
| `heat.json` | `HeatSnapshot` | 單例 row：`score`, `level`, `components`(JSON), `drivers`(JSON) |
| `events.json` | `MarketEvent` | 逐則 row：`name`, `date`, `actual`, `forecast`, `previous`, `unit`, `note`, `visible` |
| `watchlist.json` | `WatchlistItem` | 逐則 row：`code`, `symbol`, `name` |
| `valuation_{code}.json` | `Valuation` | 每檔一 row：`code`, `updated_at`, `payload`(JSONField，整包 1214 日序列 + PE/PB 6 條 band) |
| `status.json` | `UpdateStatus` | 單例 row：`ran_at`, `ok`, `ok_count`, `total`, `sources`(JSON) |

> 估值河流圖是「計算後圖表快照」（每檔約 280KB：6 條倍數線 × 1214 點 × PE/PB），
> normalize 無意義，一律 JSONField 整包存。

### DRF 端點（掛在既有 `apiserver` router 之外，新增 `news/urls.py`）

| 方法 | 路徑 | 回傳（鏡射對應 JSON） |
|------|------|----------------------|
| GET | `/api/news/market` | market.json |
| GET | `/api/news/headlines` | news.json |
| GET | `/api/news/tsmc` | tsmc_news.json |
| GET | `/api/news/fed` | fed.json |
| GET | `/api/news/heat` | heat.json |
| GET | `/api/news/events` | events.json |
| GET | `/api/news/watchlist` | watchlist.json |
| GET | `/api/news/valuation/<code>` | valuation_{code}.json |
| GET | `/api/news/status` | status.json |

> 註：既有 `apiserver` 回傳原始 JSON（未套公司信封層）。本 App 為與現有前端一致、
> 且要鏡射原 `data/*.json`，同樣回傳原始 JSON payload，不套信封層。此為刻意決策。

### Management command：`update_news`

- `python manage.py update_news`：跑全部 fetcher，寫 DB，更新 `UpdateStatus`
- `python manage.py update_news --only market news`：只跑指定來源
- fetcher 邏輯由 `scripts/fetch_*.py` 移入 `news/fetchers/`
- 失敗容錯：單一 fetcher 失敗不影響其他，且**不覆寫該來源舊資料**（沿用原專案精神）

### 前端

- `news_platform/index.html` → `frontend/build/news.html`（併入站台導覽列）
- `news_platform/css/style.css` → `frontend/build/static/news/style.css`
- `news_platform/js/app.js` → 改 fetch 網址指向 `/api/news/*`，其餘不動
- `stark_lab/urls.py` 新增 `path('news.html', TemplateView.as_view(template_name="news.html"))`
- 既有頁面導覽列加「消息面」連結

### 自動更新（Windows 工作排程器）

- 改寫 `scripts/register_tasks.ps1` → 呼叫 `python manage.py update_news`（工作目錄 = stark_lab）
- 4 個工作：`StarkLabNews_0400 / 0800 / 1400 / 2000`
- 更新日誌沿用 Django logging（已配置 `logs/app.log`）

## 任務拆解與分派

| # | 任務 | 負責 | 依賴 |
|---|------|------|------|
| T1 | 建 `news` app、models、migration、admin | backend-architect | — |
| T2 | fetchers 移植 + `update_news` command | backend-architect | T1 |
| T3 | DRF serializers/views/urls（鏡射 JSON） | backend-architect | T1 |
| T4 | 前端 news.html + app.js 改 fetch + 導覽列 | frontend-developer | T3 |
| T5 | `register_tasks.ps1` 改呼叫 management command | backend-architect | T2 |
| T6 | L1 Code Review（對程式碼＋對規範＋對設計稿）→ Gate | tech-lead | T1-T5 |

## 影響

- 動到 `stark_lab/settings.py`（INSTALLED_APPS 加 `news`）、`stark_lab/urls.py`、`frontend/build/`
- 新增 DB 資料表（migration），現有 `apiserver` 資料表不受影響
- 需在 stark_lab 環境安裝 `yfinance / feedparser / requests / beautifulsoup4`（併入 requirements）

---

**老闆決策**: [x] 完整 Django App + Windows 排程（已於需求對話確認）
