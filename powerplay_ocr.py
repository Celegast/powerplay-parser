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

pytesseract.pytesseract.tesseract_cmd = r'C:\Tools\Tesseract-OCR\tesseract.exe'


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

    def preprocess_image(self, image_path, method='upscale'):
        """
        Preprocess image for better OCR accuracy
        Optimized for Elite Dangerous UI (dark background, light text)

        Args:
            image_path: Path to the image file
            method: Preprocessing method ('upscale', 'threshold', 'clahe', 'none')

        Returns:
            Preprocessed PIL Image
        """
        # Load image with OpenCV
        img = cv2.imread(image_path)

        if method == 'none':
            return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if method == 'upscale':
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

    def extract_text(self, image_path, preprocess_method='upscale'):
        """
        Extract text from image using OCR

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method ('upscale', 'threshold', 'clahe', 'none')

        Returns:
            Extracted text string
        """
        if preprocess_method != 'none':
            image = self.preprocess_image(image_path, method=preprocess_method)
        else:
            image = Image.open(image_path)

        # Configure tesseract for better accuracy
        # --oem 3: Use both legacy and LSTM OCR engines (default: LSTM only)
        # --psm 6: Assume a single uniform block of text
        # --psm 4: Assume a single column of text of variable sizes
        custom_config = r'--oem 1 --psm 4'
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
            if not info['system_name']:
                powerplay_found = False
                for j in range(max(0, i-3), i):
                    if 'POWERPLAY INFORMATION' in lines[j].upper():
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
            status_keywords = ['UNOCCUPIED', 'EXPLOITED', 'FORTIFIED', 'STRONGHOLD']
            line_stripped = line.strip()
            line_upper = line_stripped.upper()

            for status in status_keywords:
                if status in line_upper and not any(x in line_upper for x in ['PENALTY', 'POINTS', 'SYSTEMS', 'NEARBY', 'HAVE', 'MAINTAIN', 'CONTROL OVER']):
                    # Check if it's a standalone status (possibly with checkbox markers and extra chars)
                    # Remove common prefixes and separators
                    cleaned = line_stripped
                    # Remove prefixes like "| W ", "| TY ", "Vv ", "Y ", etc.
                    for prefix in ['| W ', '| TY ', '|W ', '|TY ', 'V ', 'Vv ', 'Y ', 'v ', 'y ', '> ', '- ', '| ', 'W ']:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()

                    # Also remove trailing characters
                    for suffix in [' tt', ' oo', ' t']:
                        if cleaned.endswith(suffix):
                            cleaned = cleaned[:-len(suffix)].strip()

                    if cleaned.upper() == status:
                        info['system_status'] = status
                        # Next line might be the description
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line and len(next_line) > 20 and not any(kw in next_line.upper() for kw in ['TUG', 'WAR', 'OPPOSING', 'CONTROL', 'POWERPLAY']):
                                info['status_description'] = next_line
                        break

            # Power names (known Powerplay leaders)
            # Check for first and last names separately since they might be on different lines
            power_first_names = ['ARISSA', 'AISLING', 'ZEMINA', 'DENTON', 'ZACHARY', 'FELICIA',
                                'EDMUND', 'LI', 'PRANAV', 'ARCHON', 'YURI', 'NAKATO', 'JEROME']
            power_last_names = ['LAVIGNY-DUVAL', 'DUVAL', 'TORVAL', 'PATREUS', 'HUDSON',
                               'WINTERS', 'MAHON', 'YONG-RUI', 'ANTAL', 'DELAINE', 'GROM', 'KAINE', 'ARCHER']

            # Check if this line has a power first name
            line_upper = line.upper()
            for j, first_name in enumerate(power_first_names):
                if first_name in line_upper:
                    # Check if last name is on same line
                    last_name = power_last_names[j]
                    if last_name in line_upper:
                        power_name = f"{first_name} {last_name}".title()
                    # Check next line for last name
                    elif i + 1 < len(lines) and last_name in lines[i + 1].upper():
                        power_name = f"{first_name} {last_name}".title()
                    else:
                        continue

                    # Determine if opposing or controlling based on context
                    # Look back a few lines to see if we're in "Opposing Powers" or "Controlling Power" section
                    context_lines = ' '.join(lines[max(0, i-3):i+1]).upper()
                    if 'OPPOSING' in context_lines:
                        info['opposing_power'] = power_name
                    else:
                        info['controlling_power'] = power_name
                    break

            # Control points with undermining and reinforcing
            # Format variations: "NUMBER < CONTROL POINTS > NUMBER", "NUMBER CONTROL POINTS » NUMBER", "NUMBER. CONTROL POINTS )) NUMBER"
            # Use word boundaries to avoid matching partial numbers from system names
            # IMPORTANT: This is the authoritative source - always use it if found, even if we already have values
            if 'CONTROL POINTS' in line.upper():
                # Match: number (with optional commas), optional separator, CONTROL POINTS, optional separator, number
                # But avoid matching numbers that are part of system names (e.g., "359 SECTOR")
                points_match = re.search(r'(\d{4,}(?:,\d{3})*)\s*[.<»\)]*\s*CONTROL\s+POINTS\s*[>»\)]*\s*(\d{4,}(?:,\d{3})*)', line, re.IGNORECASE)
                if points_match:
                    try:
                        info['undermining_points'] = int(points_match.group(1).replace(',', ''))
                        info['reinforcing_points'] = int(points_match.group(2).replace(',', ''))
                    except ValueError:
                        pass
                # If only one number found after CONTROL POINTS (reinforcing on separate line)
                elif not info['reinforcing_points']:
                    single_match = re.search(r'CONTROL\s+POINTS\s*[>»\)�]*\s*(\d{4,}(?:,\d{3})*)', line, re.IGNORECASE)
                    if single_match:
                        try:
                            info['reinforcing_points'] = int(single_match.group(1).replace(',', ''))
                        except ValueError:
                            pass

            # Also try to capture points that appear on separate lines
            # Look for UNDERMINING followed by a number on next line
            if 'UNDERMINING' in line.upper() and not info['undermining_points']:
                # Check current line for number
                under_match = re.search(r'UNDERMINING\s*[:\s]*(\d+)', line, re.IGNORECASE)
                if under_match:
                    try:
                        info['undermining_points'] = int(under_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                # Check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^\d+$', next_line):
                        try:
                            info['undermining_points'] = int(next_line)
                        except ValueError:
                            pass

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

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        filepath = input("Enter screenshot path: ").strip()
        if os.path.exists(filepath):
            ocr.process_screenshot(filepath)
        else:
            print("File not found!")

    elif choice == '2':
        print("Taking screenshot in 3 seconds...")
        import time
        time.sleep(3)
        screenshot_path = ocr.take_screenshot()
        ocr.process_screenshot(screenshot_path)

    elif choice == '3':
        ocr.start_hotkey_capture()

    else:
        print("Invalid option!")


if __name__ == "__main__":
    main()
