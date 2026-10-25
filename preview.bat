@echo off
REM preview.bat — 本機預覽交易台（改完 site.css 即 refresh 就見到）
REM 用法：雙擊，或者喺 terminal 打 preview.bat
cd /d "%~dp0"
echo.
echo   交易台本機預覽： http://localhost:8099
echo   （改 docs\site.css 之後，喺瀏覽器按 Ctrl+F5 就見到）
echo   收工：關閉呢個窗
echo.
start "" http://localhost:8099/index.html
C:\Users\rain0\trading-os\.venv\Scripts\python.exe -m http.server 8099 --directory docs
