"""
Test script for EXPANSION/CONTESTED state parsing
"""
from powerplay_ocr import PowerplayOCR
import os

def main():
    print("=" * 80)
    print("TESTING COMPETITIVE STATE PARSING (EXPANSION/CONTESTED)")
    print("=" * 80)

    ocr = PowerplayOCR()

    # Test screenshots
    test_screenshots = [
        'screenshots/Screenshot 2025-12-30 132535.png',
        'screenshots/Screenshot 2025-12-30 132552.png'
    ]

    for screenshot_path in test_screenshots:
        if not os.path.exists(screenshot_path):
            print(f"\nERROR: Screenshot not found: {screenshot_path}")
            continue

        print(f"\n{'=' * 80}")
        print(f"Testing: {screenshot_path}")
        print("=" * 80)

        try:
            # Extract competitive state data
            info = ocr.extract_powerplay_competitive(screenshot_path)

            print("\nPARSED DATA:")
            print(f"  System Name: '{info['system_name']}'")
            print(f"  System Status: '{info['system_status']}'")
            print(f"\n  Powers:")
            for power in info['powers']:
                print(f"    {power['rank']}. {power['name']}: {power['score']:,}")
            print(f"\n  Your Power: '{info['your_power']}'")
            print(f"  Your Rank: '{info['your_rank']}'")
            print(f"\n  Controlling Power (1st): '{info['controlling_power']}'")
            print(f"  Opposing Power (2nd): '{info['opposing_power']}'")

            # Also save cropped subsections for verification
            print("\nSaving subsections for verification...")
            subsections = ocr.crop_powerplay_subsections_competitive(screenshot_path)

            # Create debug directory
            debug_dir = 'competitive_debug'
            os.makedirs(debug_dir, exist_ok=True)

            # Get base filename
            base_name = os.path.splitext(os.path.basename(screenshot_path))[0]

            for section_name, section_img in subsections.items():
                section_path = f"{debug_dir}/{base_name}_{section_name}.png"
                section_img.save(section_path)

            print(f"  Subsections saved to: {debug_dir}/")

        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
