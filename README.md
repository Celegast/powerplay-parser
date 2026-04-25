# Elite Dangerous Powerplay OCR Parser

A powerful Python tool for extracting powerplay system information from Elite Dangerous screenshots using advanced OCR (Optical Character Recognition). Supports both automated batch processing and manual capture modes with initial control points tracking.

## Features

- **Automated Batch Capture**: Process multiple systems automatically from a list
- **Manual Hotkey Capture**: Press F9 to capture individual systems on-demand
- **Advanced OCR**: Dual-mode OCR with Tesseract and subsection parsing
- **Initial Control Points Detection**: Automatically reads the Thursday tick baseline from the status bar
- **Intelligent Dropdown Navigation**: OCR-based system search and selection
- **Competitive State Support**: Handles both standard and competitive powerplay states
- **Excel-Ready Output**: Tab-separated format for direct paste into Excel
- **Multi-Resolution Support**: Automatic coordinate scaling for any aspect ratio (16:9, 21:9, 32:9, etc.)
- **Cycle Plotting**: Per-cycle RF/UM time-series graphs (`plot_cycle.py`)
- **Historical Plotting**: RF/UM trends across all stored cycles (`plot_overall.py`)
- **System History Plotting**: Single-system CP history coloured by owning power (`plot_system.py`)
- **Overall Summary**: Accumulated RF/UM stats across all stored cycles (`summarize_powers_overall.py`)
- **Priority Sheet Integration**: One-command update of the group's Google Sheet with live data and CP bar images (`update_prio_sheet.bat`)
- **Debug Logging**: Comprehensive debug output for troubleshooting

## Prerequisites

### Required Software

1. **Tesseract OCR**
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **Linux**: `sudo apt-get install tesseract-ocr`
   - **macOS**: `brew install tesseract`

2. **Python 3.8+**

### Python Dependencies

**Option 1: Using pyproject.toml (recommended)**
```bash
pip install -e .
```

**Option 2: Using requirements.txt**
```bash
pip install -r requirements.txt
```

Required packages:
- `pytesseract` - Tesseract OCR wrapper
- `Pillow` - Image processing
- `opencv-python` - Computer vision for preprocessing
- `numpy` - Numerical operations
- `pyautogui` - Screenshot capture and mouse control
- `keyboard` - Hotkey detection
- `matplotlib` - Plotting
- `requests` - HTTP calls for the Google Sheet updater
- `openpyxl` - Excel file reading

## Installation

1. Clone or download this repository
2. Install Tesseract OCR (see Prerequisites)
3. Install Python dependencies:
   - **Recommended**: `pip install -e .` (uses pyproject.toml)
   - **Alternative**: `pip install -r requirements.txt`
4. Configure tesseract path in `config.py` if not in system PATH

## Usage

### Automated Batch Capture

For processing multiple systems automatically:

1. Create `input.txt` with one system name per line:
   ```
   Col 359 Sector CE-N b9-2
   Col 359 Sector RX-R c5-3
   Shinrarta Dezhra
   ```

2. Run the auto-capture script:
   ```bash
   python auto_capture.py
   ```

3. The script will:
   - Navigate to each system using the in-game search
   - Click the correct system from the dropdown
   - Capture and parse powerplay data
   - Extract initial control points from the status bar
   - Save results to `powerplay_auto_capture.txt`

**Important**: Position your game window so the powerplay panel is visible. Screen coordinates scale automatically for any resolution and aspect ratio.

### Manual Capture

For capturing individual systems interactively:

1. Run the manual capture script:
   ```bash
   python manual_capture.py
   ```

2. Navigate to powerplay screens in Elite Dangerous

3. Press **F9** to capture current system

4. Press **ESC** to exit

5. Results saved to `powerplay_data.txt`

### Plotting

Two scripts generate graphs from captured data stored in `auto_capture_outputs/`.

#### `plot_cycle.py` — Current cycle

```bash
# Default: both RF and UM in a single two-panel image
python plot_cycle.py

# Single metric
python plot_cycle.py -m reinforcement
python plot_cycle.py -m undermining
python plot_cycle.py -m decay

# Save to file instead of displaying
python plot_cycle.py -o cycle_69.png
python plot_cycle.py -m undermining -o cycle_69_um.png
```

The default (no `-m`) produces a **two-panel image** with Reinforcement on top and Undermining on the bottom, sharing the same time axis. Passing `-m` produces a single-panel plot for that metric.

#### `plot_overall.py` — All cycles

```bash
# Display interactively
python plot_overall.py

# Save to file
python plot_overall.py -o overall.png
```

