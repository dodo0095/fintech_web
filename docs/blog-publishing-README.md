# 部落格上稿 README（週報 Word → starklab.tw 文章）

> 說明 `finanical_Column` 寫好的台股週報，是怎麼進到 starklab.tw 資料庫並變成 `/blog/<id>/` 文章頁的。
> 上稿管線建立於 commit `14595a0`（feat(blog): 自建部落格 + Word 上稿管線）。

---

## 1. 整體流程

```
finanical_Column/articles/2026-W39/
 ├─ 2026-W39_台股週報_方格子專欄.docx   ← 被匯入的檔案（檔名必須符合這個格式）
 ├─ config.yaml                          ← 取標題 / 發佈日期
 └─ weekly-report-vocus.md               ← config 沒標題時，改用這裡的第一個 H1
          │
          ▼  python manage.py backfill_weekly   （批次）
          ▼  python manage.py publish_docx      （單篇）
          │
   apiserver/blogimport.py
    ├─ mammoth：把 .docx 轉成 HTML
    ├─ 圖片存到 stark_lab/media/blog/<時間戳>/imgN.png
    └─ 寫入 SQLite：stark_lab/db.sqlite3 → 資料表 article_1
          │
          ▼
   https://starklab.tw/blog/<id>/   （伺服器端渲染，模板 frontend/build/blog-post.html）
   https://starklab.tw/botBlog.html （文章列表，前端呼叫 /api/articleapi/ 取資料）
```

## 2. 相關檔案

| 檔案 | 用途 |
|------|------|
| `stark_lab/apiserver/blogimport.py` | 共用核心：docx → 欄位 dict、存圖、寫入 DB |
| `stark_lab/apiserver/management/commands/backfill_weekly.py` | 批次匯入所有週報（重複執行不會產生重複文章） |
| `stark_lab/apiserver/management/commands/publish_docx.py` | 匯入單篇 Word |
| `stark_lab/發佈文章_把Word拖進來.bat` | 把 .docx 拖到這個檔案上，就會執行 `publish_docx` |
| `stark_lab/apiserver/models.py` | `article_1`（產業時事分析）、`article_2`（科技分享） |
| `stark_lab/apiserver/views.py` → `article_detail` | 文章頁；舊文章如果沒有正文、只有 link，會 302 導到原文 |
| `stark_lab/frontend/build/blog-post.html` | 文章頁模板（含 canonical / og / JSON-LD） |

## 3. 每週上稿（最常用）

在 **`stark_lab/` 目錄**下執行（指令要能找到 `manage.py`）：

```bash
cd "C:/Users/Bandai/Desktop/ALL PROJECT/fintech_web/stark_lab"

# 1) 先預覽：只列出會匯入的檔案、標題和日期，不寫入 DB
"C:/Users/Bandai/anaconda3/python.exe" manage.py backfill_weekly --dry-run

# 2) 正式匯入（已經匯入過的週次會自動跳過）
"C:/Users/Bandai/anaconda3/python.exe" manage.py backfill_weekly
```

- 預設讀取的目錄是 `stark_lab/../../finanical_Column/articles`，也就是 `ALL PROJECT/finanical_Column/articles`。
  如果從其他位置（例如 worktree 或正式機）執行，請用 `--dir "路徑"` 指定。
- 輸出範例：`[OK] 2026-W39_台股週報_方格子專欄.docx → https://starklab.tw/blog/21/（5 圖）「…」`

### 欄位怎麼決定（`backfill_weekly`）

| 文章欄位 | 取值順序 |
|---------|---------|
| 標題 `title` | `config.yaml` 的 `subtitle` → `title` → `weekly-report*.md` 第一個 H1（vocus 版優先）→ `台股週報｜YYYY-Wnn` |
| 日期 `date` | `config.yaml` 的 `publish_date` → 該 ISO 週的週五 |
| 摘要 `abstract` | `config.yaml` 的 `subtitle` → Word 第一段文字（取前 100 字） |
| 封面 `title_picture` | Word 裡的第一張圖（沒有圖時，前端顯示品牌預設圖） |
| 正文 `content` | mammoth 轉出來的 HTML；如果開頭標題跟文章標題相同會拿掉，避免重複 |
| 作者 | 固定為「史塔克實驗室」 |
| `source_docx` | Word 檔名，**用來判斷是否匯入過（冪等 key）** |

## 4. 單篇上稿（非週報文章）

- **拖曳**：把 `.docx` 拖到 `stark_lab/發佈文章_把Word拖進來.bat` 上，再選分類 1 或 2。
- **指令**：

