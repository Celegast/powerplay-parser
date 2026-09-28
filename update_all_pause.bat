@echo off
cd /d "%~dp0"
echo ============================================
echo  Antal Priorities Sheet Updater — This Cycle + Acquisitions
echo ============================================
echo.

echo [1/3] Fetching system lists from both sheets...
python update_google_sheet.py --sync-input --all
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
python auto_capture.py --debug-pause
if errorlevel 1 (
    echo.
    echo ERROR in step 2 - aborting.
    python update_google_sheet.py --clear-status --all
    pause
    exit /b 1
)

echo.
echo [3/3] Uploading to This Cycle (data + images), then Acquisitions (data only)...
python update_google_sheet.py --all --debug-pause
if errorlevel 1 (
    echo.
    echo ERROR in step 3 - aborting.
    python update_google_sheet.py --clear-status --all
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done!
echo ============================================
