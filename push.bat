@echo off
set "PATH=C:\Program Files\Git\cmd;%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
cd /d "%~dp0"
echo ============================================================
echo   Pushing code to GitHub: ytshort_automation
echo ============================================================
git add .
git commit -m "Update Dockerfile, requirements.txt, and web_app for Hugging Face deployment"
git push -u origin main
echo.
echo Selesai!
pause
