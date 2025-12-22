"""
Elite Dangerous Powerplay OCR Parser
Extracts system information from screenshots
"""

import pytesseract
from PIL import Image
import cv2
import numpy as np
import pyautogui
import keyboard
import os
from datetime import datetime
import re
import time

#pytesseract.pytesseract.tesseract_cmd = r'C:\Tools\Tesseract-OCR\tesseract.exe'


class PowerplayOCR:
    def __init__(self, tesseract_path=None):
        """
        Initialize the OCR parser

        Args:
            tesseract_path: Path to tesseract executable (optional)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        self.screenshots_dir = "screenshots"
        self.output_dir = "extracted_data"

        # Create directories if they don't exist
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def crop_powerplay_panel(self, image_path):
        """
        Crop the Powerplay Information panel from the screenshot
        The panel is located on the right side of the screen, roughly right of center

        Args:
            image_path: Path to the image file

        Returns:
            Cropped PIL Image containing just the Powerplay panel
        """
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        height, width = img.shape[:2]

        # Powerplay panel is on the right side, roughly:
        # - Starts around 48-50% from left (slightly before center to catch panel border)
        # - Takes up about 50% of width
        # - Vertically: Start higher to include status line, exclude bottom UI

        # Define crop region (as percentages of image dimensions)
        # Adjusted to capture full Powerplay panel content without galaxy map noise
        left_pct = 0.56
        right_pct = 0.75
        top_pct = 0.15    # Start below header
        bottom_pct = 0.70 # End before bottom UI elements

        # Convert to pixel coordinates
        left = int(width * left_pct)
        right = int(width * right_pct)
        top = int(height * top_pct)
        bottom = int(height * bottom_pct)

        # Crop the image
        cropped = img[top:bottom, left:right]

        # Convert to PIL Image
        return Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))

    def preprocess_image(self, image_path, method='enhanced', crop_panel=True):
        """
        Preprocess image for better OCR accuracy
        Optimized for Elite Dangerous UI (dark background, light text)

        Args:
            image_path: Path to the image file
            method: Preprocessing method ('enhanced', 'upscale', 'threshold', 'clahe', 'none')
            crop_panel: Whether to crop to just the Powerplay panel first (default: True)

        Returns:
            Preprocessed PIL Image
        """
        # Load image with OpenCV
        img = cv2.imread(image_path)

        # Crop to Powerplay panel if requested
        if crop_panel:
            pil_cropped = self.crop_powerplay_panel(image_path)
            # Convert back to OpenCV format for processing
            img = cv2.cvtColor(np.array(pil_cropped), cv2.COLOR_RGB2BGR)

        if method == 'none':
            return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if method == 'enhanced':
            # Enhanced preprocessing for Elite Dangerous UI
            # This handles colored text on dark backgrounds better

            # Upscale significantly for better OCR
            scale_factor = 3
            width = int(gray.shape[1] * scale_factor)
            height = int(gray.shape[0] * scale_factor)
            upscaled = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

            # Apply CLAHE to enhance contrast (helps with colored text)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(upscaled)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

            # Apply adaptive thresholding to separate text from background
            # This is crucial for colored text on dark backgrounds
            thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)

            # Optional: dilate slightly to connect broken characters
            kernel = np.ones((2, 2), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=1)

            return Image.fromarray(dilated)

        elif method == 'upscale':
            # Upscale image for better OCR (helps with small text)
            scale_factor = 2
            width = int(gray.shape[1] * scale_factor)
            height = int(gray.shape[0] * scale_factor)
            upscaled = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

            # Light denoising
            denoised = cv2.fastNlMeansDenoising(upscaled, h=5)

            # Increase sharpness
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)

            return Image.fromarray(sharpened)

        elif method == 'threshold':
            # Simple thresholding approach
            # Denoise first
            denoised = cv2.fastNlMeansDenoising(gray, h=10)

            # Apply binary threshold
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            return Image.fromarray(thresh)

        elif method == 'clahe':
            # CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, h=7)

            return Image.fromarray(denoised)

        return Image.fromarray(gray)

    def extract_text(self, image_path, preprocess_method='upscale', crop_panel=True):
        """
        Extract text from image using OCR

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method ('enhanced', 'upscale', 'threshold', 'clahe', 'none')
            crop_panel: Whether to crop to powerplay panel first (default: True)

        Returns:
            Extracted text string
        """
        if preprocess_method != 'none':
            image = self.preprocess_image(image_path, method=preprocess_method, crop_panel=crop_panel)
        else:
            image = Image.open(image_path)

        # Configure tesseract for better accuracy
        # --oem 1: Use LSTM OCR engine (best for modern text)
        # --psm 6: Assume a single uniform block of text
        # --psm 4: Assume a single column of text of variable sizes (better for our UI)
        # -c tessedit_char_whitelist: Limit to expected characters (improves accuracy)
        # Additional options for better accuracy:
        # --dpi 300: Tell Tesseract this is high DPI (we upscaled to 3x)
        custom_config = r'--oem 1 --psm 6 --dpi 300'
        text = pytesseract.image_to_string(image, config=custom_config)

        return text

    def parse_powerplay_info(self, text):
        """
        Parse Powerplay information panel from extracted text

        Expected structure:
        1. POWERPLAY INFORMATION
        2. System name + LAST UPDATED:
        3. DISTANCE: XX.XX LY + time ago
        4. System status (FORTIFIED, UNDERMINED, etc.)
        5. Explanation text
        6. TUG OF WAR
        7. Opposing Powers / Controlling Power
        8. Power name(s)
        9. UNDERMINING / REINFORCING
        10. Points < CONTROL POINTS > Points
        11. SYSTEM STRENGTH PENALTY
        12. BEYOND FRONTLINE PENALTY

        Args:
            text: Raw OCR text

        Returns:
            Dictionary with parsed Powerplay information
        """
        info = {
            'system_name': '',
            'last_updated': '',
            'distance_ly': 0.0,
            'time_ago': '',
            'system_status': '',
            'status_description': '',
            'opposing_power': '',
            'controlling_power': '',
            'undermining_points': 0,
            'reinforcing_points': 0,
            'control_points': 0,
            'system_strength_penalty': '',
            'beyond_frontline_penalty': ''
        }

        lines = text.strip().split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # System name - typically follows "POWERPLAY INFORMATION"
            # Elite Dangerous system names: Letters, numbers, hyphens, spaces
            # Examples: "COL 359 SECTOR EK-L B10-4", "FLOARPH MJ-O D7-19"

            # Check if we recently passed "POWERPLAY INFORMATION" (within last 3 lines)
            # Allow for OCR variations like "POVWERPLAY", "POWERPIAY", etc.
            if not info['system_name']:
                powerplay_found = False
                for j in range(max(0, i-3), i):
                    line_check = lines[j].upper()
                    if 'POWERPLAY INFORMATION' in line_check or 'POVWERPLAY INFORMATION' in line_check or ('POWER' in line_check and 'INFORMATION' in line_check):
                        powerplay_found = True
                        break

                if powerplay_found:
                    # This line might be the system name
                    # Remove common prefix characters like "_ ", "A ", etc.
                    cleaned_line = line
                    for prefix in ['_ ', 'A ', 'V ', '> ', '- ', '| ']:
                        if cleaned_line.startswith(prefix):
                            cleaned_line = cleaned_line[len(prefix):].strip()

                    # Extract system name (stops at LAST UPDATED or special chars)
                    system_match = re.match(r'^([A-Z0-9][A-Z0-9\s\-]+?)(?:\s+LAST\s+UPDATED|[\s=,._]*$)', cleaned_line.upper())
                    if system_match and len(system_match.group(1).strip()) > 5:
                        # Make sure it's not just other text
                        name = system_match.group(1).strip()
                        if not any(x in name for x in ['DISTANCE', 'MINUTES', 'EXPLOITED', 'FORTIFIED']):
                            info['system_name'] = name

            # Distance in light years
            # Handle various formats: "19,812.17LY", "19,839.2 1LY" (with space before last digit)
            distance_match = re.search(r'DISTANCE[:\s]+(\d+[,.\s]*\d*\.?\d*)\s*LY', line, re.IGNORECASE)
            if distance_match:
                # Remove commas and spaces from number
                dist_str = distance_match.group(1).replace(',', '').replace(' ', '')
                try:
                    info['distance_ly'] = float(dist_str)
                except ValueError:
                    pass

            # Time since last update
            time_match = re.search(r'(\d+)\s+(SECOND|MINUTE|HOUR|DAY)S?\s+AGO', line, re.IGNORECASE)
            if time_match:
                info['time_ago'] = f"{time_match.group(1)} {time_match.group(2).lower()}s ago"

            # System status (FORTIFIED, UNDERMINED, etc.)
            # Look for standalone status keywords (not in "EXPLOITED systems" context)
            status_keywords = ['STRONGHOLD', 'FORTIFIED', 'EXPLOITED', 'UNOCCUPIED']  # Order matters - check STRONGHOLD before FORTIFIED
            line_stripped = line.strip()
            line_upper = line_stripped.upper()

            # Skip if already found a status
            if not info['system_status']:
                for status in status_keywords:
                    if status in line_upper and not any(x in line_upper for x in ['PENALTY', 'POINTS']):
                        # Check if it's a standalone status (possibly with checkbox markers and extra chars)
                        # Remove common prefixes and separators
                        cleaned = line_stripped
                        # Remove prefixes like "| W ", "+ ", "Y ", "PY ", "= ", etc.
                        # Use regex to remove any combination of special chars + optional letters/numbers + space at start
                        cleaned = re.sub(r'^[|VvYyWwPp=\+\-_*.\s]+', '', cleaned).strip()

                        # Also remove trailing characters and pipes
                        cleaned = re.sub(r'[\s|]+$', '', cleaned)  # Remove trailing spaces and pipes
                        for suffix in [' tt', ' oo', ' t', ' d']:
                            if cleaned.endswith(suffix):
                                cleaned = cleaned[:-len(suffix)].strip()

                        # Check if cleaned line matches the status keyword
                        cleaned_upper = cleaned.upper()
                        if cleaned_upper == status:
                            info['system_status'] = status
                            # Next line might be the description
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line and len(next_line) > 20 and not any(kw in next_line.upper() for kw in ['TUG', 'WAR', 'OPPOSING', 'CONTROL', 'POWERPLAY']):
                                    info['status_description'] = next_line
                            break
                        # Check if line starts with status keyword followed by " d ", " |", or similar OCR errors
                        # (e.g., "Fortified d systems have...", "Fortified | systems have...")
                        # Match against cleaned_upper - after upper(), single letter becomes uppercase too
                        elif re.match(rf'^{status}\s+[A-Z|\s]', cleaned_upper):
                            info['system_status'] = status
                            # This line itself is the description
                            if len(line_stripped) > 20:
                                info['status_description'] = line_stripped
                            break
                        # Also check if the status keyword appears at the start or end of a multi-status line
                        # (e.g., "UNOCCUPIED EXPLOITED FORTIFIED STRONGHOLD")
                        elif status in cleaned_upper.split():
                            # For multi-status lines, we need to determine which one applies
                            # This typically appears at the bottom as a legend, not the actual status
                            # So we skip these unless it's clearly the only word
                            pass

            # Power names (known Powerplay leaders)
            # Check for first and last names separately since they might be on different lines
            # Also handle abbreviated first names like "A.LAVIGNY-DUVAL"
            power_first_names = ['ARISSA', 'AISLING', 'ZEMINA', 'DENTON', 'ZACHARY', 'FELICIA',
                                'EDMUND', 'LI', 'PRANAV', 'ARCHON', 'YURI', 'NAKATO', 'JEROME']
            power_last_names = ['LAVIGNY-DUVAL', 'DUVAL', 'TORVAL', 'PATREUS', 'HUDSON',
                               'WINTERS', 'MAHON', 'YONG-RUI', 'ANTAL', 'DELAINE', 'GROM', 'KAINE', 'ARCHER']

            # Check if this line has a power first name or last name
            line_upper = line.upper()
            for j, first_name in enumerate(power_first_names):
                last_name = power_last_names[j]

                # Check for last name only (handles cases where OCR misses first name)
                # Use word boundary to ensure we match complete last names
                if re.search(r'\b' + re.escape(last_name) + r'\b', line_upper):
                    power_name = f"{first_name} {last_name}".title()
                    # Determine if opposing or controlling based on context
                    # Look both before AND after (up to 5 lines in each direction)
                    context_before = ' '.join(lines[max(0, i-5):i+1]).upper()
                    context_after = ' '.join(lines[i:min(len(lines), i+6)]).upper()
                    context_lines = context_before + ' ' + context_after

                    # Check for "Controlling Power" first (more specific)
                    if 'CONTROLLING POWER' in context_lines or 'CONTROLLING' in context_lines:
                        info['controlling_power'] = power_name
                    elif 'OPPOSING' in context_lines:
                        info['opposing_power'] = power_name
                    else:
                        # Default to controlling if no clear context
                        info['controlling_power'] = power_name
                    break

                # Check for abbreviated first name (e.g., "A.LAVIGNY-DUVAL", "Z.TORVAL")
                abbreviated_name = f"{first_name[0]}.{last_name}"
                if abbreviated_name in line_upper:
                    power_name = f"{first_name} {last_name}".title()
                    # Determine if opposing or controlling based on context
                    # Look both before AND after (up to 5 lines in each direction) to handle OCR inconsistencies
                    context_before = ' '.join(lines[max(0, i-5):i+1]).upper()
                    context_after = ' '.join(lines[i:min(len(lines), i+6)]).upper()
                    context_lines = context_before + ' ' + context_after

                    # Check for "Controlling Power" first (more specific)
                    if 'CONTROLLING POWER' in context_lines or 'CONTROLLING' in context_lines:
                        info['controlling_power'] = power_name
                    elif 'OPPOSING' in context_lines:
                        info['opposing_power'] = power_name
                    else:
                        # Default to controlling if no clear context
                        info['controlling_power'] = power_name
                    break

                # Check if this line has a power first name (full name)
                # Use word boundary check to avoid matching "LI" in "FRONTLINE", etc.
                # Create a regex pattern that matches the first name as a whole word
                if re.search(r'\b' + first_name + r'\b', line_upper):
                    power_name = None
                    # Check if last name is on same line
                    if last_name in line_upper:
                        power_name = f"{first_name} {last_name}".title()
                    else:
                        # Check next few lines for last name (up to 3 lines ahead)
                        for k in range(1, 4):
                            if i + k < len(lines) and last_name in lines[i + k].upper():
                                power_name = f"{first_name} {last_name}".title()
                                break
                        # If we can't find the last name, use full name anyway as fallback
                        # This handles cases where OCR fails on the last name
                        if power_name is None:
                            power_name = f"{first_name} {last_name}".title()

                    # Determine if opposing or controlling based on context
                    # Look both before AND after (up to 5 lines in each direction) to handle OCR inconsistencies
                    context_before = ' '.join(lines[max(0, i-5):i+1]).upper()
                    context_after = ' '.join(lines[i:min(len(lines), i+6)]).upper()
                    context_lines = context_before + ' ' + context_after

                    # Check for "Controlling Power" first (more specific)
                    if 'CONTROLLING POWER' in context_lines or 'CONTROLLING' in context_lines:
                        info['controlling_power'] = power_name
                    elif 'OPPOSING' in context_lines:
                        info['opposing_power'] = power_name
                    else:
                        # Default to controlling if no clear context
                        info['controlling_power'] = power_name
                    break

            # Control points with undermining and reinforcing
            # Format variations: "NUMBER < CONTROL POINTS > NUMBER", "NUMBER CONTROL POINTS » NUMBER", "NUMBER. CONTROL POINTS )) NUMBER"
            # Also handles: "52317 ° CONTROL POINTS » 150642" with unusual separators
            # Use word boundaries to avoid matching partial numbers from system names
            # IMPORTANT: This is the authoritative source - always use it if found, even if we already have values
            if 'CONTROL POINTS' in line.upper():
                # Match: number (with optional commas), optional separator (including °, _, comma, unicode chars, etc.), CONTROL POINTS, optional separator, number
                # But avoid matching numbers that are part of system names (e.g., "359 SECTOR")
                # Use \S* to match any non-whitespace separator characters (handles �, y, etc.)
                points_match = re.search(r'(\d{4,}(?:,\d{3})*)\s+\S*\s*CONTROL\s+POINTS\s+\S*\s*(\d{4,}(?:,\d{3})*)', line, re.IGNORECASE)
                if points_match:
                    try:
                        info['undermining_points'] = int(points_match.group(1).replace(',', ''))
                        info['reinforcing_points'] = int(points_match.group(2).replace(',', ''))
                    except ValueError:
                        pass
                # If only one number found after CONTROL POINTS, it's the undermining value
                # Reinforcement might be missing/garbled (e.g., "2098 CONTROL POINTS » 8)")
                elif not info['undermining_points']:
                    single_match = re.search(r'(\d{4,}(?:,\d{3})*)\s+\S*\s*CONTROL\s+POINTS', line, re.IGNORECASE)
                    if single_match:
                        try:
                            info['undermining_points'] = int(single_match.group(1).replace(',', ''))
                            # Check if there's a small number after (likely garbled 0)
                            after_match = re.search(r'CONTROL\s+POINTS\s*[>»\)�]*\s*(\d{1,3})(?:\)|$)', line, re.IGNORECASE)
                            if after_match:
                                # Small numbers like "8)" are likely garbled zeros
                                info['reinforcing_points'] = 0
                        except ValueError:
                            pass

            # Also try to capture points that appear on separate lines
            # Look for UNDERMINING followed by a number on next line (or within next few lines)
            if 'UNDERMINING' in line.upper() and not info['undermining_points']:
                # Check current line for number
                under_match = re.search(r'UNDERMINING\s*[:\s_,]*(\d{4,}(?:,\d{3})*)', line, re.IGNORECASE)
                if under_match:
                    try:
                        info['undermining_points'] = int(under_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                # Check next few lines for a standalone number (with or without leading colon)
                else:
                    for j in range(1, 4):
                        if i + j < len(lines):
                            future_line = lines[i + j].strip()
                            # Match standalone numbers (4+ digits to avoid noise), optionally prefixed with colon
                            standalone_match = re.match(r'^:?\s*(\d{4,}(?:,\d{3})*)$', future_line)
                            if standalone_match:
                                try:
                                    info['undermining_points'] = int(standalone_match.group(1).replace(',', ''))
                                    break
                                except ValueError:
                                    pass

            # Also look for standalone numbers after "Opposing Powers" section
            # These are likely undermining values when no explicit UNDERMINING label is found
            if 'OPPOSING POWERS' in line.upper() and not info['undermining_points']:
                # Check next few lines for standalone number
                for j in range(1, 6):
                    if i + j < len(lines):
                        future_line = lines[i + j].strip()
                        # Match standalone numbers (4+ digits to avoid noise)
                        standalone_match = re.match(r'^(\d{4,}(?:,\d{3})*)$', future_line)
                        if standalone_match:
                            # Make sure this isn't already captured as reinforcing
                            potential_undermining = int(standalone_match.group(1).replace(',', ''))
                            if potential_undermining != info['reinforcing_points']:
                                try:
                                    info['undermining_points'] = potential_undermining
                                    break
                                except ValueError:
                                    pass
                        # Stop if we hit another section
                        if any(keyword in future_line.upper() for keyword in ['TUG OF WAR', 'CONTROLLING POWER', 'REINFORCING']):
                            break

            # Look for REINFORCING followed by a number
            if 'REINFORCING' in line.upper() and not info['reinforcing_points']:
                # Check current line for number
                reinf_match = re.search(r'REINFORCING\s*[:\s]*(\d+)', line, re.IGNORECASE)
                if reinf_match:
                    try:
                        info['reinforcing_points'] = int(reinf_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                # Check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Look ahead a couple lines for the number
                    for j in range(1, 4):
                        if i + j < len(lines):
                            future_line = lines[i + j].strip()
                            if re.match(r'^\d+$', future_line):
                                try:
                                    info['reinforcing_points'] = int(future_line)
                                    break
                                except ValueError:
                                    pass

            # System strength penalty
            if 'SYSTEM STRENGTH PENALTY' in line.upper():
                penalty_match = re.search(r'PENALTY[:\s]+(\w+)', line, re.IGNORECASE)
                if penalty_match:
                    info['system_strength_penalty'] = penalty_match.group(1).upper()

            # Beyond frontline penalty
            if 'BEYOND FRONTLINE PENALTY' in line.upper():
                penalty_match = re.search(r'PENALTY[:\s]+(\w+)', line, re.IGNORECASE)
                if penalty_match:
                    info['beyond_frontline_penalty'] = penalty_match.group(1).upper()

        return info

    def take_screenshot(self, region=None):
        """
        Take a screenshot and save it

        Args:
            region: Tuple of (x, y, width, height) for partial screenshot

        Returns:
            Path to saved screenshot
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"powerplay_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)

        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()

        screenshot.save(filepath)
        print(f"Screenshot saved: {filepath}")

        return filepath

    def process_screenshot(self, screenshot_path):
        """
        Process a screenshot and extract Powerplay information

        Args:
            screenshot_path: Path to screenshot file

        Returns:
            Dictionary with extracted information
        """
        print(f"Processing: {screenshot_path}")

        # Extract text
        text = self.extract_text(screenshot_path)

        # Parse Powerplay information
        info = self.parse_powerplay_info(text)

        # Save raw text and parsed information
        text_filename = os.path.splitext(os.path.basename(screenshot_path))[0] + ".txt"
        text_filepath = os.path.join(self.output_dir, text_filename)

        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write("=== RAW OCR TEXT ===\n")
            f.write(text)
            f.write("\n\n=== PARSED POWERPLAY INFORMATION ===\n")
            f.write(f"System Name: {info['system_name']}\n")
            f.write(f"Distance: {info['distance_ly']} LY\n")
            f.write(f"Last Updated: {info['time_ago']}\n")
            f.write(f"System Status: {info['system_status']}\n")
            if info['status_description']:
                f.write(f"Status Description: {info['status_description']}\n")
            f.write(f"\nControlling Power: {info['controlling_power']}\n")
            f.write(f"Opposing Power: {info['opposing_power']}\n")
            f.write(f"\nUndermining Points: {info['undermining_points']}\n")
            f.write(f"Reinforcing Points: {info['reinforcing_points']}\n")
            f.write(f"\nSystem Strength Penalty: {info['system_strength_penalty']}\n")
            f.write(f"Beyond Frontline Penalty: {info['beyond_frontline_penalty']}\n")

        print(f"Results saved: {text_filepath}")

        return info

    def is_valid_powerplay_data(self, info):
        """
        Check if parsed data contains valid powerplay information
        All required fields must be present: System Name, Power, State, Undermining, Reinforcement

        Note: 0 is a valid control point value (e.g., a system with 0 reinforcement points)

        Args:
            info: Dictionary with parsed powerplay information

        Returns:
            True if data appears valid, False otherwise
        """
        # All required fields must be present
        if not info['system_name']:
            return False

        if not (info['controlling_power'] or info['opposing_power']):
            return False

        if not info['system_status']:
            return False

        # Note: 0 is a valid value for control points
        if info['undermining_points'] < 0:
            return False

        if info['reinforcing_points'] < 0:
            return False

        return True

    def format_for_excel(self, info):
        """
        Format parsed data as tab-separated values for Excel

        Args:
            info: Dictionary with parsed powerplay information

        Returns:
            Tab-separated string
        """
        # Columns: System Name, Power, State, (empty), Undermining, Reinforcement
        power = info['controlling_power'] or info['opposing_power'] or ''
        state = info['system_status'] or ''
        # Note: 0 is a valid value, so use >= 0 check
        undermining = str(info['undermining_points']) if info['undermining_points'] >= 0 else ''
        reinforcement = str(info['reinforcing_points']) if info['reinforcing_points'] >= 0 else ''

        return f"{info['system_name']}\t{power}\t{state}\t\t{undermining}\t{reinforcement}"

    def start_continuous_monitoring(self, hotkey='f9', check_interval=2.0, output_file='powerplay_data.txt'):
        """
        Start continuous monitoring mode that automatically captures and validates powerplay data

        Args:
            hotkey: Keyboard key to toggle monitoring on/off (default: f9)
            check_interval: Seconds between automatic captures when monitoring is active
            output_file: File to save collected powerplay data (default: powerplay_data.txt)
        """
        print("=" * 60)
        print("CONTINUOUS MONITORING MODE")
        print("=" * 60)
        print(f"Press '{hotkey.upper()}' to START/STOP monitoring")
        print("Press 'ESC' to exit completely")
        print(f"Output file: {output_file}")
        print("=" * 60)
        print("\nValid datasets will be printed in Excel-compatible format:")
        print("System Name\tPower\tState\t\tUndermining\tReinforcement")
        print("-" * 60)

        monitoring_active = False
        last_capture_time = 0
        collected_systems = {}  # Track unique systems by name
        invalid_parses = []  # Store invalid parses for later analysis

        # Initialize output file with header
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("System Name\tPower\tState\t\tUndermining\tReinforcement\n")

        def save_to_file():
            """Save all collected systems to file"""
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("System Name\tPower\tState\t\tUndermining\tReinforcement\n")
                for system_name in sorted(collected_systems.keys()):
                    excel_line = self.format_for_excel(collected_systems[system_name])
                    f.write(excel_line + '\n')

        def save_invalid_parses():
            """Save invalid parses for analysis"""
            invalid_file = 'invalid_parses.txt'
            with open(invalid_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("INVALID PARSES FOR ANALYSIS\n")
                f.write("=" * 80 + "\n\n")
                for idx, (info, raw_text, screenshot_path) in enumerate(invalid_parses, 1):
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"INVALID PARSE #{idx}\n")
                    f.write(f"{'=' * 80}\n\n")
                    f.write(f"SCREENSHOT: {screenshot_path}\n\n")
                    f.write("PARSED DATA:\n")
                    f.write(f"  System Name: '{info['system_name']}'\n")
                    f.write(f"  Controlling Power: '{info['controlling_power']}'\n")
                    f.write(f"  Opposing Power: '{info['opposing_power']}'\n")
                    f.write(f"  System Status: '{info['system_status']}'\n")
                    f.write(f"  Undermining Points: {info['undermining_points']}\n")
                    f.write(f"  Reinforcing Points: {info['reinforcing_points']}\n")
                    f.write(f"  Distance: {info['distance_ly']} LY\n")
                    f.write(f"  Last Updated: {info['time_ago']}\n")
                    f.write("\nRAW OCR TEXT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(raw_text)
                    f.write("\n" + "-" * 80 + "\n")

        def toggle_monitoring():
            nonlocal monitoring_active
            monitoring_active = not monitoring_active
            if monitoring_active:
                print(f"\n[MONITORING STARTED - Capturing every {check_interval}s]")
            else:
                print("\n[MONITORING STOPPED]")

        keyboard.add_hotkey(hotkey, toggle_monitoring)

        try:
            while True:
                if keyboard.is_pressed('esc'):
                    break

                if monitoring_active:
                    current_time = time.time()
                    if current_time - last_capture_time >= check_interval:
                        # Take screenshot
                        screenshot_path = self.take_screenshot()

                        # Extract text and parse immediately
                        print(f"[Processing {screenshot_path}...]", end=' ')
                        text = self.extract_text(screenshot_path)
                        info = self.parse_powerplay_info(text)

                        # Check if valid
                        if self.is_valid_powerplay_data(info):
                            system_name = info['system_name']
                            # Only add if not already collected
                            if system_name not in collected_systems:
                                collected_systems[system_name] = info
                                # Print in Excel format
                                excel_line = self.format_for_excel(info)
                                print(f"VALID: {excel_line}")
                                # Save to file immediately
                                save_to_file()
                            else:
                                print(f"DUPLICATE: {system_name}")

                            # Delete valid screenshot
                            try:
                                os.remove(screenshot_path)
                            except Exception as e:
                                print(f"\nWarning: Could not delete {screenshot_path}: {e}")
                        else:
                            # Store invalid parse with raw text and keep screenshot
                            invalid_parses.append((info, text, screenshot_path))
                            # Show what failed validation
                            print(f"INVALID - Name:{info['system_name']}, Power:{info['controlling_power'] or info['opposing_power']}, State:{info['system_status']}, Under:{info['undermining_points']}, Reinf:{info['reinforcing_points']}")

                        last_capture_time = current_time

                time.sleep(0.1)  # Small sleep to prevent CPU spinning

        except KeyboardInterrupt:
            pass

        finally:
            # Save invalid parses for analysis
            if invalid_parses:
                save_invalid_parses()
                print("\n" + "=" * 60)
                print(f"Saved {len(invalid_parses)} invalid parse(s) to: invalid_parses.txt")

            # Print final summary
            print("\n" + "=" * 60)
            print(f"COLLECTED POWERPLAY DATA ({len(collected_systems)} systems)")
            print("=" * 60)
            print("System Name\tPower\tState\t\tUndermining\tReinforcement")
            print("-" * 60)
            for system_name in sorted(collected_systems.keys()):
                excel_line = self.format_for_excel(collected_systems[system_name])
                print(excel_line)
            print("=" * 60)
            print(f"Data saved to: {output_file}")
            print("Exiting...")

    def start_hotkey_capture(self, hotkey='f9'):
        """
        Start listening for hotkey to capture screenshots

        Args:
            hotkey: Keyboard key to trigger screenshot
        """
        print(f"Press '{hotkey}' to capture screenshot, 'esc' to quit")

        def on_hotkey():
            print("Capturing screenshot...")
            screenshot_path = self.take_screenshot()
            self.process_screenshot(screenshot_path)
            print("Ready for next capture...\n")

        keyboard.add_hotkey(hotkey, on_hotkey)
        keyboard.wait('esc')
        print("Exiting...")


def main():
    """Main function"""
    print("=" * 50)
    print("Elite Dangerous Powerplay OCR Parser")
    print("=" * 50)

    # Initialize OCR parser
    # If tesseract is not in PATH, specify the path here:
    # Example for Windows: r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    ocr = PowerplayOCR()

    print("\nOptions:")
    print("1. Process existing screenshot")
    print("2. Take screenshot now and process")
    print("3. Start hotkey capture mode (F9 to capture)")
    print("4. Start continuous monitoring mode (F9 to toggle, ESC to exit)")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == '1':
        filepath = input("Enter screenshot path: ").strip()
        if os.path.exists(filepath):
            ocr.process_screenshot(filepath)
        else:
            print("File not found!")

    elif choice == '2':
        print("Taking screenshot in 3 seconds...")
        time.sleep(3)
        screenshot_path = ocr.take_screenshot()
        ocr.process_screenshot(screenshot_path)

    elif choice == '3':
        ocr.start_hotkey_capture()

    elif choice == '4':
        ocr.start_continuous_monitoring()

    else:
        print("Invalid option!")


if __name__ == "__main__":
    main()
