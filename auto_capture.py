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

def click_and_paste(x, y, text):
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
    time.sleep(random.uniform(0.2, 1.0))

    # Click below to trigger search (move to y=204 with randomness)
    x_offset = random.randint(-10, 10)
    y_offset = random.randint(-5, 5)
    pyautogui.moveTo(x + x_offset, 204 + y_offset)
    time.sleep(random.uniform(0.2, 1.0))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.2, 1.0))
    pyautogui.mouseUp()

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
            click_and_paste(SEARCH_X, SEARCH_Y, system_name)

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

                # Append to output file
                with open(output_file, 'a', encoding='utf-8') as f:
                    excel_line = ocr.format_for_excel(info)
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
        for system_name in sorted(collected_systems.keys()):
            excel_line = ocr.format_for_excel(collected_systems[system_name])
            print(excel_line)
        print("=" * 80)
        print(f"\nData saved to: {output_file}")
        print("You can copy/paste this directly into Excel!")
    else:
        print("\nNo valid systems captured.")

    print("\nDone!")

if __name__ == "__main__":
    main()