Shows RF and UM across **all stored cycles** in two stacked panels. Vertical dotted lines mark each Thursday tick with cycle numbers (C62, C63, …) labelled at the top. The sawtooth pattern within each cycle (values rise during the week and reset at the tick) is clearly visible.

#### `plot_system.py` — Single-system CP history

```bash
# Display interactively
python plot_system.py "Col 359 Sector ZI-N b9-1"

# Save to file (substring match is fine)
python plot_system.py "ZI-N b9-1" -o zi-n_b9-1.png
```

Plots net control points (initial CP + RF − UM) over time for one system. Line segments are coloured by the power that owned the system at each data point. Contested periods are shaded in red. Horizontal threshold lines mark the Fortified (350 k) and Stronghold (1 000 k) boundaries. Each cycle is labelled with its number and end-of-cycle state (FF / SH / EX / C!).

### Summarizing data across all cycles

#### `summarize_powers.py` — Single capture file

```bash
python summarize_powers.py                          # latest capture
python summarize_powers.py auto_capture_outputs/powerplay_auto_capture_20260420_123456.txt
python summarize_powers.py -p "Aisling Duval"       # show another power's systems
```

#### `summarize_powers_overall.py` — All stored cycles

```bash
python summarize_powers_overall.py                  # full history
python summarize_powers_overall.py -c 70 78         # cycles 70–78 only
python summarize_powers_overall.py -p "Yuri Grom"   # another power's system detail
python summarize_powers_overall.py -v               # include per-cycle breakdown
```

Accumulates RF, UM, and decay across every stored capture file. Each cycle is represented by the latest reading of each system seen that cycle, so partial captures within a week are handled correctly.

---

## Priority Sheet Integration

Keeps the group's Google Sheet (`Antal Priorities`) up to date with one command: current UM/RF numbers and a cropped CP-bar image for every system.

### One-time Google Apps Script setup (~5 minutes, free — no Google Cloud billing required)

1. Open the Google Sheet → **Extensions → Apps Script**
2. Paste the entire contents of `antal_priorities_updater.gs`, replacing any existing code
3. Change `SECRET_TOKEN` in the script to any password you choose
4. Click **Deploy → New deployment → Web app**
   - *Execute as:* **Me**
   - *Who has access:* **Anyone**
5. Copy the deployment URL

### Configure credentials

Copy `credentials_template.py` to `credentials.py` (which is gitignored) and fill in your values:

```python
WEB_APP_URL  = 'https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec'
SECRET_TOKEN = 'your-chosen-password'   # must match antal_priorities_updater.gs
```

`credentials.py` is never committed — it stays local to your machine.

The sheet tab name (`"This Cycle 78"`, `"This Cycle 79"`, …) is derived automatically from the current cycle number — no changes needed each week.

### Running the updater

**Full workflow in one command (recommended):**

```
update_prio_sheet.bat
```

This runs all three steps in sequence:

1. **Fetch system list** — reads col B of the Google Sheet and writes it to `input.txt` (picks up any priority changes the group made since the last run)
2. **In-game capture** — launches `auto_capture.py`; switch to Elite Dangerous when prompted
3. **Upload** — pushes UM, RF, timestamp, and CP-bar images to the sheet

**Running steps individually:**

```bash
# Refresh input.txt from the sheet (no game needed)
python update_google_sheet.py --sync-input

# Full update — all systems (data + images)
python update_google_sheet.py

# Upload from a specific archive file
python update_google_sheet.py -c auto_capture_outputs/powerplay_auto_capture_20260420_123456.txt

# Images only — re-upload CP bars without touching UM/RF/timestamp (no capture file needed)
python update_google_sheet.py --images-only

# Data only — skip CP bar images
python update_google_sheet.py --no-images

# Update a single system only (case-insensitive substring match)
python update_google_sheet.py --system "Tofana"

# Single system, images only
python update_google_sheet.py --images-only --system "Tofana"

# Preview without writing to the sheet
python update_google_sheet.py --dry-run
```

### What gets updated in the sheet

| Column | Field | Value |
|--------|-------|-------|
| C | Updated (UTC) | Timestamp of the capture file |
| E | CP bar image | Cropped status bar from the screenshot |
| H | UM | Net undermining (decay-adjusted) |
| I | RF | Reinforcement points |

Only rows whose system name (col B) appears in the capture file are touched. Systems below the `---END` marker in the sheet are ignored.

### Adjusting the CP bar image

Two constants in `update_google_sheet.py` control how the bar looks in the sheet:

