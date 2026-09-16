# Local-only Django runserver for the backtest page. Does not touch Caddy or git.
$ErrorActionPreference = "Stop"
$candidates = @(
  "C:\Users\AUSER\Desktop\fintech_web\stark_lab\manage.py",
  "C:\Users\AUSER\Desktop\fintech_web\manage.py"
)
$manage = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $manage) { throw "找不到 manage.py" }
Set-Location (Split-Path $manage)
Write-Host "http://127.0.0.1:8000/backtest/"
python manage.py runserver 127.0.0.1:8000
