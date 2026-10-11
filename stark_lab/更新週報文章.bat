@echo off
chcp 65001 >nul
REM 一鍵更新台股週報：把 C:\server website\finanical_Column\articles 的週報同步到 starklab.tw 部落格
REM  - 新的週報 → 新增文章
REM  - 已上站但 Word / config.yaml 有改過 → 就地更新（不會重複建立）
REM  - 沒改過 → 跳過
REM  加參數 --dry-run 可只預覽不寫入，例如：更新週報文章.bat --dry-run

call C:\ProgramData\Anaconda3\Scripts\activate py310
set "PATH=C:\py310;%PATH%"
set "PATH=C:\py310\Scripts;%PATH%"

cd /d "C:\server website\fintech_web\stark_lab"

echo ============================================
echo    StarkLab 週報同步
echo ============================================
python manage.py backfill_weekly --dir "C:\server website\finanical_Column\articles" --update %*

echo.
pause
