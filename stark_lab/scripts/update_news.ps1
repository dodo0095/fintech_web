# StarkLab News 資料更新包裝腳本（供 Windows 工作排程器呼叫）
#   執行 `python manage.py update_news`，並把 stdout/stderr 寫入 logs\news-update-YYYY-MM-DD.log
#
# 手動測試：
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\update_news.ps1
#
# ⚠️ 部署機請把 $PythonExe 設成專案實際使用的 Python（含 django/yfinance 等依賴的 conda env）。
#    例：本機開發 = starklab_news_py38；部署機 = py310。

$ErrorActionPreference = "Continue"

# --- 設定：專案使用的 Python 執行檔（含 django/yfinance 等依賴）---
# 優先序：環境變數 STARKLAB_PYTHON > 部署機 py310 > PATH 上的 python
$PythonExe = $env:STARKLAB_PYTHON
if (-not $PythonExe -and (Test-Path "C:\py310\python.exe")) {
    $PythonExe = "C:\py310\python.exe"          # 部署機 py310 環境
}
if (-not $PythonExe) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}

# stark_lab 專案根目錄（manage.py 所在）= scripts 的上一層
$Root = Split-Path -Parent $PSScriptRoot
$Manage = Join-Path $Root "manage.py"
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd"
$logFile = Join-Path $LogDir ("news-update-{0}.log" -f $stamp)

if (-not $PythonExe) {
    Add-Content -Path $logFile -Value ("[{0}] ERROR: 找不到 Python，請設定環境變數 STARKLAB_PYTHON" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
    exit 1
}

$header = @"
============================================================
[{0}] start update_news
  root   = $Root
  python = $PythonExe
============================================================
"@ -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Add-Content -Path $logFile -Value $header -Encoding UTF8

Push-Location $Root
try {
    & $PythonExe $Manage update_news *>> $logFile
    $code = $LASTEXITCODE
} catch {
    Add-Content -Path $logFile -Value ("EXCEPTION: {0}" -f $_) -Encoding UTF8
    $code = 1
} finally {
    Pop-Location
}

$footer = "[{0}] exit={1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $code
Add-Content -Path $logFile -Value $footer -Encoding UTF8
Add-Content -Path $logFile -Value "" -Encoding UTF8
exit $code