```bash
python manage.py publish_docx "檔案.docx" --cat 1 --title "標題" --date 2026-09-27
python manage.py publish_docx "檔案.docx" --update 12   # 覆蓋 id=12 的舊文章
```

參數：`--cat 1|2`、`--title`、`--author`、`--author-pic`、`--cover`、`--abstract`、`--date`、`--link`（原文出處）、`--update ID`。

## 5. 修改已經上站的週報

`backfill_weekly` 用檔名判斷是否匯入過，所以 **Word 內容改了，再跑一次也不會更新**。修改方法：

1. 用 `publish_docx "那份.docx" --update <文章id>` 覆蓋（推薦）；或
2. 到 Django admin（`/admin/`）直接編輯該篇文章。

> ⚠️ 不要用 `--force`，它會**新增一篇重複的文章**，不會更新原本那篇。

## 6. ⚠️ 本機 vs 正式站

DB（`db.sqlite3`）和圖片（`media/`）都**不在 git 版控裡**。在本機匯入的文章，**不會自動出現在正式站**。
正式站路徑（見 `Caddyfile`）：`C:\server website\fintech_web\stark_lab`。

二選一：
- **推薦**：直接在正式機的 `stark_lab/` 執行 `backfill_weekly --dir "<正式機上 finanical_Column/articles 的路徑>"`。
- 或把本機的 `db.sqlite3` 和 `media/blog/` 複製到正式機。**注意：整個 DB 覆蓋會蓋掉正式站的其他資料**（例如訂閱名單），執行前請先備份。

## 7. 前置需求

```bash
pip install mammoth beautifulsoup4 pyyaml   # 已寫在 requirements.txt
python manage.py migrate                    # 需要 migration 0014（content/slug/source_docx/updated 欄位）
```

## 8. 常見問題

| 狀況 | 原因 / 處理 |
|------|------------|
| `找不到週報 Word` | 檔名必須是 `*台股週報_方格子專欄.docx`，並且放在 `articles/<週次>/` 底下 |
| 某一週被 `[skip]` | 這週已經匯入過；要更新內容請看第 5 節 |
| 標題不理想 | 改 `config.yaml` 的 `subtitle`（最優先）後重新上稿，或到 admin 修改 |
| `/blog/<id>/` 出現 404 | 檢查 Caddyfile 的 `@dirScan` 規則有沒有誤擋 `/blog`（commit `78e1ce9` 修過一次） |
| Word 暫存檔 `~$xxx.docx` | 會自動略過 |

## 9. SEO

| 項目 | 說明 |
|------|------|
| Sitemap | `https://starklab.tw/sitemap.xml`（Django `django.contrib.sitemaps` 產生，程式在 `stark_lab/apiserver/sitemaps.py`）。內容：主要公開頁（首頁、`botBlog.html`、`bot.html`、`botAbout.html`、選股歷史/現況頁）＋所有**有站內正文**的文章（`/blog/<id>/`、`/blog/tech/<id>/`）。只有外部連結、沒有正文的舊文不列入。上稿後自動出現，不必手動維護。 |
| lastmod | 有 `updated` 用 `updated`，否則用 `date`；格式無法解析就省略該篇的 lastmod（不會讓 sitemap 壞掉）。 |
| 網域 | sitemap 與文章頁 `og:image` 一律輸出 `settings.SITE_BASE_URL`（預設 `https://starklab.tw`，可用環境變數 `SITE_BASE_URL` 覆寫），本機測試也會顯示正式網址，屬正常。 |
| robots.txt | 正式站實際由 **Caddyfile** 的 `starklab.tw` 區塊回應（含 `Sitemap: https://starklab.tw/sitemap.xml`）；Django 的 `/robots.txt` 只在沒經過 Caddy 時生效，兩邊內容請同步。 |
| 文章頁 | `og:image`、JSON-LD `image` 為絕對網址；JSON-LD 有 `datePublished`／`dateModified`（ISO 8601，+08:00）。 |

**上線步驟**

1. 更新正式機程式碼後重啟 Django（本次無 migration，**不需要** `migrate`）。
2. Caddyfile 有改 → 必須 reload 才生效：`caddy reload --config <Caddyfile 路徑>`。
3. 驗證：`curl https://starklab.tw/robots.txt`（應為三行，含 Sitemap 行）、`curl https://starklab.tw/sitemap.xml`（`<loc>` 都是 `https://starklab.tw/...`）。
4. 到 [Google Search Console](https://search.google.com/search-console) →「Sitemap」→ 提交 `sitemap.xml`（只需做一次，之後 Google 會定期重抓）。
