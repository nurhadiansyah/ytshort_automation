@echo off
title AI Shorts Animator Studio - Web GUI
cd /d "%~dp0"

echo ============================================================
echo   Memulai AI Shorts Animator Studio (Web GUI Lokal)...
echo ============================================================
echo.
echo Sedang memuat modul dan server lokal...
echo Browser akan terbuka otomatis begitu server 100%% siap!
echo.

python web_app.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Server berhenti atau terjadi kendala.
    echo Pastikan dependensi sudah terpasang dan Python aktif di PATH.
)
pause
