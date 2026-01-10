#!/usr/bin/env python3
"""
Automated Powerplay System Capture
Reads system names from input.txt and automatically captures each one
"""

# Standard library imports
import os
import random
import time
from difflib import SequenceMatcher

# Third-party imports
import pyautogui
import winsound

# Local imports
from powerplay_ocr import PowerplayOCR
import config

def play_success_sound():
    """Play a success sound (high beep)"""
    try:
        winsound.Beep(1000, 200)  # 1000 Hz for 200ms
    except:
        print('\a')

def play_error_sound():
    """Play an error sound (low beep)"""
    try:
        winsound.Beep(400, 400)  # 400 Hz for 400ms
    except:
        print('\a\a')

def find_and_click_system_in_dropdown(search_x, search_y, system_name, debug_index=0):
    """
    Find the correct system in the dropdown list using OCR and click it

    Args:
        search_x: X coordinate of search field
        search_y: Y coordinate of search field
        system_name: The exact system name to find
        debug_index: Index for debug file naming

    Returns:
        True if found and clicked, False otherwise
    """
    import pytesseract
    import cv2
    import numpy as np
    from PIL import Image

    # Dropdown appears below the search field
    # Use configuration values for dropdown positioning
    dropdown_left = search_x + config.DROPDOWN_OFFSET_X
    dropdown_top = search_y + config.DROPDOWN_OFFSET_Y
    dropdown_width = config.DROPDOWN_WIDTH
    dropdown_max_height = config.DROPDOWN_MAX_HEIGHT

    # Take screenshot of dropdown area immediately (dropdown should already be visible)
    screenshot_full = pyautogui.screenshot(region=(dropdown_left, dropdown_top, dropdown_width, dropdown_max_height))

    # Dynamically detect where the dropdown content ends
    # Strategy: Scan from BOTTOM to TOP looking for where content starts
    # Convert to OpenCV format for analysis
    img_full = cv2.cvtColor(np.array(screenshot_full), cv2.COLOR_RGB2BGR)

    # Convert to grayscale for brightness analysis
    gray = cv2.cvtColor(img_full, cv2.COLOR_BGR2GRAY)

    dropdown_height = dropdown_max_height  # Default to full height

    # Scan from bottom to top
    # Look for rows where most pixels are very dark (black background with no content)
    dark_threshold = 30  # Pixel values below this are considered dark/black
    dark_pixel_ratio_threshold = 0.9  # 90% of pixels must be dark

    # We need to find where empty black space starts
    # Look for 2 consecutive rows that are almost entirely black
    for y in range(dropdown_max_height - 1, 10, -1):  # Start from bottom, go up to row 10
        # Check current row and next row up
        row_current = gray[y, :]
        row_prev = gray[y - 1, :] if y > 0 else row_current

        # Count dark pixels in both rows
        dark_pixels_current = np.sum(row_current < dark_threshold)
        dark_pixels_prev = np.sum(row_prev < dark_threshold)

        dark_ratio_current = dark_pixels_current / len(row_current)
        dark_ratio_prev = dark_pixels_prev / len(row_prev)

        # If both rows are almost entirely dark, this is where content ended
        if dark_ratio_current >= dark_pixel_ratio_threshold and dark_ratio_prev >= dark_pixel_ratio_threshold:
            # Found the end of content - crop here
            dropdown_height = y
            # Don't break - keep going up to find the FIRST content (bottom-most)
        else:
            # Found content - stop here
            if dropdown_height < dropdown_max_height:
                # Add a small margin (10 pixels) to include the last line
                dropdown_height = min(dropdown_height + 10, dropdown_max_height)
                break

    # Crop to just the dropdown area
    screenshot = screenshot_full.crop((0, 0, dropdown_width, dropdown_height))

    # Save screenshot for debugging
    debug_path = f"auto_capture/debug/dropdown/dropdown_{debug_index:03d}.png"
    os.makedirs('auto_capture/debug/dropdown', exist_ok=True)
    screenshot.save(debug_path)

    # Save debug info about the cropping
    debug_info_path = f"auto_capture/debug/dropdown/dropdown_{debug_index:03d}_info.txt"
    with open(debug_info_path, 'w') as f:
        f.write(f"Max height captured: {dropdown_max_height}px\n")
        f.write(f"Detected dropdown height: {dropdown_height}px\n")
        f.write(f"Dark pixel threshold: {dark_threshold}\n")
        f.write(f"Dark ratio threshold: {dark_pixel_ratio_threshold}\n")
        f.write(f"Looking for: {system_name}\n")
        f.write(f"\nRow darkness analysis (from bottom up):\n")
        for y in range(dropdown_max_height - 1, max(0, dropdown_height - 50), -1):
            row = gray[y, :]
            dark_pixels = np.sum(row < dark_threshold)
            dark_ratio = dark_pixels / len(row)
            marker = " <- BOUNDARY" if y == dropdown_height else ""
            f.write(f"Row {y}: {dark_ratio:.1%} dark{marker}\n")

    # Preprocess image for better OCR accuracy
    # Convert PIL to OpenCV format
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Upscale 2x (not 3x - was too large for OCR)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Elite Dangerous has orange/yellow text on dark background
    # Use simple thresholding to isolate bright text
    _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)

    # Very light morphological operations to clean up without distorting text
    kernel = np.ones((1, 1), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Save preprocessed image for debugging
    preprocessed_path = f"auto_capture/debug/dropdown/dropdown_{debug_index:03d}_preprocessed.png"
    cv2.imwrite(preprocessed_path, cleaned)

    # Convert back to PIL for pytesseract
    preprocessed_pil = Image.fromarray(cleaned)

    # OCR the dropdown to find matching system names
    # Try PSM 11 (sparse text, find as much text as possible)
    text = pytesseract.image_to_string(
        preprocessed_pil,
        config='--oem 3 --psm 11'
    )

    # Save OCR text for debugging
    ocr_debug_path = f"auto_capture/debug/dropdown/dropdown_{debug_index:03d}_ocr.txt"
    with open(ocr_debug_path, 'w', encoding='utf-8') as f:
        f.write(f"Looking for: {system_name}\n")
        f.write("=" * 80 + "\n")
        f.write("RAW OCR Result:\n")
        f.write(text)
        f.write("\n" + "=" * 80 + "\n")

    # Split into lines and find the matching system
    lines = [line.strip().upper() for line in text.split('\n') if line.strip()]

    system_name_upper = system_name.upper()
    match_index = -1
    match_method = ""

    # Write parsed lines to debug
    with open(ocr_debug_path, 'a', encoding='utf-8') as f:
        f.write("\nParsed Lines (filtered, uppercase):\n")
        for i, line in enumerate(lines):
            f.write(f"  [{i}] {line}\n")
        f.write("\n" + "=" * 80 + "\n")

    # First try exact match
    for i, line in enumerate(lines):
        if system_name_upper == line:
            match_index = i
            match_method = "exact match"
            break

    # If no exact match, try fuzzy matching using similarity ratio
    if match_index < 0:
        # SequenceMatcher imported at top of file
        best_ratio = 0.0
        best_index = -1

        for i, line in enumerate(lines):
            # Skip very short lines (likely noise)
            if len(line) < 5:
                continue

            # Calculate similarity ratio
            ratio = SequenceMatcher(None, system_name_upper, line).ratio()

            # Keep track of best match
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = i

        # Accept if similarity is at least 70%
        if best_ratio >= 0.7 and best_index >= 0:
            match_index = best_index
            match_method = f"fuzzy match ({best_ratio:.1%})"

    # Fallback: if no match found at all, use first valid line (skip very short ones)
    if match_index < 0:
        for i, line in enumerate(lines):
            if len(line) >= 10:  # Must be at least 10 characters to be a system name
                match_index = i
                match_method = "fallback (first valid line)"
                break

    if match_index >= 0:
        # Calculate click position
        # Each line is approximately 30-40 pixels tall
        line_height = 38
        click_y = dropdown_top + (match_index * line_height) + (line_height // 2)
        click_x = dropdown_left + (dropdown_width // 2)

        # Save debug info about click position
        with open(ocr_debug_path, 'a', encoding='utf-8') as f:
            f.write(f"Match Method: {match_method}\n")
            f.write(f"Matched at line [{match_index}]: {lines[match_index]}\n")
            f.write(f"Click position: ({click_x}, {click_y})\n")
            f.write(f"  dropdown_left={dropdown_left}, dropdown_top={dropdown_top}\n")
            f.write(f"  match_index={match_index}, line_height={line_height}\n")

        # Add randomness
        click_x += random.randint(-10, 10)
        click_y += random.randint(-5, 5)

        # Click on the matched system - quick click to avoid route plotting
        pyautogui.moveTo(click_x, click_y)
        time.sleep(random.uniform(0.1, 0.2))
        pyautogui.mouseDown()
        time.sleep(random.uniform(0.05, 0.1))  # Very short press - just a quick tap
        pyautogui.mouseUp()

        # Small delay before moving mouse away
        time.sleep(random.uniform(0.1, 0.2))

        return True

    return False

def get_cycle_tick_time(reference_time):
    """
    Calculate the most recent Thursday 7am UTC tick before (or at) the reference time.

    Powerplay cycles run from Thursday 7am UTC to the next Thursday 7am UTC.

    Args:
        reference_time: datetime object to calculate the cycle tick for

    Returns:
        datetime object representing the most recent Thursday 7am UTC
    """
    from datetime import timedelta, timezone

    # Get the reference time in UTC
    if reference_time.tzinfo is None:
        # Assume local time, convert to UTC
        reference_utc = reference_time.replace(tzinfo=timezone.utc)
    else:
        reference_utc = reference_time.astimezone(timezone.utc)

    # Find the most recent Thursday 7am UTC
    # Thursday is weekday 3 (Monday=0, Tuesday=1, Wednesday=2, Thursday=3, ...)
    current_weekday = reference_utc.weekday()

    # Calculate days since last Thursday
    if current_weekday >= 3:
        # We're on or after Thursday this week
        days_since_thursday = current_weekday - 3
    else:
        # We're before Thursday (Mon, Tue, Wed) - go back to last week's Thursday
        days_since_thursday = current_weekday + 4  # (7 - 3 + current_weekday)

    # Go back to that Thursday at 7am UTC
    last_thursday = reference_utc - timedelta(days=days_since_thursday)
    last_tick = last_thursday.replace(hour=7, minute=0, second=0, microsecond=0)

    # If we're on Thursday but before 7am UTC, go back one more week
    if last_tick > reference_utc:
        last_tick = last_tick - timedelta(days=7)

    return last_tick

def load_previous_capture(output_dir, current_time):
    """
    Load the most recent previous capture file for comparison

    Args:
        output_dir: Directory containing capture files
        current_time: Current datetime for cycle comparison

    Returns:
        Tuple of (previous_data, is_same_cycle) where:
        - previous_data: Dictionary mapping system names to {undermining, reinforcing} or None
        - is_same_cycle: Boolean indicating if previous capture is from same cycle
    """
    import glob
    from datetime import datetime

    # Find all previous capture files
    pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
    files = sorted(glob.glob(pattern))

    if len(files) < 1:
        return None, False  # No previous file

    # Get the most recent file (the current file hasn't been written yet, so files[-1] is the previous run)
    prev_file = files[-1]

    print(f"\nLoading previous capture for comparison: {os.path.basename(prev_file)}")

    # Extract timestamp from filename (format: powerplay_auto_capture_YYYYMMDD_HHMMSS.txt)
    basename = os.path.basename(prev_file)
    try:
        # Extract the timestamp part: YYYYMMDD_HHMMSS
        timestamp_str = basename.replace('powerplay_auto_capture_', '').replace('.txt', '')
        # Parse as naive datetime (local time when file was created)
        prev_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        # Note: prev_time is in local time, same as current_time will be
    except ValueError:
        print(f"  Warning: Could not parse timestamp from filename")
        return None, False

    # Check if both captures are in the same cycle
    current_tick = get_cycle_tick_time(current_time)
    previous_tick = get_cycle_tick_time(prev_time)
    is_same_cycle = (current_tick == previous_tick)

    if is_same_cycle:
        print(f"  Previous capture is from the SAME cycle (tick: {current_tick.strftime('%Y-%m-%d %H:%M UTC')})")
    else:
        print(f"  WARNING: Previous capture is from a DIFFERENT cycle!")
        print(f"    Previous tick: {previous_tick.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"    Current tick:  {current_tick.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"  -> CP validation will be SKIPPED (values reset after cycle tick)")

    previous_data = {}
    try:
        with open(prev_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Skip header line
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('-') or line.startswith('='):
                continue

            parts = line.split('\t')
            if len(parts) >= 6:
                system_name = parts[0]
                try:
                    undermining = int(parts[4].replace(',', '')) if parts[4] else -1
                    reinforcing = int(parts[5].replace(',', '')) if parts[5] else -1
                    previous_data[system_name] = {'undermining': undermining, 'reinforcing': reinforcing}
                except (ValueError, IndexError):
                    continue

    except Exception as e:
        print(f"  Warning: Could not load previous file: {e}")
        return None, False

    print(f"  Loaded {len(previous_data)} systems from previous capture")
    return previous_data, is_same_cycle

def click_and_paste(x, y, text, debug_index=0):
    """
    Click at coordinates and type text with randomized movement and timing

    Adds natural variation to mouse movements and delays:
    - X position: +/- 10 pixels
    - Y position: +/- 5 pixels
    - Delays: 0.2 to 1.0 seconds
    """
    # Add randomness to coordinates
    x_offset = random.randint(-10, 10)
    y_offset = random.randint(-5, 5)

    # Click on the input field using mouseDown/mouseUp
    pyautogui.moveTo(x + x_offset, y + y_offset)
    time.sleep(random.uniform(0.2, 1.0))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.2, 1.0))
    pyautogui.mouseUp()
    time.sleep(random.uniform(0.2, 1.0))

    # Clear existing text with backspace
    pyautogui.press('backspace')
    time.sleep(random.uniform(0.2, 1.0))

    # Type the text directly (slower but more reliable)
    pyautogui.write(text, interval=0.05)

    # Wait for dropdown to appear and stabilize
    time.sleep(1.2)  # Fixed delay to ensure dropdown is fully visible

    # Find and click the exact system in the dropdown
    if find_and_click_system_in_dropdown(x, y, text, debug_index):
        print(f"  -> Found and clicked '{text}' in dropdown")
    else:
        print(f"  -> ERROR: Could not find '{text}' in dropdown")

    # Move mouse back to search field
    pyautogui.moveTo(x + x_offset, y + y_offset)

    # Wait for the game to process and display system info
    time.sleep(random.uniform(0.5, 1.0))

def main():
    print("=" * 80)
    print("ELITE DANGEROUS POWERPLAY OCR - AUTOMATED CAPTURE")
    print("=" * 80)
    print("\nThis script will automatically:")
    print("1. Read system names from input.txt")
    print("2. PHASE 1: Capture screenshots of all systems (fast)")
    print("3. PHASE 2: Process screenshots with OCR (slower)")
    print("\n" + "=" * 80)

    # Create output files: main file + timestamped archive
    from datetime import datetime as dt
    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    output_dir = 'auto_capture_outputs'
    os.makedirs(output_dir, exist_ok=True)

    # Main output file (always latest)
    main_output_file = 'powerplay_auto_capture.txt'

    # Timestamped archive file
    archive_output_file = os.path.join(output_dir, f'powerplay_auto_capture_{timestamp}.txt')

    # Check if input.txt exists
    if not os.path.exists('input.txt'):
        print("\nERROR: input.txt not found!")
        print("Please create input.txt with one system name per line.")
        return

    # Read system names
    with open('input.txt', 'r', encoding='utf-8') as f:
        system_names = [line.strip() for line in f if line.strip()]

    if not system_names:
        print("\nERROR: input.txt is empty!")
        return

    print(f"\nFound {len(system_names)} systems to process:")
    for i, name in enumerate(system_names[:5], 1):
        print(f"  {i}. {name}")
    if len(system_names) > 5:
        print(f"  ... and {len(system_names) - 5} more")

    # Load previous capture for comparison
    current_time = dt.now()
    previous_data, is_same_cycle = load_previous_capture(output_dir, current_time)

    print("\n" + "=" * 80)
    print("\nYou have 5 seconds to switch to Elite Dangerous...")
    print("Make sure the Galaxy Map is open and ready!")
    for i in range(5, 0, -1):
        print(f"Starting in {i}...", end='\r')
        time.sleep(1)
    print("\nStarting automation...                ")
    print("=" * 80)

    ocr = PowerplayOCR()

    # Create directories for screenshots
    os.makedirs('auto_capture/screenshots', exist_ok=True)

    # Search field coordinates from config
    SEARCH_X = config.SEARCH_FIELD_X
    SEARCH_Y = config.SEARCH_FIELD_Y

    # =========================================================================
    # PHASE 1: CAPTURE SCREENSHOTS (FAST - GAME INTERACTION)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PHASE 1: CAPTURING SCREENSHOTS")
    print("=" * 80)

    screenshot_mapping = {}  # Maps system_name -> screenshot_path

    for i, system_name in enumerate(system_names, 1):
        print(f"\n[{i}/{len(system_names)}] Capturing: {system_name}")

        try:
            # Click, paste, enter, wait
            print(f"  -> Searching for system...")
            click_and_paste(SEARCH_X, SEARCH_Y, system_name, i)

            # Wait for map to load and display system info
            print(f"  -> Waiting for map to load...")
            time.sleep(1.0)

            # Take screenshot only (no OCR yet)
            print(f"  -> Taking screenshot...")
            screenshot_path = ocr.take_screenshot()

            # Save screenshot with system name
            if screenshot_path:
                import shutil

                # Sanitize system name for filename (replace invalid chars)
                safe_name = system_name.replace(' ', '_').replace('/', '-').replace('\\', '-')

                # Save the full screenshot with system name
                saved_path = f"auto_capture/screenshots/capture_{i:03d}_{safe_name}.png"
                shutil.move(screenshot_path, saved_path)
                screenshot_mapping[system_name] = (i, saved_path)

                print(f"  -> [OK] Screenshot saved!")
            else:
                print(f"  -> [ERROR] Screenshot failed!")

        except Exception as e:
            print(f"  -> [ERROR] {str(e)}")

        # Brief pause between systems
        if i < len(system_names):
            time.sleep(0.5)

    print("\n" + "=" * 80)
    print(f"PHASE 1 COMPLETE - CAPTURED {len(screenshot_mapping)}/{len(system_names)} SCREENSHOTS")
    print("=" * 80)

    # Play sound to indicate phase transition
    play_success_sound()
    time.sleep(0.3)
    play_success_sound()

    # =========================================================================
    # PHASE 2: PROCESS SCREENSHOTS WITH OCR (OFFLINE)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PHASE 2: PROCESSING SCREENSHOTS WITH OCR")
    print("=" * 80)
    print("\nYou can now close Elite Dangerous if needed.")
    print("Processing screenshots...")

    # Create directories for debug output
    os.makedirs('auto_capture/debug/cropped', exist_ok=True)
    os.makedirs('auto_capture/debug/ocr_text', exist_ok=True)
    os.makedirs('auto_capture/debug/subsections', exist_ok=True)

    # Initialize both output files with headers
    header = "System Name\tPower\tState\t\tUndermining\tReinforcement\tInitial CP\n"
    with open(main_output_file, 'w', encoding='utf-8') as f:
        f.write(header)
    with open(archive_output_file, 'w', encoding='utf-8') as f:
        f.write(header)

    collected_systems = {}

    # Process each screenshot
    for system_name, (i, screenshot_path) in screenshot_mapping.items():
        print(f"\n[{i}/{len(system_names)}] Processing: {system_name}")

        try:
            print(f"  -> Running OCR...")
            info = ocr.extract_powerplay_auto(screenshot_path)

            # Detect initial control points from status bar (non-competitive states only)
            is_competitive = 'powers' in info and info['powers']
            if not is_competitive:
                initial_cp = ocr.detect_initial_control_points_from_bar(screenshot_path)
                info['initial_control_points'] = initial_cp if initial_cp is not None else -1
            else:
                info['initial_control_points'] = -1  # Not applicable for competitive states

            # Get raw text for debug
            text = ocr.extract_text(screenshot_path, preprocess_method='upscale', crop_panel=False, use_subsections=False)

            # Determine if this is a competitive state
            is_competitive = 'powers' in info and info['powers']

            # Save cropped panel
            if is_competitive:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=True)
            else:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=False)
            cropped_path = f"auto_capture/debug/cropped/capture_{i:03d}.png"
            cropped_img.save(cropped_path)

            # Save subsections
            if is_competitive:
                subsections = ocr.crop_powerplay_subsections_competitive(screenshot_path)
            else:
                subsections = ocr.crop_powerplay_subsections(screenshot_path)
            for section_name, section_img in subsections.items():
                subsection_path = f"auto_capture/debug/subsections/capture_{i:03d}_{section_name}.png"
                section_img.save(subsection_path)

            # Save OCR text
            ocr_text_path = f"auto_capture/debug/ocr_text/capture_{i:03d}.txt"
            with open(ocr_text_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"CAPTURE #{i} - {system_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write("RAW OCR TEXT:\n")
                f.write("-" * 80 + "\n")
                f.write(text)
                f.write("\n" + "-" * 80 + "\n\n")
                f.write("PARSED DATA:\n")
                f.write(f"  System Name: '{info['system_name']}'\n")
                f.write(f"  Controlling Power: '{info['controlling_power']}'\n")
                f.write(f"  Opposing Power: '{info['opposing_power']}'\n")
                f.write(f"  System Status: '{info['system_status']}'\n")
                initial_cp = info.get('initial_control_points', -1)
                if initial_cp >= 0:
                    f.write(f"  Initial Control Points: {initial_cp:,}\n")
                f.write(f"  Undermining Points: {info['undermining_points']}\n")
                f.write(f"  Reinforcing Points: {info['reinforcing_points']}\n")

                # Add voting details if available (shows OCR accuracy)
                if '_undermining_votes' in info:
                    f.write(f"\n  OCR Voting Results (Undermining):\n")
                    f.write(f"    Votes: {info['_undermining_votes']}\n")
                    f.write(f"    Winner: {info['_undermining_winner']}\n")
                if '_reinforcing_votes' in info:
                    f.write(f"  OCR Voting Results (Reinforcing):\n")
                    f.write(f"    Votes: {info['_reinforcing_votes']}\n")
                    f.write(f"    Winner: {info['_reinforcing_winner']}\n")

            # Check if valid
            if ocr.is_valid_powerplay_data(info):
                parsed_name = info['system_name']

                print(f"  -> Parsed:")
                print(f"     System: {parsed_name}")
                print(f"     Status: {info['system_status']}")
                initial_cp = info.get('initial_control_points', -1)
                if initial_cp >= 0:
                    print(f"     Initial CP: {initial_cp:,}")

                if is_competitive:
                    print(f"     Type: COMPETITIVE")
                    for power_info in info.get('powers', []):
                        rank = power_info.get('rank', '?')
                        print(f"       {rank}. {power_info['name']}: {power_info['score']:,}")
                else:
                    print(f"     Type: STANDARD")
                    print(f"     Power: {info['controlling_power'] or info['opposing_power']}")
                    print(f"     CP: {info['undermining_points']} / {info['reinforcing_points']}")

                # Save to collected systems (use input system name as key)
                collected_systems[system_name] = info

                # Append to both output files (use original system name from input.txt)
                excel_line = ocr.format_for_excel(info, original_system_name=system_name)
                with open(main_output_file, 'a', encoding='utf-8') as f:
                    f.write(excel_line + '\n')
                with open(archive_output_file, 'a', encoding='utf-8') as f:
                    f.write(excel_line + '\n')

                print(f"  -> [OK] Data saved!")

                # Delete original full screenshot (keep cropped for debug)
                try:
                    os.remove(screenshot_path)
                except:
                    pass

            else:
                # Invalid parse
                missing = []
                if not info['system_name']:
                    missing.append("Name")
                if not (info['controlling_power'] or info['opposing_power']):
                    missing.append("Power")
                if not info['system_status']:
                    missing.append("Status")
                if info['undermining_points'] < 0:
                    missing.append("Under")
                if info['reinforcing_points'] < 0:
                    missing.append("Reinf")

                print(f"  -> [ERROR] Invalid: Missing {', '.join(missing)}")
                print(f"  -> Debug saved: {cropped_path}, {ocr_text_path}")

                # Keep the original screenshot for debugging failed parses
                # Don't delete it

        except Exception as e:
            print(f"  -> [ERROR] {str(e)}")
            # Keep the original screenshot for debugging errors

    # Print final summary
    print("\n" + "=" * 80)
    print(f"PROCESSING COMPLETE - PARSED {len(collected_systems)}/{len(system_names)} SYSTEMS")
    print("=" * 80)

    if collected_systems:
        print("\nSystem Name\tPower\tState\t\tUndermining\tReinforcement\tInitial CP")
        print("-" * 100)
        for system_name in sorted(collected_systems.keys()):
            info = collected_systems[system_name]
            # System name is already the original input name (used as dict key)
            excel_line = ocr.format_for_excel(info, original_system_name=system_name)
            print(excel_line)
        print("=" * 80)
        print(f"\nData saved to:")
        print(f"  Main file: {main_output_file}")
        print(f"  Archive:   {archive_output_file}")
        print("You can copy/paste this directly into Excel!")

        # Compare with previous capture to detect anomalies
        if previous_data and is_same_cycle:
            print("\n" + "=" * 80)
            print("CYCLE VALIDATION - CP values should only increase within a cycle")
            print("=" * 80)

            violations = []
            large_increases = []

            for system_name in sorted(collected_systems.keys()):
                if system_name not in previous_data:
                    continue

                current = collected_systems[system_name]
                previous = previous_data[system_name]

                current_u = current.get('undermining_points', -1)
                current_r = current.get('reinforcing_points', -1)
                prev_u = previous.get('undermining', -1)
                prev_r = previous.get('reinforcing', -1)

                # Check for decreases (possible OCR errors)
                u_decreased = prev_u >= 0 and current_u >= 0 and current_u < prev_u
                r_decreased = prev_r >= 0 and current_r >= 0 and current_r < prev_r

                if u_decreased or r_decreased:
                    violations.append({
                        'system': system_name,
                        'prev_u': prev_u,
                        'curr_u': current_u,
                        'prev_r': prev_r,
                        'curr_r': current_r,
                        'u_decreased': u_decreased,
                        'r_decreased': r_decreased
                    })

                # Check for suspiciously large increases (possible extra digit added by OCR)
                # Flag if increase is more than 9x the previous value (likely added a digit)
                # 9x catches most cases where digit is added (e.g., 2489 -> 24889 = 10x)
                if prev_u > 0 and current_u > 0:
                    u_ratio = current_u / prev_u
                    if u_ratio >= 9.0:  # Increased by 9x or more
                        large_increases.append({
                            'system': system_name,
                            'type': 'Undermining',
                            'prev': prev_u,
                            'curr': current_u,
                            'ratio': u_ratio
                        })

                if prev_r > 0 and current_r > 0:
                    r_ratio = current_r / prev_r
                    if r_ratio >= 9.0:  # Increased by 9x or more
                        large_increases.append({
                            'system': system_name,
                            'type': 'Reinforcing',
                            'prev': prev_r,
                            'curr': current_r,
                            'ratio': r_ratio
                        })

            if violations:
                print(f"\nWARNING: {len(violations)} system(s) with DECREASED CP (possible OCR errors):\n")
                print(f"{'System Name':<40} {'Type':<15} {'Previous':<12} {'Current':<12} {'Change'}")
                print("-" * 100)
                for v in violations:
                    name_short = v['system'][:38] if len(v['system']) > 38 else v['system']
                    if v['u_decreased']:
                        change = v['curr_u'] - v['prev_u']
                        print(f"{name_short:<40} {'Undermining':<15} {v['prev_u']:>10,}   {v['curr_u']:>10,}   {change:>+10,}")
                    if v['r_decreased']:
                        change = v['curr_r'] - v['prev_r']
                        print(f"{name_short:<40} {'Reinforcing':<15} {v['prev_r']:>10,}   {v['curr_r']:>10,}   {change:>+10,}")
                print("\n" + "=" * 80)
                print("These systems should be manually verified!")

            if large_increases:
                print(f"\n{'='*80}")
                print(f"WARNING: {len(large_increases)} system(s) with LARGE INCREASES (possible extra digit):\n")
                print(f"{'System Name':<40} {'Type':<15} {'Previous':<12} {'Current':<12} {'Ratio'}")
                print("-" * 100)
                for v in large_increases:
                    name_short = v['system'][:38] if len(v['system']) > 38 else v['system']
                    print(f"{name_short:<40} {v['type']:<15} {v['prev']:>10,}   {v['curr']:>10,}   {v['ratio']:>7.1f}x")
                print("\n" + "=" * 80)
                print("These increases are unusually large - verify they are correct!")

            if not violations and not large_increases:
                print("\nAll CP values are valid (no issues detected)")
                print(f"Compared {len([s for s in collected_systems.keys() if s in previous_data])} systems with previous capture")
            print("=" * 80)
        elif previous_data and not is_same_cycle:
            print("\n" + "=" * 80)
            print("CYCLE VALIDATION SKIPPED")
            print("=" * 80)
            print("\nPrevious capture is from a different cycle.")
            print("CP values reset after Thursday 7am UTC tick - validation not applicable.")
            print("=" * 80)
    else:
        print("\nNo valid systems captured.")

    print("\nDone!")

if __name__ == "__main__":
    main()
