@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo    StarkLab 部落格上稿工具
echo ============================================
echo.

if "%~1"=="" (
  echo 用法：把 Word 檔（.docx）直接拖到這個檔案上即可上站。
  echo 也可手動執行： 發佈文章_把Word拖進來.bat "檔案路徑.docx"
  echo.
  pause
  exit /b
)

set "CAT="
set /p CAT="請選分類  [1]=產業時事分析(預設)  [2]=科技分享 ： "
if "%CAT%"=="" set CAT=1

echo.
echo 上稿中： %~nx1  （分類 %CAT%）
echo.

"C:\Users\Bandai\anaconda3\python.exe" manage.py publish_docx "%~1" --cat %CAT%

echo.
echo （若上方顯示網址即代表成功。記得把本機的 DB / media 部署到正式站，或直接在正式站的 stark_lab 目錄執行本工具。）
echo.
pause
