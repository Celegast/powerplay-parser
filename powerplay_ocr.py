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
    def __init__(self, tesseract_path=None, use_easyocr=True):
        """
        Initialize the OCR parser

        Args:
            tesseract_path: Path to tesseract executable (optional)
            use_easyocr: Whether to enable EasyOCR as fallback (default: True)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Initialize EasyOCR if enabled (lazy loading to save memory)
        self.use_easyocr = use_easyocr
        self._easyocr_reader = None

        self.screenshots_dir = "screenshots"
        self.output_dir = "extracted_data"

        # Create directories if they don't exist
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def crop_powerplay_panel(self, image_path):
        """
        Crop the Powerplay Information panel from the screenshot using exact coordinates
        For 5120x1440 resolution screenshots

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

        # Exact pixel coordinates for 5120x1440 resolution
        # Panel location: upper-left (2916, 224), lower-right (3656, 870)
        # For other resolutions, scale proportionally
        expected_width = 5120
        expected_height = 1440

        # Calculate scaling factors
        width_scale = width / expected_width
        height_scale = height / expected_height

        # Apply scaling to coordinates
        left = int(2916 * width_scale)
        top = int(224 * height_scale)
        right = int(3656 * width_scale)
        bottom = int(870 * height_scale)

        # Crop the image
        cropped = img[top:bottom, left:right]

        # Convert to PIL Image
        return Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))

    def crop_powerplay_subsections(self, image_path):
        """
        Crop the Powerplay panel into subsections using exact pixel coordinates
        Based on the cropped panel coordinates (740x646 pixels from full 5120x1440 screenshot)

        Subsections (relative to cropped panel):
        - system_name: (14, 56) - (552, 96)
        - system_status: (14, 212) - (424, 280)
        - controlling_power: (528, 360) - (714, 410)
        - undermining: (70, 446) - (260, 474)
        - reinforcing: (480, 446) - (672, 474)

        Args:
            image_path: Path to the image file (can be full screenshot or cropped panel)

        Returns:
            Dictionary of cropped PIL Images for each section
        """
        # First, get the cropped panel (or use it directly if already cropped)
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        height, width = img.shape[:2]

        # If this looks like a full screenshot (width > 2000), crop to panel first
        if width > 2000:
            pil_panel = self.crop_powerplay_panel(image_path)
            img = cv2.cvtColor(np.array(pil_panel), cv2.COLOR_RGB2BGR)
            height, width = img.shape[:2]

        # Expected panel dimensions after cropping from 5120x1440
        # Panel size: 3656-2916 = 740 width, 870-224 = 646 height
        expected_panel_width = 740
        expected_panel_height = 646

        # Calculate scaling factors in case of different resolution
        width_scale = width / expected_panel_width
        height_scale = height / expected_panel_height

        # Define subsection regions using exact pixel coordinates
        subsections = {
            'system_name': {
                'left': int(14 * width_scale),
                'top': int(56 * height_scale),
                'right': int(552 * width_scale),
                'bottom': int(96 * height_scale),
                'description': 'System name line'
            },
            'system_status': {
                'left': int(14 * width_scale),
                'top': int(212 * height_scale),
                'right': int(424 * width_scale),
                'bottom': int(280 * height_scale),
                'description': 'System status with description'
            },
            'controlling_power': {
                'left': int(528 * width_scale),
                'top': int(360 * height_scale),
                'right': int(714 * width_scale),
                'bottom': int(410 * height_scale),
                'description': 'Controlling power name'
            },
            'control_points': {
                'left': int(70 * width_scale),
                'top': int(446 * height_scale),
                'right': int(672 * width_scale),
                'bottom': int(474 * height_scale),
                'description': 'Both undermining and reinforcing control points'
            }
        }

        cropped_sections = {}
        for section_name, coords in subsections.items():
            left = coords['left']
            top = coords['top']
            right = coords['right']
            bottom = coords['bottom']

            # Crop this section
            section_img = img[top:bottom, left:right]

            # Convert to PIL Image
            cropped_sections[section_name] = Image.fromarray(
                cv2.cvtColor(section_img, cv2.COLOR_BGR2RGB)
            )

        return cropped_sections

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

    def extract_text(self, image_path, preprocess_method='upscale', crop_panel=True, use_subsections=False):
        """
        Extract text from image using OCR

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method ('enhanced', 'upscale', 'threshold', 'clahe', 'none')
            crop_panel: Whether to crop to powerplay panel first (default: True)
            use_subsections: Whether to crop into subsections for better accuracy (default: False)

        Returns:
            Extracted text string
        """
        if use_subsections:
            return self.extract_text_subsections(image_path, preprocess_method=preprocess_method)

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

    def extract_text_subsections(self, image_path, preprocess_method='upscale'):
        """
        Extract text by processing subsections independently
        This improves OCR accuracy by focusing on specific UI regions

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method to apply to each subsection

        Returns:
            Combined extracted text string with subsection markers
        """
        # Get subsections
        subsections = self.crop_powerplay_subsections(image_path)

        combined_text = []

        for section_name, section_image in subsections.items():
            # Save section to temp file for preprocessing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                section_image.save(tmp.name)
                temp_path = tmp.name

            # Preprocess the subsection
            if preprocess_method != 'none':
                processed_img = self.preprocess_image(temp_path, method=preprocess_method, crop_panel=False)
            else:
                processed_img = section_image

            # Choose PSM mode based on section
            if section_name == 'header':
                # Header has system name and info spread across multiple lines
                psm = 6  # Single uniform block of text
            elif section_name == 'power_section':
                # Power section has a specific layout with avatars and text
                psm = 3  # Fully automatic page segmentation (works best for this section)
            elif section_name in ['control_points', 'penalties']:
                # These have specific formats
                psm = 6  # Single uniform block
            else:
                # Status and other sections
                psm = 6  # Single uniform block

            custom_config = f'--oem 1 --psm {psm} --dpi 300'
            section_text = pytesseract.image_to_string(processed_img, config=custom_config)

            # Add section marker
            combined_text.append(f"[{section_name.upper()}]")
            combined_text.append(section_text.strip())

            # Clean up temp file
            import os
            try:
                os.remove(temp_path)
            except:
                pass

        return '\n'.join(combined_text)

    def extract_text_easyocr(self, image_path, preprocess_method='upscale'):
        """
        Extract text using EasyOCR (deep learning-based OCR)
        Use as fallback when Tesseract fails completely

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method to use

        Returns:
            Extracted text string
        """
        if not self.use_easyocr:
            return ""

        # Lazy load EasyOCR reader
        if self._easyocr_reader is None:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(['en'], gpu=False)
            except ImportError:
                print("EasyOCR not installed. Install with: pip install easyocr")
                return ""

        # Preprocess image
        if preprocess_method != 'none':
            image = self.preprocess_image(image_path, method=preprocess_method, crop_panel=False)

            # Save preprocessed image to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                image.save(tmp.name)
                temp_path = tmp.name
        else:
            temp_path = image_path

        # Run EasyOCR
        try:
            result = self._easyocr_reader.readtext(temp_path)

            # Extract text from results
            # EasyOCR returns list of (bbox, text, confidence)
            texts = [text for (bbox, text, conf) in result]
            combined_text = '\n'.join(texts)

            # Clean up temp file
            if temp_path != image_path:
                try:
                    import os
                    os.remove(temp_path)
                except:
                    pass

            return combined_text
        except Exception as e:
            print(f"EasyOCR error: {e}")
            return ""

    def extract_powerplay_subsections_optimized(self, image_path):
        """
        Extract powerplay data using exact subsection coordinates with optimized OCR per section
        This is the most accurate method - processes each UI element independently

        Args:
            image_path: Path to screenshot (full or already cropped panel)

        Returns:
            Dictionary with extracted powerplay information
        """
        import tempfile
        import os

        # Get the exact subsections
        subsections = self.crop_powerplay_subsections(image_path)

        info = {
            'system_name': '',
            'controlling_power': '',
            'opposing_power': '',
            'system_status': '',
            'undermining_points': -1,
            'reinforcing_points': -1
        }

        # Process system name section - PSM 7 (single line), threshold for text clarity
        if 'system_name' in subsections:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                subsections['system_name'].save(tmp_path)

            try:
                # Try multiple methods to get best OCR result
                candidates = []

                for method in ['none', 'upscale', 'threshold']:
                    text = pytesseract.image_to_string(
                        self.preprocess_image(tmp_path, method=method, crop_panel=False),
                        config='--oem 3 --psm 7 --dpi 300'
                    ).strip().upper()

                    # Extract just the system name (before LAST UPDATED)
                    if 'LAST UPDATED' in text:
                        name = text.split('LAST UPDATED')[0].strip()
                    else:
                        name = text

                    # Clean up common OCR prefix noise
                    for prefix in ['= ', '_ ', 'A ', 'V ', '> ', '- ', '| ']:
                        if name.startswith(prefix):
                            name = name[len(prefix):].strip()

                    # Apply OCR error corrections
                    # Fix common OCR misreads: DE -> D2, DE- -> D2-, GE -> CE
                    name = re.sub(r'([A-Z])E-(\d)', r'\g<1>2-\2', name)  # DE-20 -> D2-20
                    name = re.sub(r'([A-Z])E(\d)', r'\1\2', name)  # DE2 -> D2
                    name = re.sub(r'\bGE-', 'CE-', name)  # GE-N -> CE-N
                    name = re.sub(r'\bGOL\b', 'COL', name)  # GOL -> COL

                    # Valid system name should be at least 3 characters
                    # Can have "SECTOR" or be a simple name like "LTT 970"
                    if len(name) >= 3:
                        candidates.append(name)

                # Pick the most common result, or the first valid one
                if candidates:
                    # Use the first candidate from 'none' or 'upscale' if available
                    info['system_name'] = candidates[0]
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        # Process status section - look for status keyword in clean text
        if 'system_status' in subsections:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                subsections['system_status'].save(tmp_path)

            try:
                text = pytesseract.image_to_string(
                    self.preprocess_image(tmp_path, method='upscale', crop_panel=False),
                    config='--oem 3 --psm 6 --dpi 300'
                ).strip()

                # Extract first word from description text
                # "Exploited systems have..." -> "EXPLOITED"
                first_word = text.split()[0].upper() if text else ''

                status_keywords = ['STRONGHOLD', 'FORTIFIED', 'EXPLOITED', 'UNOCCUPIED']
                if first_word in status_keywords:
                    info['system_status'] = first_word
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        # Process controlling power section - PSM 6, upscale for text
        if 'controlling_power' in subsections:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                subsections['controlling_power'].save(tmp_path)

            try:
                text = pytesseract.image_to_string(
                    self.preprocess_image(tmp_path, method='upscale', crop_panel=False),
                    config='--oem 3 --psm 6 --dpi 300'
                ).upper()

                # Known power names
                power_names = [
                    'ARISSA LAVIGNY-DUVAL', 'AISLING DUVAL', 'ZEMINA TORVAL',
                    'DENTON PATREUS', 'ZACHARY HUDSON', 'FELICIA WINTERS',
                    'EDMUND MAHON', 'LI YONG-RUI', 'PRANAV ANTAL',
                    'ARCHON DELAINE', 'YURI GROM', 'NAKATO KAINE', 'JEROME ARCHER'
                ]

                # Match against known powers with fuzzy matching
                from difflib import SequenceMatcher
                best_match = None
                best_ratio = 0.7

                for power in power_names:
                    if power in text:
                        best_match = power
                        break
                    # Fuzzy match
                    ratio = SequenceMatcher(None, text.replace('\n', ' '), power).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = power

                if best_match:
                    info['controlling_power'] = best_match.title()
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        # Process control points section - both undermining and reinforcing
        if 'control_points' in subsections:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                subsections['control_points'].save(tmp_path)

            try:
                # Try multiple preprocessing methods for best OCR accuracy
                # 'upscale' sometimes misreads 9 as 8, so try 'none' and 'threshold' too
                best_undermining = None
                best_reinforcing = None

                for method in ['none', 'threshold', 'upscale']:
                    text_full = pytesseract.image_to_string(
                        self.preprocess_image(tmp_path, method=method, crop_panel=False),
                        config='--oem 3 --psm 7 --dpi 300'
                    ).strip()

                    # Try to split by "CONTROL POINTS" to separate the two numbers
                    if 'CONTROL POINTS' in text_full.upper():
                        parts = re.split(r'CONTROL\s+POINTS', text_full, flags=re.IGNORECASE)
                        if len(parts) == 2:
                            # Extract numbers from each part
                            undermining_match = re.search(r'(\d{1,}(?:,\d{3})*)', parts[0])
                            reinforcing_match = re.search(r'(\d{1,}(?:,\d{3})*)', parts[1])

                            if undermining_match and best_undermining is None:
                                try:
                                    best_undermining = int(undermining_match.group(1).replace(',', ''))
                                except ValueError:
                                    pass

                            if reinforcing_match and best_reinforcing is None:
                                try:
                                    best_reinforcing = int(reinforcing_match.group(1).replace(',', ''))
                                except ValueError:
                                    pass
                            elif best_reinforcing is None and parts[1]:
                                # If no reinforcing number found, check if the text contains "0" or similar
                                # For EXPLOITED systems, reinforcing can be 0
                                if '0' in parts[1] or len(parts[1].strip()) < 5:
                                    best_reinforcing = 0

                            # If we found both numbers, we can stop
                            if best_undermining is not None and best_reinforcing is not None:
                                break

                # Set the best results found
                if best_undermining is not None:
                    info['undermining_points'] = best_undermining
                if best_reinforcing is not None:
                    info['reinforcing_points'] = best_reinforcing

                # If still no results, try the fallback method
                if info['undermining_points'] == -1:
                    # Fallback: if no "CONTROL POINTS" found, try digit whitelist
                    text = pytesseract.image_to_string(
                        self.preprocess_image(tmp_path, method='upscale', crop_panel=False),
                        config='--oem 3 --psm 7 --dpi 300 -c tessedit_char_whitelist=0123456789, '
                    ).strip()

                    numbers = re.findall(r'(\d{1,}(?:,\d{3})*)', text)
                    if len(numbers) >= 2:
                        try:
                            info['undermining_points'] = int(numbers[0].replace(',', ''))
                            info['reinforcing_points'] = int(numbers[1].replace(',', ''))
                        except ValueError:
                            pass
                    elif len(numbers) == 1:
                        try:
                            info['undermining_points'] = int(numbers[0].replace(',', ''))
                        except ValueError:
                            pass
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        return info

    def extract_text_hybrid(self, image_path, preprocess_method='upscale'):
        """
        Hybrid approach: Use regular OCR for most fields, subsection OCR for problematic sections
        This achieves the best of both worlds - high overall accuracy with targeted improvements

        Args:
            image_path: Path to the image file
            preprocess_method: Preprocessing method to use (default 'upscale' for best overall accuracy)

        Returns:
            Dictionary with extracted and parsed powerplay information
        """
        # Step 1: Try regular OCR with primary method (upscale is best for numbers)
        text_regular = self.extract_text(image_path, preprocess_method=preprocess_method,
                                        crop_panel=False, use_subsections=False)
        info = self.parse_powerplay_info(text_regular)

        # Step 1a: Try threshold method for system name (better for text characters)
        # Threshold method is more accurate for distinguishing letters but worse for digits
        # Always check threshold if we're using upscale as primary
        if preprocess_method == 'upscale':
            text_threshold = self.extract_text(image_path, preprocess_method='threshold',
                                             crop_panel=False, use_subsections=False)
            info_threshold = self.parse_powerplay_info(text_threshold)

            # Use threshold system name if:
            # 1. Upscale didn't find one, OR
            # 2. Threshold found a different one (likely more accurate for letters)
            if info_threshold['system_name'] and (not info['system_name'] or
                                                  info_threshold['system_name'] != info['system_name']):
                info['system_name'] = info_threshold['system_name']

        # Step 1b: If system name is still missing, try header subsection
        if not info['system_name']:
            subsections = self.crop_powerplay_subsections(image_path)
            header_section = subsections['header']

            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                header_section.save(tmp.name)
                temp_path = tmp.name

            processed = self.preprocess_image(temp_path, method=preprocess_method, crop_panel=False)
            custom_config = r'--oem 1 --psm 6 --dpi 300'
            header_text = pytesseract.image_to_string(processed, config=custom_config)
            header_info = self.parse_powerplay_info(header_text)

            if header_info['system_name']:
                info['system_name'] = header_info['system_name']

            try:
                os.remove(temp_path)
            except:
                pass

        # Step 2: If power name is missing, use subsection OCR for power_section
        if not (info['controlling_power'] or info['opposing_power']):
            subsections = self.crop_powerplay_subsections(image_path)
            power_section = subsections['power_section']

            # Save to temp file for preprocessing
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                power_section.save(tmp.name)
                temp_path = tmp.name

            # Preprocess and OCR with PSM 3 (best for power section)
            processed = self.preprocess_image(temp_path, method=preprocess_method, crop_panel=False)
            custom_config = r'--oem 1 --psm 3 --dpi 300'
            power_text = pytesseract.image_to_string(processed, config=custom_config)
            power_info = self.parse_powerplay_info(power_text)

            # Use power names from subsection
            if power_info['controlling_power'] or power_info['opposing_power']:
                info['controlling_power'] = power_info['controlling_power']
                info['opposing_power'] = power_info['opposing_power']

            try:
                os.remove(temp_path)
            except:
                pass

        # Step 3: If status is missing, try subsection OCR for status section
        if not info['system_status']:
            subsections = self.crop_powerplay_subsections(image_path)
            status_section = subsections['status']

            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                status_section.save(tmp.name)
                temp_path = tmp.name

            processed = self.preprocess_image(temp_path, method=preprocess_method, crop_panel=False)
            custom_config = r'--oem 1 --psm 6 --dpi 300'
            status_text = pytesseract.image_to_string(processed, config=custom_config)
            status_info = self.parse_powerplay_info(status_text)

            if status_info['system_status']:
                info['system_status'] = status_info['system_status']

            try:
                os.remove(temp_path)
            except:
                pass

        # Step 4: EasyOCR fallback for severe failures
        # If critical fields still missing, try EasyOCR on the whole panel
        if not info['system_name'] or not (info['controlling_power'] or info['opposing_power']):
            if self.use_easyocr:
                easyocr_text = self.extract_text_easyocr(image_path, preprocess_method=preprocess_method)
                easyocr_info = self.parse_powerplay_info(easyocr_text)

                # Use EasyOCR results if they're better
                if not info['system_name'] and easyocr_info['system_name']:
                    info['system_name'] = easyocr_info['system_name']

                if not (info['controlling_power'] or info['opposing_power']):
                    if easyocr_info['controlling_power'] or easyocr_info['opposing_power']:
                        info['controlling_power'] = easyocr_info['controlling_power']
                        info['opposing_power'] = easyocr_info['opposing_power']

                if not info['system_status'] and easyocr_info['system_status']:
                    info['system_status'] = easyocr_info['system_status']

        return info

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
                    # Remove common prefix characters like "_ ", "A ", "= ", etc.
                    cleaned_line = line
                    for prefix in ['= ', '_ ', 'A ', 'V ', '> ', '- ', '| ']:
                        if cleaned_line.startswith(prefix):
                            cleaned_line = cleaned_line[len(prefix):].strip()

                    # Extract system name (stops at LAST UPDATED or special chars)
                    # Allow lowercase letters for OCR errors like "De2-16" instead of "DE2-16"
                    system_match = re.match(r'^([A-Za-z0-9][A-Za-z0-9\s\-]+?)(?:\s+LAST\s+UPDATED|[\s=,._]*$)', cleaned_line, re.IGNORECASE)
                    if system_match and len(system_match.group(1).strip()) > 5:
                        # Make sure it's not just other text
                        name = system_match.group(1).strip().upper()  # Convert to uppercase
                        if not any(x in name for x in ['DISTANCE', 'MINUTES', 'EXPLOITED', 'FORTIFIED']):
                            # Fix common OCR errors in Elite Dangerous system names
                            # Pattern: Letters followed by digits should not have extra letters inserted
                            # e.g., "DE2-16" should be "D2-16" (remove E before digit)
                            #       "CB-1" should be "C5-1" (B looks like 5)

                            # Fix pattern like "DE2" -> "D2", "CE5" -> "C5" (extra E before digit)
                            name = re.sub(r'([A-Z])E(\d)', r'\1\2', name)

                            # Fix common character confusions
                            # In system codes, B is often misread 5, O is 0, etc.
                            # But only fix in the suffix portion (after the last space/hyphen)
                            parts = re.split(r'(\s+|-)', name)
                            if len(parts) > 0:
                                last_part = parts[-1]
                                # Fix CB-X -> C5-X pattern (B after letter before hyphen)
                                if re.match(r'^[A-Z]B-\d', last_part):
                                    last_part = last_part.replace('B-', '5-', 1)
                                    parts[-1] = last_part
                                name = ''.join(parts)

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
            # Also skip if we've reached the legend or TUG OF WAR section
            if not info['system_status'] and not any(x in line_upper for x in ['TUG OF WAR', 'OPPOSING POWERS', 'UNOCCUPIED EXPLOITED FORTIFIED STRONGHOLD']):
                for status in status_keywords:
                    # Fuzzy match for OCR errors like "=XPLOITED" for "EXPLOITED" or "VEXPLOTED" for "EXPLOITED"
                    # Use difflib similarity for better matching
                    fuzzy_match = False
                    if status in line_upper:
                        fuzzy_match = True
                    else:
                        # Try fuzzy match using sequence similarity
                        # Remove special characters first (handles "=XPLOITED" → "XPLOITED")
                        from difflib import SequenceMatcher
                        cleaned_line = re.sub(r'[^A-Z\s]', '', line_upper)
                        for word in cleaned_line.split():
                            if len(word) >= len(status) - 2 and len(word) <= len(status) + 2:
                                # Use similarity ratio (handles "VEXPLOTED" → "EXPLOITED")
                                similarity = SequenceMatcher(None, word, status).ratio()
                                if similarity > 0.75:
                                    fuzzy_match = True
                                    break

                    if fuzzy_match and not any(x in line_upper for x in ['PENALTY', 'POINTS']):
                        # For fuzzy matches, check if the status keyword appears in the line
                        # after removing special characters
                        cleaned_line = re.sub(r'[^A-Z\s]', '', line_upper)

                        # Skip description lines (e.g., "Exploited systems have a low control score and need a Fortified")
                        # These have multiple lowercase words forming sentences
                        # But allow lines like "Bm + STRONGHOLD |" which just have lowercase prefixes
                        words_in_line = line_stripped.split()
                        lowercase_words = [w for w in words_in_line if any(c.islower() for c in w) and len(w) > 3]
                        if len(lowercase_words) >= 2:  # If 2+ substantial lowercase words, it's a description
                            continue

                        # Check each word in the cleaned line
                        found_status = False
                        for word in cleaned_line.split():
                            # Check if this word matches the status (exact or fuzzy)
                            if word == status:
                                found_status = True
                                break
                            # Fuzzy check using sequence similarity
                            if len(word) >= len(status) - 2 and len(word) <= len(status) + 2:
                                # Use difflib to calculate similarity ratio
                                from difflib import SequenceMatcher
                                similarity = SequenceMatcher(None, word, status).ratio()
                                # Allow matches with >75% similarity (handles "VEXPLOTED" → "EXPLOITED")
                                if similarity > 0.75:
                                    found_status = True
                                    break

                        if found_status:
                            info['system_status'] = status
                            # Next line might be the description
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line and len(next_line) > 20 and not any(kw in next_line.upper() for kw in ['TUG', 'WAR', 'OPPOSING', 'CONTROL', 'POWERPLAY']):
                                    info['status_description'] = next_line
                            break

            # Fallback: If no status found yet, check description text patterns
            # These descriptions are standardized and often more reliably OCR'd
            if not info['system_status']:
                line_lower = line.lower()
                # EXPLOITED: "Exploited systems have a low control score and need a Fortified"
                if 'exploited systems have a low control score' in line_lower or \
                   ('exploited' in line_lower and 'low control score' in line_lower and 'fortified' in line_lower):
                    info['system_status'] = 'EXPLOITED'
                    info['status_description'] = line.strip()
                # FORTIFIED: "Fortified systems have a high level of reinforcement and maintain control over nearby Exploited systems"
                elif 'fortified systems have a high level of reinforcement' in line_lower or \
                     ('fortified' in line_lower and 'high level of reinforcement' in line_lower and 'exploited' in line_lower):
                    info['system_status'] = 'FORTIFIED'
                    info['status_description'] = line.strip()
                # STRONGHOLD: "Stronghold systems have a very high level of reinforcement"
                elif 'stronghold systems have a very high' in line_lower or \
                     ('stronghold' in line_lower and 'very high' in line_lower and 'reinforcement' in line_lower):
                    info['system_status'] = 'STRONGHOLD'
                    info['status_description'] = line.strip()

            # Power names (known Powerplay leaders)
            # Check for first and last names separately since they might be on different lines
            # Also handle abbreviated first names like "A.LAVIGNY-DUVAL"
            power_first_names = ['ARISSA', 'AISLING', 'ZEMINA', 'DENTON', 'ZACHARY', 'FELICIA',
                                'EDMUND', 'LI', 'PRANAV', 'ARCHON', 'YURI', 'NAKATO', 'JEROME']
            power_last_names = ['LAVIGNY-DUVAL', 'DUVAL', 'TORVAL', 'PATREUS', 'HUDSON',
                               'WINTERS', 'MAHON', 'YONG-RUI', 'ANTAL', 'DELAINE', 'GROM', 'KAINE', 'ARCHER']

            # Check if this line has a power first name or last name
            line_upper = line.upper()

            # Sort power pairs by last name length (longest first) to avoid substring matches
            # e.g., LAVIGNY-DUVAL before DUVAL
            power_pairs = list(zip(power_first_names, power_last_names))
            power_pairs_sorted = sorted(power_pairs, key=lambda x: len(x[1]), reverse=True)

            for first_name, last_name in power_pairs_sorted:
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
                # Also handle OCR errors like "ALAVIGNY-DUVAL" (missing period)
                abbreviated_name = f"{first_name[0]}.{last_name}"
                abbreviated_no_period = f"{first_name[0]}{last_name}"  # OCR might miss the period
                if abbreviated_name in line_upper or abbreviated_no_period in line_upper:
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
                # Match: number (with optional commas), non-digit characters, CONTROL POINTS, non-digit characters, number
                # More permissive - handles "ook 450051' CONTROL POINTS )) 587203" and other OCR noise
                points_match = re.search(r'(\d{4,}(?:,\d{3})*)\D+CONTROL\s+POINTS\D+(\d{4,}(?:,\d{3})*)', line, re.IGNORECASE)
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
        Take a screenshot and save it with validation

        Args:
            region: Tuple of (x, y, width, height) for partial screenshot

        Returns:
            Path to saved screenshot
        """
        import time

        max_retries = 3
        for attempt in range(max_retries):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"powerplay_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)

            try:
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()

                # Save with error handling
                screenshot.save(filepath, 'PNG')

                # Validate the saved file
                import cv2
                test_img = cv2.imread(filepath)
                if test_img is None:
                    raise Exception("Screenshot validation failed - image is empty")

                print(f"Screenshot saved: {filepath}")
                return filepath

            except Exception as e:
                print(f"Screenshot attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.2)  # Brief delay before retry
                    continue
                else:
                    raise Exception(f"Failed to capture valid screenshot after {max_retries} attempts")

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
