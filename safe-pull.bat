@echo off
REM git pull that keeps caddy.exe (see safe-pull.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0safe-pull.ps1" %*
pause
