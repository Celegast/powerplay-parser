@echo off
cd /d "%~dp0"
echo ============================================
echo  Antal Priorities Sheet Updater — Acquisitions
echo ============================================
echo.

echo [1/3] Fetching system list from Acquisitions sheet...
python update_google_sheet.py --sync-input --acquisitions
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
pause

echo.
echo [3/3] Uploading data to Acquisitions sheet (no CP bar images)...
python update_google_sheet.py --acquisitions
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
