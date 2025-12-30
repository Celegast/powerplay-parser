#!/usr/bin/env python3
"""Test the new subsection-based parser on existing screenshots"""

from powerplay_ocr import PowerplayOCR
import os

def test_subsection_parser():
    ocr = PowerplayOCR()

    # Test on a few screenshots
    test_files = [
        'screenshots/powerplay_20251223_101904.png',
        'screenshots/powerplay_20251223_101905.png',
        'screenshots/powerplay_20251223_101906.png',
    ]

    for screenshot in test_files:
        if not os.path.exists(screenshot):
            continue

        print(f"\n{'='*80}")
        print(f"Testing: {screenshot}")
        print('='*80)

        try:
            info = ocr.extract_powerplay_subsections_optimized(screenshot)

            print(f"\nParsed Data:")
            print(f"  System Name: '{info.get('system_name', 'MISSING')}'")
            print(f"  Controlling Power: '{info.get('controlling_power', 'MISSING')}'")
            print(f"  System Status: '{info.get('system_status', 'MISSING')}'")
            print(f"  Undermining Points: {info.get('undermining_points', 'MISSING')}")
            print(f"  Reinforcing Points: {info.get('reinforcing_points', 'MISSING')}")

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_subsection_parser()
