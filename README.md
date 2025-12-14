# Elite Dangerous Powerplay OCR Parser

A Python tool for extracting system information from Elite Dangerous powerplay screenshots using OCR (Optical Character Recognition).

## Features

- **Screenshot Capture**: Take screenshots manually or via hotkey
- **OCR Processing**: Extract text from screenshots using Tesseract OCR
- **Powerplay Information Parsing**: Automatically extract:
  - System names
  - Distance in Light Years
  - Last update time
  - System status (FORTIFIED, UNDERMINED, CONTROLLED, CONTESTED)
  - Controlling and opposing powers
  - Undermining/Reinforcing points
  - System strength and frontline penalties
- **Image Preprocessing**: Enhance images for better OCR accuracy
- **Batch Processing**: Process multiple screenshots
- **Hotkey Support**: Press F9 to capture and process screenshots on-the-fly

## Prerequisites

### Tesseract OCR

You need to install Tesseract OCR on your system:

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH, or update `TESSERACT_PATH` in [config.py](config.py)

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Main Script

```bash
python powerplay_ocr.py
```

You'll see three options:

1. **Process existing screenshot**: Provide path to an existing image file
2. **Take screenshot now**: Captures screen after 3-second countdown
3. **Hotkey capture mode**: Press F9 to capture, ESC to quit

### Example Workflow

1. Start the script: `python powerplay_ocr.py`
2. Select option 3 (hotkey mode)
3. Switch to Elite Dangerous
4. Navigate to powerplay screens
5. Press F9 to capture and process
6. Check the `extracted_data` folder for results

### Configuration

Edit [config.py](config.py) to customize:
- Tesseract path
- Hotkeys
- OCR settings
- Preprocessing parameters
- Directories

## Output

The script creates two directories:

- `screenshots/`: Captured screenshot images
- `extracted_data/`: Text files with OCR results and parsed information

Each processed screenshot generates a `.txt` file containing:
- Raw OCR text
- Parsed Powerplay information:
  - System name and distance
  - System status (FORTIFIED, UNDERMINED, etc.)
  - Controlling power
  - Undermining and reinforcing points
  - System penalties

## Tips for Better OCR Results

1. **Screenshot the Powerplay Panel**: Focus on the right-side Powerplay Information panel
2. **Use High Resolution**: Higher resolution screenshots provide better OCR accuracy
3. **Default Preprocessing**: The 'upscale' method (2x upscaling with sharpening) works best for Elite Dangerous UI
4. **Standard UI Scaling**: Best results with standard in-game UI scaling
5. **Good Contrast**: Ensure Powerplay panel text is clearly visible

## Recognized Powerplay Leaders

The parser automatically detects these powers:
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
├── powerplay_ocr.py      # Main script
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── screenshots/         # Captured screenshots (auto-created)
└── extracted_data/      # OCR results (auto-created)
```

## Dependencies

- **pytesseract**: Python wrapper for Tesseract OCR
- **Pillow**: Image processing library
- **opencv-python**: Computer vision library for preprocessing
- **keyboard**: Hotkey detection
- **pyautogui**: Screenshot capture
- **numpy**: Numerical operations

## Troubleshooting

### Tesseract not found
- Make sure Tesseract is installed
- Update `TESSERACT_PATH` in [config.py](config.py) with full path to tesseract.exe

### Poor OCR accuracy
- Adjust `THRESHOLD_VALUE` and `CONTRAST_ENHANCEMENT` in [config.py](config.py)
- Try capturing at higher resolution
- Ensure in-game text is sharp and clear

### Keyboard hotkey not working
- Run script with administrator privileges (Windows)
- Check if another program is using the same hotkey

## Future Enhancements

- CSV export for parsed data
- GUI interface
- Region-specific screenshot capture
- Integration with EDSM/EDDN
- Real-time route planning
- Database storage for historical data

## License

This project is provided as-is for use with Elite Dangerous.

## Credits

Created for the Elite Dangerous community. o7 Commanders!
