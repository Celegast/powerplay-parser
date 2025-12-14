"""
Configuration file for PowerplayParser
"""

# Tesseract Configuration
# If tesseract is not in your system PATH, specify the full path here
# Windows example: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Linux example: '/usr/bin/tesseract'
TESSERACT_PATH = None

# Screenshot Configuration
SCREENSHOT_HOTKEY = 'f9'  # Key to press for capturing screenshots
QUIT_HOTKEY = 'esc'  # Key to press to exit hotkey mode

# OCR Configuration
OCR_CONFIG = r'--oem 3 --psm 6'  # Tesseract OCR engine mode and page segmentation mode

# Image Preprocessing
ENABLE_PREPROCESSING = True
THRESHOLD_VALUE = 150
CONTRAST_ENHANCEMENT = 2.0

# Directories
SCREENSHOTS_DIR = "screenshots"
OUTPUT_DIR = "extracted_data"

# System Information Parsing
# Add known allegiances to look for
ALLEGIANCES = [
    'Federation',
    'Empire',
    'Alliance',
    'Independent'
]

# Add known system states to look for
SYSTEM_STATES = [
    'Boom',
    'War',
    'Civil War',
    'Expansion',
    'Lockdown',
    'Outbreak',
    'Famine',
    'Election',
    'Retreat',
    'Investment'
]
