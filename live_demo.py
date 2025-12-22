"""
Live Demo - Manual Powerplay Capture with Audio Feedback
Press F9 to capture each system
Press ESC to exit
"""
from powerplay_ocr import PowerplayOCR
import keyboard
import winsound
import os
import time

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
    print("\nManual capture mode with audio feedback")
    print("\nInstructions:")
    print("1. Switch to Elite Dangerous")
    print("2. Open the Galaxy Map and view Powerplay Information for a system")
    print("3. Press F9 to CAPTURE the current system")
    print("4. You'll hear:")
    print("   - HIGH beep = Valid data captured successfully")
    print("   - LOW beep = Invalid/incomplete data")
    print("5. Press ESC to exit and view results")
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

            # Extract and parse
            text = ocr.extract_text(screenshot_path)
            info = ocr.parse_powerplay_info(text)

            # Save cropped image for verification
            cropped_img = ocr.crop_powerplay_panel(screenshot_path)
            cropped_path = f"live_demo_debug/cropped/capture_{capture_count:03d}.png"
            cropped_img.save(cropped_path)

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
                f.write(f"  Distance: {info['distance_ly']} LY\n")

            # Check if valid
            if ocr.is_valid_powerplay_data(info):
                system_name = info['system_name']

                # Check for duplicate
                if system_name not in collected_systems:
                    excel_line = ocr.format_for_excel(info)

                    # Display parsed data
                    print(f"\n  System: {info['system_name']}")
                    print(f"  Power: {info['controlling_power'] or info['opposing_power']}")
                    print(f"  Status: {info['system_status']}")
                    print(f"  Under/Reinf: {info['undermining_points']} / {info['reinforcing_points']}")
                    print(f"\n  Excel format: {excel_line}")
                    print(f"\n  Debug saved: {cropped_path}")

                    # Ask for confirmation
                    print("\n  Is this correct? (Y/n/r) [Y=yes, n=no/skip, r=retry]")
                    print("  Press 'y' or SPACE to accept, 'n' to reject, 'r' to retry capture...")

                    # Wait for confirmation (with timeout)
                    import msvcrt
                    start_time = time.time()
                    response = None

                    while time.time() - start_time < 10:  # 10 second timeout
                        if msvcrt.kbhit():
                            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                            if key in ['y', ' ', '\r']:  # Yes
                                response = 'y'
                                break
                            elif key == 'n':  # No
                                response = 'n'
                                break
                            elif key == 'r':  # Retry
                                response = 'r'
                                break
                        time.sleep(0.1)

                    # Default to yes if timeout
                    if response is None:
                        response = 'y'
                        print("  (Auto-accepted after 10s)")

                    if response == 'y':
                        collected_systems[system_name] = info
                        print("\n  ✓ ACCEPTED - Data saved!")
                        play_success_sound()

                        # Save to file immediately
                        save_to_file()
                        print(f"  Total systems: {len(collected_systems)}")

                        # Delete original screenshot (keep cropped for debug)
                        try:
                            os.remove(screenshot_path)
                        except:
                            pass

                    elif response == 'n':
                        print("\n  ✗ REJECTED - Data discarded")
                        play_error_sound()
                        # Keep both screenshots and debug files for review

                    elif response == 'r':
                        print("\n  ⟳ RETRY - Please press F9 again")
                        # Keep files for comparison
                else:
                    print(f"\n  ⚠ DUPLICATE: {system_name} (already captured)")
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

                print(f"\n  ✗ INVALID: Missing {', '.join(missing)}")
                print(f"  Debug saved: {cropped_path}, {ocr_text_path}")
                print(f"  Screenshot: {screenshot_path}")
                play_error_sound()

        except Exception as e:
            print(f"\n  ✗ ERROR: {str(e)}")
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
