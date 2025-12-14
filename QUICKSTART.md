# Quick Start Guide

## Step 1: Install Tesseract OCR

### Windows
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer and note the installation path
3. Add to PATH or update `TESSERACT_PATH` in [config.py](config.py)

### Linux
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### macOS
```bash
brew install tesseract
```

## Step 2: Verify Dependencies Installed

All Python dependencies should already be installed. Verify with:
```bash
pip list | grep -E "pytesseract|Pillow|keyboard|pyautogui|opencv-python"
```

## Step 3: Test Tesseract

Verify Tesseract is working:
```bash
tesseract --version
```

If this fails on Windows, update [config.py](config.py) with the full path:
```python
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Step 4: Run the Script

```bash
python powerplay_ocr.py
```

## Step 5: Choose a Mode

**Option 1**: Process existing screenshot
- Have a screenshot ready
- Enter the file path when prompted

**Option 2**: Take screenshot now
- Get Elite Dangerous ready on screen
- Select this option
- You have 3 seconds to switch windows

**Option 3**: Hotkey mode (Recommended)
- Press F9 anytime to capture
- Press ESC to quit
- Perfect for capturing multiple screens quickly

## Step 6: Check Results

Look in the `extracted_data/` folder for `.txt` files containing:
- Raw OCR text
- Parsed system names
- Distances
- Allegiances
- States

## Tips

- **Better Results**: Use higher in-game resolution
- **Partial Capture**: Edit the script to capture only specific UI regions
- **Batch Processing**: Use [example_usage.py](example_usage.py) for batch processing

## Common Issues

**"Tesseract not found"**
- Install Tesseract and add to PATH
- Or set `TESSERACT_PATH` in [config.py](config.py)

**"Permission denied" for hotkey**
- Run terminal/command prompt as administrator

**Poor OCR quality**
- Increase in-game resolution
- Adjust `THRESHOLD_VALUE` in [config.py](config.py)
- Try `CONTRAST_ENHANCEMENT = 1.5` instead of `2.0`

## Next Steps

- Check [example_usage.py](example_usage.py) for advanced usage
- Modify parsing rules in [powerplay_ocr.py](powerplay_ocr.py) for your needs
- Export results to CSV for spreadsheet analysis

Happy exploring, Commander! o7
