"""
Test parsing improvements against all captures in live_demo_debug
"""
from powerplay_ocr import PowerplayOCR
import os

def load_correct_data(filepath):
    """Load the correct data from the tab-separated file"""
    correct_data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Skip header line
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 6:
                system_name = parts[0]
                power = parts[1]
                state = parts[2]
                undermining = parts[4] if parts[4] else '0'
                reinforcement = parts[5] if parts[5] else '0'

                correct_data[system_name] = {
                    'system_name': system_name,
                    'power': power,
                    'state': state,
                    'undermining': int(undermining),
                    'reinforcement': int(reinforcement)
                }
    return correct_data

def test_parsing():
    """Test parsing against all captures"""
    ocr = PowerplayOCR()

    # Load correct data
    correct_data = load_correct_data('live_demo_debug/correct_data.txt')

    print("=" * 100)
    print("TESTING PARSING IMPROVEMENTS")
    print("=" * 100)
    print()

    results = []
    total_tests = 0
    passed_tests = 0

    # Test each capture
    for i in range(1, 13):
        capture_num = f"{i:03d}"
        ocr_text_file = f"live_demo_debug/ocr_text/capture_{capture_num}.txt"

        if not os.path.exists(ocr_text_file):
            continue

        total_tests += 1

        # Extract the raw OCR text from the file
        with open(ocr_text_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract just the raw OCR text section
            raw_text_start = content.find("RAW OCR TEXT:")
            raw_text_end = content.find("PARSED DATA:")
            if raw_text_start == -1 or raw_text_end == -1:
                continue

            raw_text = content[raw_text_start:raw_text_end]
            # Remove the header and separator lines
            lines = raw_text.split('\n')
            raw_text = '\n'.join(lines[2:])  # Skip "RAW OCR TEXT:" and "---" lines

        # Parse the text
        info = ocr.parse_powerplay_info(raw_text)

        # Find matching system in correct data
        system_name = info['system_name']
        if system_name not in correct_data:
            print(f"Capture #{i:02d}: [X] System '{system_name}' not found in correct data")
            results.append((i, False, "System not found in correct data"))
            continue

        expected = correct_data[system_name]

        # Check each field
        errors = []

        # Power - check both controlling and opposing
        actual_power = info['controlling_power'] or info['opposing_power']
        if actual_power != expected['power']:
            errors.append(f"Power: expected '{expected['power']}', got '{actual_power}'")

        # State
        if info['system_status'] != expected['state']:
            errors.append(f"State: expected '{expected['state']}', got '{info['system_status']}'")

        # Undermining
        if info['undermining_points'] != expected['undermining']:
            errors.append(f"Undermining: expected {expected['undermining']}, got {info['undermining_points']}")

        # Reinforcement
        if info['reinforcing_points'] != expected['reinforcement']:
            errors.append(f"Reinforcement: expected {expected['reinforcement']}, got {info['reinforcing_points']}")

        # Print result
        if errors:
            print(f"Capture #{i:02d} ({system_name}): FAILED")
            for error in errors:
                print(f"  - {error}")
            results.append((i, False, errors))
        else:
            print(f"Capture #{i:02d} ({system_name}): PASSED")
            passed_tests += 1
            results.append((i, True, None))
        print()

    # Print summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests / total_tests * 100) if total_tests > 0 else 0:.1f}%")
    print()

    # Print failed tests details
    if passed_tests < total_tests:
        print("=" * 100)
        print("FAILED TESTS DETAILS")
        print("=" * 100)
        for capture_num, passed, errors in results:
            if not passed and errors != "System not found in correct data":
                print(f"\nCapture #{capture_num}:")
                for error in errors:
                    print(f"  - {error}")

if __name__ == "__main__":
    test_parsing()
