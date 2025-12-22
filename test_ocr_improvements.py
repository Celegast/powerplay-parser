"""
Test OCR improvements on failing captures
Compare old vs new preprocessing methods
"""
from powerplay_ocr import PowerplayOCR
import os

def test_ocr_on_capture(capture_num, expected_power):
    """Test OCR on a specific capture with different methods"""
    ocr = PowerplayOCR()

    cropped_path = f"live_demo_debug/cropped/capture_{capture_num:03d}.png"

    if not os.path.exists(cropped_path):
        print(f"File not found: {cropped_path}")
        return

    print(f"\n{'='*80}")
    print(f"CAPTURE #{capture_num} - Expected Power: {expected_power}")
    print(f"{'='*80}")

    methods = [
        ('enhanced', 'Enhanced (new)'),
        ('upscale', 'Upscale (old)'),
        ('threshold', 'Threshold'),
        ('clahe', 'CLAHE')
    ]

    for method, description in methods:
        # Don't crop again - the image is already cropped
        text = ocr.extract_text(cropped_path, preprocess_method=method, crop_panel=False)
        info = ocr.parse_powerplay_info(text)

        detected_power = info['controlling_power'] or info['opposing_power'] or '(none)'
        match = "[OK]" if expected_power.lower() in detected_power.lower() else "[FAIL]"

        print(f"\n{description}:")
        print(f"  Detected Power: {detected_power} {match}")
        print(f"  System: {info['system_name']}")
        print(f"  Status: {info['system_status']}")
        print(f"  Points: {info['undermining_points']} / {info['reinforcing_points']}")

def main():
    """Test OCR improvements on all failing captures"""

    failing_captures = [
        (1, "Pranav Antal"),
        (6, "Nakato Kaine"),
        (7, "Li Yong-Rui"),  # This one fails on number parsing
        (8, "Edmund Mahon"),
        (12, "Yuri Grom")
    ]

    print("="*80)
    print("TESTING OCR IMPROVEMENTS")
    print("="*80)
    print("\nComparing different preprocessing methods on failing captures...")

    for capture_num, expected_power in failing_captures:
        test_ocr_on_capture(capture_num, expected_power)

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
