"""
Test Excel formatting for both standard and competitive states
"""
from powerplay_ocr import PowerplayOCR
import os

def main():
    print("=" * 80)
    print("TESTING EXCEL FORMAT OUTPUT (MIXED STATES)")
    print("=" * 80)

    ocr = PowerplayOCR()

    # Mix of standard and competitive states
    test_screenshots = [
        'screenshots/powerplay_20251221_122751.png',
        'screenshots/powerplay_20251221_122824.png',
        'screenshots/Screenshot 2025-12-30 132535.png',
        'screenshots/Screenshot 2025-12-30 132552.png',
    ]

    print("\nSystem Name\tPower\tState\t\tUndermining\tReinforcement")
    print("-" * 80)

    for screenshot_path in test_screenshots:
        if not os.path.exists(screenshot_path):
            continue

        try:
            # Use auto-detection
            info = ocr.extract_powerplay_auto(screenshot_path)

            # Format for Excel
            excel_line = ocr.format_for_excel(info)
            print(excel_line)

        except Exception as e:
            print(f"ERROR: {screenshot_path} - {str(e)}")

    print("=" * 80)
    print("\nColumn mapping:")
    print("  Standard states:")
    print("    Power = Controlling Power")
    print("    State = System Status (EXPLOITED, FORTIFIED, STRONGHOLD)")
    print("    Undermining = Undermining points")
    print("    Reinforcement = Reinforcing points")
    print("\n  Competitive states:")
    print("    Power = 1st ranked power name")
    print("    State = 2nd ranked power name")
    print("    Undermining = 2nd power control points")
    print("    Reinforcement = 1st power control points")
    print("=" * 80)

if __name__ == "__main__":
    main()