```python
BAR_CROP_LEFT_PCT = 0.24   # fraction of the left (grey "unoccupied") section to discard
BAR_TARGET_WIDTH  = 368    # display width in pixels; height scales proportionally
```

### Redeploying after script changes

When `antal_priorities_updater.gs` is edited, the live deployment must be updated:
**Deploy → Manage deployments → edit → select "New version" → Deploy**. The URL stays the same.

---

## How It Works

### OCR Pipeline

The parser uses a sophisticated multi-stage OCR approach:

1. **Screenshot Capture**
   - Full screen or region-specific capture
   - Automatic panel cropping with resolution-aware scaling (see Configuration)

2. **Subsection Extraction**
   - System Name: (14, 56) - (552, 96)
   - System Status: (14, 212) - (424, 280)
   - Controlling Power: (528, 360) - (714, 410)
   - Undermining: (70, 446) - (260, 474)
   - Reinforcing: (480, 446) - (672, 474)
   - Initial CP Bar: (16, 568) - (735, 609)

3. **Image Preprocessing**
   - 2x upscaling using cubic interpolation
   - Grayscale conversion
   - Simple thresholding (threshold=80)
   - Light morphological operations (1x1 kernel)

4. **OCR Processing**
   - Tesseract OCR with PSM 6 (uniform block) for text sections
   - PSM 11 (sparse text) for dropdown detection
   - Custom preprocessing per section type

5. **Data Parsing**
   - Power name extraction (fuzzy matching against known powers)
   - System state detection (EXPLOITED, FORTIFIED, STRONGHOLD, etc.)
   - Control points extraction (undermining/reinforcing)
   - Competitive state handling (multi-power systems)

### Initial Control Points Detection

The parser automatically detects initial CP from the colored status bar:

1. **Bar Location**: Bottom of powerplay panel (16, 568) to (735, 609)
2. **Structure**: 4 equal sections (180px each):
   - Unoccupied (grey): 0 CP
   - Exploited (red): 0 - 350,000 CP
   - Fortified (green): 350,000 - 1,000,000 CP
   - Stronghold (purple): 1,000,000 - 2,000,000 CP

3. **Detection Method**:
   - Scans for pure white center pixel of the 3-pixel-wide marker line
   - Calculates position ratio across the bar
   - Maps to CP value within the appropriate section
   - Rounds to nearest 1,000 CP for cleaner output

### Dropdown Detection

Auto-capture uses advanced dropdown handling:

1. **Dynamic Cropping**:
   - Scans from bottom-up to find where content ends
   - Detects rows with 90%+ dark pixels
   - Crops to show only the black dropdown area

2. **OCR Matching**:
   - Reads all visible system names
   - Exact match first, then fuzzy matching (≥70% similarity)
   - Handles OCR errors in system names gracefully

3. **Click Precision**:
   - Quick mouse press (50-100ms) to avoid triggering route plotting
   - Randomized timing to appear more natural

## Output Format

### Standard States

Tab-separated format ready for Excel:
```
System Name             Power              State        Undermining  Reinforcement
Col 359 Sector CE-N b9-2  Aisling Duval     STRONGHOLD   135,772      322,419
```

### Competitive States

For systems with multiple competing powers:
```
System Name          Power 1st        Power 2nd        CP 2nd    CP 1st
FK-L b10-1          Denton Patreus   Nakato Kaine     442,035   580,212
```

### Initial Control Points Summary

At the end of auto-capture runs:
```
INITIAL CONTROL POINTS SUMMARY
Systems with Initial CP: 40/49

System Name                              Initial CP
--------------------------------------------------------------------------------
Col 359 Sector CE-N b9-2                  1,321,000  (Stronghold)
Col 359 Sector CE-N b9-1                    417,000  (Fortified)
Col 359 Sector KW-V d2-20                    96,000  (Exploited)
```

## Configuration

Edit `config.py` to customize:

```python
# Tesseract path (if not in system PATH)
TESSERACT_PATH = None  # or r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Hotkeys
SCREENSHOT_HOTKEY = 'f9'
QUIT_HOTKEY = 'esc'

# OCR Configuration
OCR_CONFIG = r'--oem 3 --psm 6'
```

## Recognized Powerplay Leaders

All current powerplay leaders are supported:
- Arissa Lavigny-Duval
- Aisling Duval
- Zemina Torval
- Denton Patreus
- Zachary Hudson
- Felicia Winters
- Edmund Mahon
- Li Yong-Rui
- Pranav Antal
- Archon Delaine
- Yuri Grom
- Nakato Kaine
- Jerome Archer

## Project Structure

