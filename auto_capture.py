#!/usr/bin/env python3
"""
Automated Powerplay System Capture
Reads system names from input.txt and automatically captures each one
"""
from powerplay_ocr import PowerplayOCR
import pyautogui
import time
import os
import winsound
import random
import ctypes
from ctypes import wintypes

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
    # Approximate dropdown region (adjust based on your resolution)
    # Search field is at (2700, 168), dropdown starts 10 pixels below
    dropdown_left = search_x - 460
    dropdown_top = search_y + 25
    dropdown_width = 450
    dropdown_height = 400  # Capture enough for ~10 results

    # Take screenshot of dropdown area immediately (dropdown should already be visible)
    screenshot = pyautogui.screenshot(region=(dropdown_left, dropdown_top, dropdown_width, dropdown_height))

    # Save screenshot for debugging
    debug_path = f"auto_capture_debug/dropdown/dropdown_{debug_index:03d}.png"
    os.makedirs('auto_capture_debug/dropdown', exist_ok=True)
    screenshot.save(debug_path)

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
    preprocessed_path = f"auto_capture_debug/dropdown/dropdown_{debug_index:03d}_preprocessed.png"
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
    ocr_debug_path = f"auto_capture_debug/dropdown/dropdown_{debug_index:03d}_ocr.txt"
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
        from difflib import SequenceMatcher
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
    print("2. Click the search field and enter each system")
    print("3. Wait for the map to load")
    print("4. Capture and parse the Powerplay information")
    print("\n" + "=" * 80)

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

    print("\n" + "=" * 80)
    print("\nYou have 5 seconds to switch to Elite Dangerous...")
    print("Make sure the Galaxy Map is open and ready!")
    for i in range(5, 0, -1):
        print(f"Starting in {i}...", end='\r')
        time.sleep(1)
    print("\nStarting automation...                ")
    print("=" * 80)

    ocr = PowerplayOCR()
    output_file = 'powerplay_auto_capture.txt'
    collected_systems = {}

    # Create directories for debug output
    os.makedirs('auto_capture_debug/cropped', exist_ok=True)
    os.makedirs('auto_capture_debug/ocr_text', exist_ok=True)
    os.makedirs('auto_capture_debug/subsections', exist_ok=True)

    # Search field coordinates
    SEARCH_X = 2700
    SEARCH_Y = 168

    # Initialize output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("System Name\tPower\tState\t\tUndermining\tReinforcement\n")

    # Process each system
    for i, system_name in enumerate(system_names, 1):
        print(f"\n[{i}/{len(system_names)}] Processing: {system_name}")

        try:
            # Step 1-4: Click, paste, enter, wait
            print(f"  -> Searching for system...")
            click_and_paste(SEARCH_X, SEARCH_Y, system_name, i)

            # Wait for map to load and display system info
            print(f"  -> Waiting for map to load (3 seconds)...")
            time.sleep(3)

            # Step 5: Take screenshot and parse
            print(f"  -> Capturing screenshot...")
            screenshot_path = ocr.take_screenshot()

            print(f"  -> Parsing Powerplay information...")
            info = ocr.extract_powerplay_auto(screenshot_path)

            # Get raw text for debug
            text = ocr.extract_text(screenshot_path, preprocess_method='upscale', crop_panel=False, use_subsections=False)

            # Determine if this is a competitive state
            is_competitive = 'powers' in info and info['powers']

            # Save cropped panel
            if is_competitive:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=True)
            else:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=False)
            cropped_path = f"auto_capture_debug/cropped/capture_{i:03d}.png"
            cropped_img.save(cropped_path)

            # Save subsections
            if is_competitive:
                subsections = ocr.crop_powerplay_subsections_competitive(screenshot_path)
            else:
                subsections = ocr.crop_powerplay_subsections(screenshot_path)
            for section_name, section_img in subsections.items():
                subsection_path = f"auto_capture_debug/subsections/capture_{i:03d}_{section_name}.png"
                section_img.save(subsection_path)

            # Save OCR text
            ocr_text_path = f"auto_capture_debug/ocr_text/capture_{i:03d}.txt"
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
                f.write(f"  Undermining Points: {info['undermining_points']}\n")
                f.write(f"  Reinforcing Points: {info['reinforcing_points']}\n")

            # Check if valid
            if ocr.is_valid_powerplay_data(info):
                parsed_name = info['system_name']

                print(f"  -> Parsed:")
                print(f"     System: {parsed_name}")
                print(f"     Status: {info['system_status']}")

                if is_competitive:
                    print(f"     Type: COMPETITIVE")
                    for power_info in info.get('powers', []):
                        rank = power_info.get('rank', '?')
                        print(f"       {rank}. {power_info['name']}: {power_info['score']:,}")
                else:
                    print(f"     Type: STANDARD")
                    print(f"     Power: {info['controlling_power'] or info['opposing_power']}")
                    print(f"     CP: {info['undermining_points']} / {info['reinforcing_points']}")

                # Save to collected systems
                collected_systems[parsed_name] = info

                # Append to output file (use original system name from input.txt)
                with open(output_file, 'a', encoding='utf-8') as f:
                    excel_line = ocr.format_for_excel(info, original_system_name=system_name)
                    f.write(excel_line + '\n')

                print(f"  -> [OK] Data saved!")
                play_success_sound()

                # Delete original screenshot (keep cropped for debug)
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
                play_error_sound()

        except Exception as e:
            print(f"  -> [ERROR] {str(e)}")
            play_error_sound()

        # Brief pause between systems
        if i < len(system_names):
            time.sleep(0.5)

    # Print final summary
    print("\n" + "=" * 80)
    print(f"AUTOMATION COMPLETE - CAPTURED {len(collected_systems)}/{len(system_names)} SYSTEMS")
    print("=" * 80)

    if collected_systems:
        print("\nSystem Name\tPower\tState\t\tUndermining\tReinforcement")
        print("-" * 80)
        for parsed_name in sorted(collected_systems.keys()):
            info = collected_systems[parsed_name]
            # Find the original system name from input.txt by matching the parsed name
            # Since we stored by parsed_name but want to display original name
            original_name = parsed_name  # Use parsed name as fallback
            for input_system_name in system_names:
                # Fuzzy match to find the original name
                from difflib import SequenceMatcher
                if SequenceMatcher(None, input_system_name.upper(), parsed_name.upper()).ratio() >= 0.7:
                    original_name = input_system_name
                    break
            excel_line = ocr.format_for_excel(info, original_system_name=original_name)
            print(excel_line)
        print("=" * 80)
        print(f"\nData saved to: {output_file}")
        print("You can copy/paste this directly into Excel!")
    else:
        print("\nNo valid systems captured.")

    print("\nDone!")

if __name__ == "__main__":
    main()
