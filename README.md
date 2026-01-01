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

**Important**: Position your game window so the powerplay panel is visible. The script uses screen coordinates that may need adjustment for different resolutions.

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

## How It Works

### OCR Pipeline

The parser uses a sophisticated multi-stage OCR approach:

1. **Screenshot Capture**
   - Full screen or region-specific capture
   - Automatic panel cropping (740x646 px from 5120x1440 resolution)

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
├── auto_capture.py          # Automated batch processing
├── manual_capture.py        # Manual hotkey capture
├── powerplay_ocr.py        # Core OCR library
├── config.py               # Configuration
├── input.txt               # System list for auto-capture
├── pyproject.toml          # Project metadata and dependencies (recommended)
├── requirements.txt        # Python dependencies (legacy)
├── README.md               # This file
├── tests/                  # Test and debug scripts
│   ├── test_*.py          # Various test scripts
│   └── debug_*.py         # Debug utilities
└── auto_capture_debug/     # Debug output (auto-created)
    ├── cropped/           # Cropped panel images
    ├── dropdown/          # Dropdown screenshots
    └── text/              # OCR debug text
```

## Tips for Best Results

### Resolution & Display
- Best results at 5120x1440 resolution
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
- Adjust search field coordinates for your resolution
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
- Currently only optimized for 5120x1440 resolution
- OCR can misread similar characters (e.g., "0" vs "O")
- Dropdown detection limited to ~600px height
- Initial CP rounded to nearest 1,000 (sufficient precision)

## Future Enhancements

- [ ] Multi-resolution support with auto-scaling
- [ ] GUI for configuration and monitoring
- [ ] CSV/JSON export formats
- [ ] Integration with the Powerplay Tracker

## License

This project is provided as-is for use with Elite Dangerous.

## Credits

Created for the Elite Dangerous community by commanders who needed better powerplay tracking tools.

Special thanks to:
- The Tesseract OCR team
- The Python computer vision community
- Fellow commanders who tested and provided feedback

o7 Commanders! Fly safe and claim those systems!
