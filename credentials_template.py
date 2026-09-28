# Template for credentials.py — copy this file to credentials.py and fill in your values.
# credentials.py is gitignored and must never be committed.

# Google Apps Script deployment URL (from Deploy -> Manage deployments)
WEB_APP_URL = ''

# Must match SECRET_TOKEN in antal_priorities_updater.gs
SECRET_TOKEN = ''

# Firebase Realtime Database path key (from the ed-powerplay-tracker web app)
FIREBASE_DB_KEY = ''

# Debug defaults — override on the command line with --debug-ocr / --debug-pause.
# Leave these False day-to-day; flip to True only while troubleshooting.
DEBUG_OCR   = False   # capture the raw full-panel OCR text dump (extra tesseract pass)
DEBUG_PAUSE = False   # pause after in-game capture and after upload, for manual inspection
