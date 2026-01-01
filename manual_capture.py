"""
Manual Powerplay Capture
Interactive tool for manually capturing powerplay data system-by-system
Press F9 to capture current system
Press ESC to exit
"""

# Standard library imports
import os
import time

# Third-party imports
import keyboard
import winsound

# Local imports
from powerplay_ocr import PowerplayOCR

def play_success_sound():
    """Play a success sound (high beep)"""
    try:
        winsound.Beep(1000, 200)  # 1000 Hz for 200ms
    except:
        print('\a')  # Fallback to system beep

def play_error_sound():
    """Play an error sound (low beep)"""
    try:
        winsound.Beep(400, 400)  # 400 Hz for 400ms
    except:
        print('\a\a')  # Fallback to double beep

if __name__ == "__main__":
    print("=" * 80)
    print("ELITE DANGEROUS POWERPLAY OCR - LIVE DEMO")
    print("=" * 80)
    print("\nManual capture mode with auto-detection and audio feedback")
    print("\nInstructions:")
    print("1. Switch to Elite Dangerous")
    print("2. Open the Galaxy Map and view Powerplay Information for a system")
    print("3. Press F9 to CAPTURE the current system")
    print("4. Auto-detects state type (Standard or Competitive)")
    print("5. Valid data is auto-accepted and saved immediately")
    print("6. Audio feedback:")
    print("   - HIGH beep = Valid data captured successfully")
    print("   - LOW beep = Invalid/incomplete data or duplicate")
    print("7. Press ESC to exit and view results")
    print("\n" + "=" * 80)
    print("\nReady! Press F9 to capture your first system...")
    print("=" * 80)

    ocr = PowerplayOCR()
    output_file = 'powerplay_live_demo.txt'
    collected_systems = {}
    capture_count = 0

    # Create directories for debug output
    os.makedirs('live_demo_debug/cropped', exist_ok=True)
    os.makedirs('live_demo_debug/ocr_text', exist_ok=True)
    os.makedirs('live_demo_debug/subsections', exist_ok=True)

    # Initialize output file with header
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("System Name\tPower\tState\t\tUndermining\tReinforcement\n")

    def save_to_file():
        """Save all collected systems to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("System Name\tPower\tState\t\tUndermining\tReinforcement\n")
            for system_name in sorted(collected_systems.keys()):
                excel_line = ocr.format_for_excel(collected_systems[system_name])
                f.write(excel_line + '\n')

    def on_f9_press():
        """Handle F9 key press - capture and parse screenshot"""
        global capture_count
        capture_count += 1

        print(f"\n[{time.strftime('%H:%M:%S')}] Capture #{capture_count} - Processing...")

        try:
            # Take screenshot
            screenshot_path = ocr.take_screenshot()

            # Extract and parse using auto-detection (handles all state types)
            info = ocr.extract_powerplay_auto(screenshot_path)

            # Also get raw text for debug output
            text = ocr.extract_text(screenshot_path, preprocess_method='upscale', crop_panel=False, use_subsections=False)

            # Determine if this is a competitive state
            is_competitive = 'powers' in info and info['powers']

            # Save cropped panel for verification
            if is_competitive:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=True)
            else:
                cropped_img = ocr.crop_powerplay_panel(screenshot_path, extended=False)
            cropped_path = f"live_demo_debug/cropped/capture_{capture_count:03d}.png"
            cropped_img.save(cropped_path)

            # Save subsections for debugging
            if is_competitive:
                subsections = ocr.crop_powerplay_subsections_competitive(screenshot_path)
            else:
                subsections = ocr.crop_powerplay_subsections(screenshot_path)
            for section_name, section_img in subsections.items():
                subsection_path = f"live_demo_debug/subsections/capture_{capture_count:03d}_{section_name}.png"
                section_img.save(subsection_path)

            # Save OCR text for verification
            ocr_text_path = f"live_demo_debug/ocr_text/capture_{capture_count:03d}.txt"
            with open(ocr_text_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"CAPTURE #{capture_count}\n")
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
                system_name = info['system_name']

                # Check for duplicate
                if system_name not in collected_systems:
                    excel_line = ocr.format_for_excel(info)

                    # Display parsed data
                    print(f"\n  System: {info['system_name']}")
                    print(f"  Status: {info['system_status']}")

                    # Display based on state type
                    if is_competitive:
                        print(f"  State Type: COMPETITIVE")
                        for power_info in info.get('powers', []):
                            rank = power_info.get('rank', '?')
                            print(f"    {rank}. {power_info['name']}: {power_info['score']:,}")
                    else:
                        print(f"  State Type: STANDARD")
                        print(f"  Power: {info['controlling_power'] or info['opposing_power']}")
                        print(f"  Under/Reinf: {info['undermining_points']} / {info['reinforcing_points']}")

                    print(f"\n  Excel format: {excel_line}")

                    # Auto-accept valid data (no confirmation needed)
                    collected_systems[system_name] = info
                    print("\n  [OK] AUTO-ACCEPTED - Data saved!")
                    play_success_sound()

                    # Save to file immediately
                    save_to_file()
                    print(f"  Total systems: {len(collected_systems)}")

                    # Delete original screenshot (keep cropped for debug)
                    try:
                        os.remove(screenshot_path)
                    except:
                        pass
                else:
                    print(f"\n  [WARN] DUPLICATE: {system_name} (already captured)")
                    play_error_sound()
                    # Delete screenshots for duplicates
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

                print(f"\n  [X] INVALID: Missing {', '.join(missing)}")
                print(f"  Debug saved: {cropped_path}, {ocr_text_path}")
                print(f"  Screenshot: {screenshot_path}")
                play_error_sound()

        except Exception as e:
            print(f"\n  [X] ERROR: {str(e)}")
            play_error_sound()

    # Register F9 hotkey
    keyboard.add_hotkey('f9', on_f9_press)

    # Wait for ESC to exit
    try:
        keyboard.wait('esc')
    except KeyboardInterrupt:
        pass

    # Print final summary
    print("\n" + "=" * 80)
    print(f"SESSION COMPLETE - CAPTURED {len(collected_systems)} SYSTEMS")
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

    print("\nExiting...")
