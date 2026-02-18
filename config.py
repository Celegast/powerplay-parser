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
# All X coordinates are stored in the 16:9-zone-relative space at the reference height.
# The reference ultrawide screen (5120x1440, 32:9) has a centered 16:9 zone of 2560px
# wide, with a 1280px ultrawide offset on each side.  Subtracting that offset gives
# coordinates that scale uniformly with screen height for any aspect ratio.
#
# At runtime, actual coordinates are computed as:
#   scale    = actual_height / EXPECTED_SCREEN_HEIGHT
#   x_offset = max(0, (actual_width - actual_height * 16/9) / 2)
#   actual_x = int(x_offset + CONFIG_X * scale)
#   actual_y = int(CONFIG_Y * scale)
EXPECTED_SCREEN_HEIGHT = 1440  # Reference height (pixels)

# Powerplay Panel Coordinates — X values in 16:9-zone-relative space at 1440 height
# (reference ultrawide values minus the 1280px ultrawide offset)
PANEL_LEFT = 1636             # was 2916 on 5120x1440 (2916 - 1280)
PANEL_TOP = 224
PANEL_RIGHT_STANDARD = 2376  # Standard panel right edge (3656 - 1280); width: 740px
PANEL_BOTTOM_STANDARD = 870  # Standard panel bottom; height: 646px
PANEL_RIGHT_EXTENDED = 2378  # Extended panel right edge (3658 - 1280); width: 742px
PANEL_BOTTOM_EXTENDED = 1064  # Extended panel bottom; height: 840px

# Calculated Panel Dimensions
PANEL_WIDTH_STANDARD = 740   # PANEL_RIGHT_STANDARD - PANEL_LEFT
PANEL_HEIGHT_STANDARD = 646  # PANEL_BOTTOM_STANDARD - PANEL_TOP
PANEL_WIDTH_EXTENDED = 742   # PANEL_RIGHT_EXTENDED - PANEL_LEFT
PANEL_HEIGHT_EXTENDED = 840  # PANEL_BOTTOM_EXTENDED - PANEL_TOP

# Galaxy Map Search Field Coordinates — X in 16:9-zone-relative space at 1440 height
SEARCH_FIELD_X = 1420         # was 2700 on 5120x1440 (2700 - 1280)
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
