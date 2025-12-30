#!/usr/bin/env python3
"""Test the subsection parser on all screenshots"""

from powerplay_ocr import PowerplayOCR
import os

def test_all_screenshots():
    ocr = PowerplayOCR()

    # Get all PNG files in screenshots folder
    screenshot_files = sorted([f for f in os.listdir('screenshots') if f.endswith('.png')])

    print("Testing subsection parser on all screenshots:")
    print("=" * 80)

    for screenshot_file in screenshot_files:
        screenshot_path = os.path.join('screenshots', screenshot_file)

        print(f"\n{screenshot_file}:")

        try:
            info = ocr.extract_powerplay_subsections_optimized(screenshot_path)

            print(f"  System Name: {info.get('system_name', 'MISSING')}")
            print(f"  Controlling Power: {info.get('controlling_power', 'MISSING')}")
            print(f"  System Status: {info.get('system_status', 'MISSING')}")
            print(f"  Undermining: {info.get('undermining_points', 'MISSING')}")
            print(f"  Reinforcing: {info.get('reinforcing_points', 'MISSING')}")

        except Exception as e:
            print(f"  [ERROR] {str(e)}")

if __name__ == '__main__':
    test_all_screenshots()
