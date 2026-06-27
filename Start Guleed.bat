@echo off
cd /d "%~dp0"
echo ============================================
echo   Starting Guleed Spareparts (local/offline)
echo ============================================
echo.
echo Keep THIS black window open while you use the app.
echo Close it to stop the program.
echo.
python desktop.py
echo.
echo The program stopped. Press any key to close.
pause >nul
