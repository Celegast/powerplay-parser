@echo off
cd /d "%~dp0"
echo ============================================
echo  Antal Priorities Sheet Updater
echo ============================================
echo.

echo [1/3] Fetching system list from Google Sheet...
python update_google_sheet.py --sync-input
if errorlevel 1 (
    echo.
    echo ERROR in step 1 - aborting.
    pause
    exit /b 1
)

echo.
echo [2/3] Starting in-game capture...
echo Switch to Elite Dangerous now.
echo.
python auto_capture.py
if errorlevel 1 (
    echo.
    echo ERROR in step 2 - aborting.
    pause
    exit /b 1
)

echo.
echo [3/3] Uploading data and images to Google Sheet...
python update_google_sheet.py
if errorlevel 1 (
    echo.
    echo ERROR in step 3 - aborting.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done!
echo ============================================
pause
