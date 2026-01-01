"""
Test subsection-based OCR vs regular OCR
"""
from powerplay_ocr import PowerplayOCR
import os

def test_subsection_ocr(capture_num, expected_power):
    """Test subsection-based OCR on a specific capture"""
    ocr = PowerplayOCR()

    cropped_path = f"live_demo_debug/cropped/capture_{capture_num:03d}.png"

    if not os.path.exists(cropped_path):
        print(f"File not found: {cropped_path}")
        return

    print(f"\n{'='*80}")
    print(f"CAPTURE #{capture_num} - Expected Power: {expected_power}")
    print(f"{'='*80}")

    # Test regular OCR
    print("\n[REGULAR OCR - Upscale]")
    text_regular = ocr.extract_text(cropped_path, preprocess_method='upscale', crop_panel=False, use_subsections=False)
    info_regular = ocr.parse_powerplay_info(text_regular)
    power_regular = info_regular['controlling_power'] or info_regular['opposing_power'] or '(none)'
    match_regular = "[OK]" if expected_power.lower() in power_regular.lower() else "[FAIL]"
    print(f"  Power: {power_regular} {match_regular}")
    print(f"  System: {info_regular['system_name']}")
    print(f"  Status: {info_regular['system_status']}")
    print(f"  Points: {info_regular['undermining_points']} / {info_regular['reinforcing_points']}")

    # Test subsection-based OCR
    print("\n[SUBSECTION OCR - Upscale]")
    text_subsection = ocr.extract_text(cropped_path, preprocess_method='upscale', use_subsections=True)
    info_subsection = ocr.parse_powerplay_info(text_subsection)
    power_subsection = info_subsection['controlling_power'] or info_subsection['opposing_power'] or '(none)'
    match_subsection = "[OK]" if expected_power.lower() in power_subsection.lower() else "[FAIL]"
    print(f"  Power: {power_subsection} {match_subsection}")
    print(f"  System: {info_subsection['system_name']}")
    print(f"  Status: {info_subsection['system_status']}")
    print(f"  Points: {info_subsection['undermining_points']} / {info_subsection['reinforcing_points']}")

    # Show improvement
    if match_regular == "[FAIL]" and match_subsection == "[OK]":
        print("\n  >>> SUBSECTION METHOD FIXED THIS! <<<")
    elif match_regular == "[OK]" and match_subsection == "[FAIL]":
        print("\n  >>> WARNING: SUBSECTION METHOD BROKE THIS <<<")

def main():
    """Test subsection approach on failing captures"""

    failing_captures = [
        (1, "Pranav Antal"),
        (6, "Nakato Kaine"),
        (7, "Li Yong-Rui"),
        (8, "Edmund Mahon"),
        (12, "Yuri Grom")
    ]

    print("="*80)
    print("TESTING SUBSECTION-BASED OCR")
    print("="*80)
    print("\nComparing regular OCR vs subsection-based OCR...")

    improvements = 0
    regressions = 0

    for capture_num, expected_power in failing_captures:
        test_subsection_ocr(capture_num, expected_power)

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
