# 安全修補：M2 / M3 + Dependabot 弱點清理

> **執行人**: tech-lead
> **日期**: 2026-09-04
> **範圍**: `stark_lab/stark_lab/settings.py`、`stark_lab/requirements.txt`
> **驗證環境**: Django 5.2.17（乾淨 venv）— `check` / `test news` / `migrate --plan` / WSGI 載入 / apiserver import 全綠

---

## 一、M2 — SECRET_KEY 移出原始碼

- 移除 settings.py 中硬編碼的 `SECRET_KEY`，改由**環境變數 / `.env`** 讀取。
- 新增 `.env` 載入機制（`python-dotenv`，選用相依；未安裝時退回系統環境變數）。
- 缺 `SECRET_KEY` 時 `raise ImproperlyConfigured` **fail-fast**，避免以空值啟動。
- `.env` 中的值與原硬編碼**完全相同** → 改讀 env 對現有 session **無縫、不登出使用者**。

> ⚠️ 舊 key 仍存在於 git 歷史（曾被 commit）。如需徹底失效，另行**輪替**：
> `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
> 將新值寫入**各部署機的 `.env`**（輪替會使現有 session 失效，需擇時執行）。本次為降低風險採「延續同值」，輪替列為選用後續。

## 二、M3 — 收斂 ALLOWED_HOSTS

- `["*"]` → 預設 `starklab.tw, www.starklab.tw, localhost, 127.0.0.1`。
- 可用環境變數 `DJANGO_ALLOWED_HOSTS`（逗號分隔）覆寫。
- 另將 `DEBUG` 改為可由 `DJANGO_DEBUG` 環境變數控制（預設 False）。

## 三、Dependabot — requirements.txt 清理與升級

**移除未被程式 import 的弱點套件**（掃描全 `.py` 確認零引用）：
`django-allauth`、`djangorestframework-jwt`、`djangorestframework-simplejwt`、`oauthlib`、
`requests-oauthlib`、`PyJWT`、`python3-openid`、`qrcode`、`psycopg2-binary`（用 SQLite）、
`Pillow`（無 ImageField）、`pylint`/`astroid`/`isort`/`mccabe`/`wrapt`/`lazy-object-proxy`（開發工具）、
`virtualenv*`、`stevedore`、`pbr` 等。

**升級實際使用的 runtime 依賴至安全版本**：
| 套件 | 舊 | 新 |
|------|----|----|
| Django | 3.0.3 | **5.2 LTS**（多個 CVE 修補） |
| djangorestframework | 3.11.0 | ≥3.15.2 |
| django-filter | 2.3.0 | ≥24.3 |
| django-cors-headers | 3.2.1 | ≥4.4.0 |
| requests | 2.23.0 | ≥2.32.3 |
| pandas / numpy | 舊 | ≥2.2 / ≥1.26 |

**補上實際使用卻漏列的套件**：`waitress`（serve.py 正式啟動）、`python-dotenv`（載入 .env）。

> Django 升級安全性依據：全專案掃描**無破壞性 API**（無 `conf.urls.url` / `ugettext` /
> `force_text` / `six` / `NullBooleanField` 等），僅移除已淘汰的 `USE_L10N`。

## 四、驗證證據（Django 5.2.17，乾淨 venv）

```
manage.py check                → System check identified no issues (0 silenced)
manage.py test news            → Ran 15 tests OK
manage.py migrate --plan       → 相容（news.0002 / sessions）
import stark_lab.wsgi          → WSGI OK: WSGIHandler
import apiserver.{views,models} → apiserver import OK
```
`check --deploy` 尚餘 2 警告（`SECURE_HSTS_SECONDS`、`SECURE_SSL_REDIRECT`）——TLS/HSTS
由前端 **Caddy 反向代理**處理，Django 端維持 False 為刻意設計，非本次範圍。

## 五、⚠️ 部署 Runbook（正式機 `C:\server website\fintech_web`）

> 這是**正式 fintech 站的框架大版本升級**，本機已盡可能驗證，但 15 個測試未涵蓋
> apiserver 端點、admin、模板渲染等執行期行為。**請於維護時段部署並準備回滾。**

```bat
:: 0) 前置：確認部署機 Python >= 3.10、且 stark_lab\.env 內有 SECRET_KEY
cd "C:\server website\fintech_web"
git pull

cd stark_lab
C:\py310\python.exe -m pip install -r requirements.txt   :: 升級 Django 5.2 等
C:\py310\python.exe manage.py check                       :: 應 0 issues
C:\py310\python.exe manage.py migrate                     :: 套用 migration
C:\py310\python.exe manage.py collectstatic --noinput
:: 重啟 Django（waitress :8000）

:: 冒煙檢查：首頁、/news.html、/api/news/status、選股機器人頁、admin 登入
```

**回滾**：`git reset --hard <前一版>` + `pip install -r requirements.txt`（舊版）+ 重啟。
建議部署前先 `pip freeze > requirements.lock.bak` 備份現況。

## 六、殘留 / 後續建議

- 🟡 SECRET_KEY **輪替**（徹底失效歷史洩漏值）— 需協調各部署機 .env，擇時執行。
- 🟡 `CORS_ORIGIN_ALLOW_ALL = True`（settings.py）偏寬鬆，建議改用白名單。
- 🟡 git 歷史仍含舊 SECRET_KEY / 舊 .env — 如需清除需 `filter-repo`（高風險，另案評估）。
