#!/usr/bin/env python3
"""
Test script to check initial CP detection on cropped debug images
"""
from powerplay_ocr import PowerplayOCR
import os
import glob

def main():
    ocr = PowerplayOCR()

    # Find all cropped debug images
    cropped_dir = "auto_capture_debug/cropped"
    if not os.path.exists(cropped_dir):
        print(f"Directory not found: {cropped_dir}")
        return

    image_files = sorted(glob.glob(os.path.join(cropped_dir, "capture_*.png")))

    if not image_files:
        print(f"No capture images found in {cropped_dir}")
        return

    print("=" * 80)
    print("TESTING INITIAL CONTROL POINTS DETECTION")
    print("=" * 80)
    print(f"\nFound {len(image_files)} images\n")

    results = []

    for img_path in image_files:
        filename = os.path.basename(img_path)

        try:
            # Detect initial CP from the status bar
            initial_cp = ocr.detect_initial_control_points_from_bar(img_path)

            if initial_cp is not None:
                # Determine which state range it falls into
                if initial_cp == 0:
                    state_range = "UNOCCUPIED (0 CP)"
                elif initial_cp < 350000:
                    state_range = f"EXPLOITED (0-350K)"
                elif initial_cp < 1000000:
                    state_range = f"FORTIFIED (350K-1M)"
                else:
                    state_range = f"STRONGHOLD (1M-2M)"

                result = f"{filename}: {initial_cp:,} CP ({state_range})"
                print(result)
                results.append((filename, initial_cp, state_range))
            else:
                result = f"{filename}: FAILED - No white marker detected"
                print(result)
                results.append((filename, None, "FAILED"))

        except Exception as e:
            result = f"{filename}: ERROR - {str(e)}"
            print(result)
            results.append((filename, None, f"ERROR: {str(e)}"))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r[1] is not None]
    failed = [r for r in results if r[1] is None]

    print(f"\nSuccessful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")

    if successful:
        print("\n" + "-" * 80)
        print("SUCCESSFUL DETECTIONS:")
        print("-" * 80)
        for filename, cp, state_range in successful:
            print(f"  {filename}: {cp:,} CP ({state_range})")

    if failed:
        print("\n" + "-" * 80)
        print("FAILED DETECTIONS:")
        print("-" * 80)
        for filename, _, reason in failed:
            print(f"  {filename}: {reason}")

if __name__ == "__main__":
    main()
