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

# Screen Resolution and Coordinates
# All coordinates are based on 5120x1440 resolution
# The code automatically scales for different resolutions
EXPECTED_SCREEN_WIDTH = 5120
EXPECTED_SCREEN_HEIGHT = 1440

# Powerplay Panel Coordinates (for cropping from full screenshot)
PANEL_LEFT = 2916
PANEL_TOP = 224
PANEL_RIGHT_STANDARD = 3656  # Standard panel width: 740px
PANEL_BOTTOM_STANDARD = 870  # Standard panel height: 646px
PANEL_RIGHT_EXTENDED = 3658  # Extended panel width: 742px
PANEL_BOTTOM_EXTENDED = 1064  # Extended panel height: 840px

# Calculated Panel Dimensions
PANEL_WIDTH_STANDARD = 740   # PANEL_RIGHT_STANDARD - PANEL_LEFT
PANEL_HEIGHT_STANDARD = 646  # PANEL_BOTTOM_STANDARD - PANEL_TOP
PANEL_WIDTH_EXTENDED = 742   # PANEL_RIGHT_EXTENDED - PANEL_LEFT
PANEL_HEIGHT_EXTENDED = 840  # PANEL_BOTTOM_EXTENDED - PANEL_TOP

# Galaxy Map Search Field Coordinates (for auto_capture.py)
SEARCH_FIELD_X = 2700
SEARCH_FIELD_Y = 168

# Dropdown Menu Configuration (relative to search field)
DROPDOWN_OFFSET_X = -460     # dropdown_left = search_x - 460
DROPDOWN_OFFSET_Y = 25       # dropdown_top = search_y + 25
DROPDOWN_WIDTH = 450
DROPDOWN_MAX_HEIGHT = 600

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
