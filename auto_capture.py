#!/usr/bin/env python3
"""
Automated Powerplay System Capture
Reads system names from input.txt and automatically captures each one
"""

# Standard library imports
import concurrent.futures
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

# Third-party imports
import pyautogui
import shutil
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

def _roman_numeral_suffix(name_upper):
    """
    Return the trailing Roman-numeral token of a system name (e.g. 'I', 'II'),
    or None if the name doesn't end with one.

    Names like 'Hyadum I' / 'Hyadum II' differ only by this suffix and are
    easily confused by OCR (dropped/added stroke) or fuzzy string matching
    (they're ~90%+ similar). Extracting it lets matching treat it as a hard
    constraint instead of just another character in a similarity ratio.
    """
    m = re.search(r'\s([IVXLCDM]+)$', name_upper.strip())
    return m.group(1) if m else None


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
    # Config values are in reference pixels at 1440 height; scale to actual screen height
    _, actual_height = pyautogui.size()
    scale = actual_height / config.EXPECTED_SCREEN_HEIGHT
    dropdown_left = search_x + int(config.DROPDOWN_OFFSET_X * scale)
    dropdown_top = search_y + int(config.DROPDOWN_OFFSET_Y * scale)
    dropdown_width = int(config.DROPDOWN_WIDTH * scale)
    dropdown_max_height = int(config.DROPDOWN_MAX_HEIGHT * scale)

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

        # Scanning upward from the game map (bright), the first pair of dark rows marks
        # the bottom edge of the dropdown. Use that Y as the crop height with a small
        # margin. Do NOT keep scanning upward — that walks into the dropdown content
        # (orange text on dark bg, ~92% dark) and shrinks the crop to almost nothing.
        if dark_ratio_current >= dark_pixel_ratio_threshold and dark_ratio_prev >= dark_pixel_ratio_threshold:
            dropdown_height = min(y + 15, dropdown_max_height)
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

    # OCR the dropdown to find matching system names.
    # PSM 6 (uniform text block) keeps multi-word names like "HIP 1897" on one line,
    # unlike PSM 11 (sparse text) which splits them into separate tokens.
    text = pytesseract.image_to_string(
        preprocessed_pil,
        config='--oem 3 --psm 6'
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

        target_suffix = _roman_numeral_suffix(system_name_upper)

        for i, line in enumerate(lines):
            # Skip very short lines (likely noise)
            if len(line) < 5:
                continue

            # Names differing only by a Roman-numeral suffix (Hyadum I vs
            # Hyadum II) score ~90%+ on plain similarity — too close for
            # fuzzy matching to tell apart reliably. If the target has a
            # numeral suffix, reject candidates whose own suffix reads
            # differently, even if their overall similarity is higher.
            line_suffix = _roman_numeral_suffix(line)
            if target_suffix and line_suffix and line_suffix != target_suffix:
                continue

            # Calculate similarity ratio
            ratio = SequenceMatcher(None, system_name_upper, line).ratio()

            # Keep track of best match
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = i

        # Accept if similarity is at least 65%
        if best_ratio >= 0.65 and best_index >= 0:
            match_index = best_index
            match_method = f"fuzzy match ({best_ratio:.1%})"

    # Fallback: if no match found at all, use first valid line (skip very short ones)
    if match_index < 0:
        for i, line in enumerate(lines):
            if len(line) >= 5:  # Must be at least 5 characters to be a system name
                match_index = i
                match_method = "fallback (first valid line)"
                break

    if match_index >= 0:
        # Calculate click position
        # Each line is approximately 38 pixels tall at reference height (1440); scale to actual
        line_height = int(38 * scale)
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
    from datetime import datetime, timedelta, timezone

    # Get the reference time in UTC
    if reference_time.tzinfo is None:
        # Assume local time, convert to UTC
        local_tz = datetime.now().astimezone().tzinfo
        reference_utc = reference_time.replace(tzinfo=local_tz).astimezone(timezone.utc)
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

# Loaded from config — see config.py for full documentation and examples.
_WRITE_VK_OVERRIDES = config.WRITE_VK_OVERRIDES

def _write_text(text, interval=0.02):
    """
    Type text using pyautogui.write(). If the text contains characters that
    pyautogui mistypes (see _WRITE_VK_OVERRIDES), those are handled one at a
    time via keybd_event; surrounding plain segments are written in one call.
    """
    if not any(ch in _WRITE_VK_OVERRIDES for ch in text):
        pyautogui.write(text, interval=interval)
        return

    import ctypes
    KEYEVENTF_KEYUP = 0x0002
    keybd = ctypes.windll.user32.keybd_event

    segment = []
    for ch in text:
        if ch in _WRITE_VK_OVERRIDES:
            if segment:
                pyautogui.write(''.join(segment), interval=interval)
                segment = []
            vk = _WRITE_VK_OVERRIDES[ch]
            keybd(vk, 0, 0, 0)
            time.sleep(interval)
            keybd(vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(interval)
        else:
            segment.append(ch)
    if segment:
        pyautogui.write(''.join(segment), interval=interval)


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

    # Clear any existing text, then type with layout-aware overrides for
    # special characters like '+' that pyautogui.write() mistypes on German keyboards.
    pyautogui.press('backspace')
    time.sleep(random.uniform(0.2, 1.0))
    _write_text(text)

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


def _run_ocr_worker(ocr, i, system_name, screenshot_path):
    """
    Run the full OCR pipeline for one already-captured screenshot and write its
    per-index debug files (cropped panel, subsections, OCR text). Safe to call
    concurrently from multiple threads: every path this touches is keyed by `i`,
    so no two workers ever write the same file. Tesseract itself is a single-
    threaded external process, so running many of these in parallel threads lets
    multiple tesseract processes run at once across CPU cores.

    Deliberately does NOT touch collected_systems, last_data_age, or the shared
    output files — those are updated afterwards by the caller in original capture
    order so results stay deterministic regardless of which worker finishes first.
    """
    result = {
        'system_name': system_name,
        'i': i,
        'screenshot_path': screenshot_path,
        'error': None,
        'info': None,
        'is_competitive': False,
        'cropped_path': None,
        'ocr_text_path': None,
    }

    try:
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

        result['info'] = info
        result['is_competitive'] = is_competitive
        result['cropped_path'] = cropped_path
        result['ocr_text_path'] = ocr_text_path
    except Exception as e:
        result['error'] = str(e)

    return result


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
    print("\nBefore continuing, ensure the following:")
    print("  1. Elite Dangerous is running with the Galaxy Map open")
    print("  2. The Powerplay view is open in the right-hand panel")
    print("     (select the Powerplay tab in the panel on the right side)")
    print()
    print("Press ENTER when ready, then switch back to Elite Dangerous.")
    input()
    print("\nYou have 5 seconds to switch to Elite Dangerous...")
    for i in range(5, 0, -1):
        print(f"Starting in {i}...", end='\r')
        time.sleep(1)
    print("\nStarting automation...                ")
    print("=" * 80)

    ocr = PowerplayOCR()

    # Wipe stale capture data from previous runs so old images and OCR files
    # from a different cycle don't get picked up by build_capture_index_map().
    for _d in ['auto_capture/screenshots',
               'auto_capture/debug/cropped',
               'auto_capture/debug/ocr_text',
               'auto_capture/debug/subsections']:
        if os.path.exists(_d):
            shutil.rmtree(_d)
        os.makedirs(_d)

    # Search field coordinates: scale config values to actual screen resolution
    actual_width, actual_height = pyautogui.size()
    _scale = actual_height / config.EXPECTED_SCREEN_HEIGHT
    _x_offset = max(0, (actual_width - actual_height * 16 / 9) / 2)
    SEARCH_X = int(_x_offset + config.SEARCH_FIELD_X * _scale)
    SEARCH_Y = int(config.SEARCH_FIELD_Y * _scale)

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

    # Initialize both output files with headers (placeholder - will be updated with data_age)
    header_base = "System Name\tPower\tState\t\tUndermining\tReinforcement\tInitial CP"
    with open(main_output_file, 'w', encoding='utf-8') as f:
        f.write(header_base + "\n")
    with open(archive_output_file, 'w', encoding='utf-8') as f:
        f.write(header_base + "\n")

    collected_systems = {}
    last_data_age = None  # Track data age from most recent screenshot

    # Run OCR for every screenshot in parallel. Tesseract is a single-threaded
    # external process per call, so spreading calls across as many worker threads
    # as CPU cores lets that many tesseract processes run at once.
    items = list(screenshot_mapping.items())
    results = []
    if items:
        max_workers = min(len(items), os.cpu_count() or 4)
        print(f"Running OCR across {max_workers} parallel worker(s) "
              f"({os.cpu_count() or '?'} CPU core(s) detected)...")

        results = [None] * len(items)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_run_ocr_worker, ocr, i, system_name, screenshot_path): idx
                for idx, (system_name, (i, screenshot_path)) in enumerate(items)
            }
            done = 0
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
                done += 1
                print(f"  OCR done [{done}/{len(items)}]: {results[idx]['system_name']}")

    # Apply results in original capture order so output files and last_data_age
    # come out identical to a sequential run, regardless of which worker finished first.
    for result in results:
        system_name = result['system_name']
        i = result['i']
        screenshot_path = result['screenshot_path']
        print(f"\n[{i}/{len(system_names)}] Processing: {system_name}")

        if result['error']:
            print(f"  -> [ERROR] {result['error']}")
            # Keep the original screenshot for debugging errors
            continue

        try:
            info = result['info']
            is_competitive = result['is_competitive']
            cropped_path = result['cropped_path']
            ocr_text_path = result['ocr_text_path']

            # Update data_age from each screenshot (keep the last one)
            if info.get('data_age_minutes', -1) >= 0:
                last_data_age = info['data_age_minutes']

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

    # Update output files with data timestamp on separate line above header
    if last_data_age is not None and last_data_age >= 0:
        # Calculate actual timestamp from current time minus data age
        data_time = datetime.now(timezone.utc) - timedelta(minutes=last_data_age)
        data_age_line = data_time.strftime("%Y-%m-%d %H:%M UTC")
    else:
        data_age_line = None

    # Rewrite the files with data_age line above header
    for output_file in [main_output_file, archive_output_file]:
        with open(output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Insert data_age line before header, replace old header
        if lines:
            if data_age_line:
                lines[0] = f"{data_age_line}\n{header_base}\n"
            else:
                lines[0] = f"{header_base}\n"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    # Print final summary
    print("\n" + "=" * 80)
    print(f"PROCESSING COMPLETE - PARSED {len(collected_systems)}/{len(system_names)} SYSTEMS")
    if data_age_line:
        print(f"Data timestamp: {data_age_line}")
    print("=" * 80)

    if collected_systems:
        if data_age_line:
            print(f"\n{data_age_line}")
        print(header_base)
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

    # Play sound to indicate that parsing has finished
    play_success_sound()
    time.sleep(0.3)
    play_success_sound()

if __name__ == "__main__":
    main()
