"""
Test hybrid OCR approach: regular OCR + targeted subsection OCR for power names
"""
from powerplay_ocr import PowerplayOCR
import pytesseract
import os

def extract_power_names_from_subsection(ocr, image_path):
    """Extract power names using just the power_section subsection"""
    subsections = ocr.crop_powerplay_subsections(image_path)
    power_section = subsections['power_section']

    # Save to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        power_section.save(tmp.name)
        temp_path = tmp.name

    # Preprocess
    processed = ocr.preprocess_image(temp_path, method='upscale', crop_panel=False)

    # OCR with PSM 6
    custom_config = r'--oem 1 --psm 6 --dpi 300'
    text = pytesseract.image_to_string(processed, config=custom_config)

    # Clean up
    try:
        os.remove(temp_path)
    except:
        pass

    return text

def test_hybrid_ocr(capture_num, expected_power):
    """Test hybrid OCR approach"""
    ocr = PowerplayOCR()

    cropped_path = f"live_demo_debug/cropped/capture_{capture_num:03d}.png"

    if not os.path.exists(cropped_path):
        print(f"File not found: {cropped_path}")
        return

    print(f"\n{'='*80}")
    print(f"CAPTURE #{capture_num} - Expected Power: {expected_power}")
    print(f"{'='*80}")

    # Regular OCR for all data
    text_regular = ocr.extract_text(cropped_path, preprocess_method='upscale', crop_panel=False)
    info_regular = ocr.parse_powerplay_info(text_regular)

    # Targeted subsection OCR for power names
    power_text = extract_power_names_from_subsection(ocr, cropped_path)
    info_power = ocr.parse_powerplay_info(power_text)

    # Hybrid: Use power names from subsection if regular OCR failed
    if not (info_regular['controlling_power'] or info_regular['opposing_power']):
        if info_power['controlling_power'] or info_power['opposing_power']:
            print("\n[USING SUBSECTION FOR POWER NAMES]")
            info_regular['controlling_power'] = info_power['controlling_power']
            info_regular['opposing_power'] = info_power['opposing_power']

    power = info_regular['controlling_power'] or info_regular['opposing_power'] or '(none)'
    match = "[OK]" if expected_power.lower() in power.lower() else "[FAIL]"

    print(f"  Power: {power} {match}")
    print(f"  System: {info_regular['system_name']}")
    print(f"  Status: {info_regular['system_status']}")
    print(f"  Points: {info_regular['undermining_points']} / {info_regular['reinforcing_points']}")

    return match == "[OK]"

def main():
    """Test hybrid approach"""

    failing_captures = [
        (1, "Pranav Antal"),
        (6, "Nakato Kaine"),
        (7, "Li Yong-Rui"),
        (8, "Edmund Mahon"),
        (12, "Yuri Grom")
    ]

    print("="*80)
    print("TESTING HYBRID OCR APPROACH")
    print("="*80)
    print("\nRegular OCR + Targeted subsection OCR for power names...")

    passed = 0
    for capture_num, expected_power in failing_captures:
        if test_hybrid_ocr(capture_num, expected_power):
            passed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed}/{len(failing_captures)} passed")
    print("="*80)

if __name__ == "__main__":
    main()