```
PowerplayParser/
├── auto_capture.py               # Automated batch processing
├── manual_capture.py             # Manual hotkey capture
├── powerplay_ocr.py              # Core OCR library
├── summarize_powers.py           # Single-file per-power summary and decay calculation
├── summarize_powers_overall.py   # Accumulated summary across all stored cycles
├── plot_cycle.py                 # RF/UM graph for the current cycle
├── plot_overall.py               # RF/UM graphs across all stored cycles
├── plot_system.py                # CP history graph for a single system
├── update_google_sheet.py        # Google Sheet updater (data + CP bar images)
├── antal_priorities_updater.gs   # Apps Script to paste into the Google Sheet
├── update_prio_sheet.bat         # One-click: sync → capture → upload
├── config.py                     # Configuration and screen coordinates
├── credentials_template.py       # Template for credentials.py (committed)
├── credentials.py                # Local secrets — gitignored, never committed
├── input.txt                     # System list for auto-capture (synced from sheet)
├── pyproject.toml                # Project metadata and dependencies (recommended)
├── requirements.txt              # Python dependencies (legacy)
├── README.md                     # This file
├── auto_capture_outputs/         # Timestamped capture results
├── tests/                        # Test and debug scripts
│   ├── test_*.py                # Various test scripts
│   └── debug_*.py               # Debug utilities
└── auto_capture/                 # Debug output (auto-created)
    ├── screenshots/             # Full screenshots (deleted after successful OCR)
    ├── debug/cropped/           # Cropped panel images (used for CP bar extraction)
    ├── debug/dropdown/          # Dropdown screenshots
    └── debug/ocr_text/          # OCR and parsing details per system
```

## Tips for Best Results

### Resolution & Display
- Supported resolutions: any aspect ratio (16:9, 21:9, 32:9, etc.)
- Coordinates in `config.py` are stored in the 16:9-zone-relative space at 1440 height and scaled automatically at runtime
- Standard in-game UI scaling
- Ensure powerplay panel is fully visible
- Good contrast with clear text

### Auto-Capture Tips
- Position game window consistently
- Let automation complete (don't move mouse)
- Systems must exist in the galaxy map
- Clear the search field before starting

### Manual Capture Tips
- Wait for panel to fully load before pressing F9
- Ensure all text is visible and sharp
- Works at any resolution (may need coordinate adjustment)

## Debug Output

Both modes create extensive debug files:

### Auto-Capture Debug
- `auto_capture_debug/cropped/capture_NNN.png` - Cropped powerplay panels
- `auto_capture_debug/dropdown/dropdown_NNN.png` - Dropdown screenshots
- `auto_capture_debug/dropdown/dropdown_NNN_info.txt` - Dropdown detection details
- `auto_capture_debug/text/capture_NNN.txt` - OCR and parsing details

### Manual Capture Debug
- Screenshots in `screenshots/`
- Parsed data in `extracted_data/`

## Troubleshooting

### OCR Accuracy Issues
- Verify Tesseract installation: `tesseract --version`
- Check image quality in debug output
- Adjust in-game UI scaling
- Try different preprocessing methods

### Auto-Capture Not Clicking
- Check debug dropdown images - are system names visible?
- Search field and dropdown coordinates scale automatically; verify `SEARCH_FIELD_X/Y` in `config.py` match your screen layout if issues persist
- Ensure dropdown has time to appear (timing in code)

### Initial CP Not Detected
- Check that status bar is visible in screenshot
- Verify bar coordinates match your resolution
- Look at debug info for saturation values

### Mouse/Keyboard Not Working
- Run with administrator privileges (Windows)
- Check for conflicting hotkeys
- Verify pyautogui has screen access (macOS)

## Development

### Test Scripts

The `tests/` folder contains utilities for development:
- `test_initial_cp.py` - Test CP detection on all cropped images
- `test_competitive.py` - Test competitive state parsing
- `test_all_screenshots.py` - Batch test OCR on screenshots

Run tests from the tests directory:
```bash
cd tests
python test_initial_cp.py
```

## Known Limitations

- Requires consistent window positioning for auto-capture
- OCR can misread similar characters (e.g., "0" vs "O")
- Dropdown detection limited to ~600px height at reference resolution (scales automatically)
- Initial CP rounded to nearest 1,000 (sufficient precision)

## License

This project is provided as-is for use with Elite Dangerous.

## Credits

Created for the Elite Dangerous community by commanders who needed better powerplay tracking tools.

Special thanks to:
- The Tesseract OCR team
- The Python computer vision community
- Fellow commanders who tested and provided feedback

o7 Commanders! Fly safe and claim those systems!
