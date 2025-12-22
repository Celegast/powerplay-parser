"""
Debug power section OCR
"""
from powerplay_ocr import PowerplayOCR
import pytesseract

def debug_power_section(capture_num):
    """Debug power section OCR"""
    ocr = PowerplayOCR()

    cropped_path = f"live_demo_debug/cropped/capture_{capture_num:03d}.png"

    print(f"\n{'='*80}")
    print(f"CAPTURE #{capture_num}")
    print(f"{'='*80}")

    # Get power section
    subsections = ocr.crop_powerplay_subsections(cropped_path)
    power_section = subsections['power_section']

    # Save it for inspection
    power_section.save(f"debug_power_{capture_num:03d}.png")
    print(f"Saved power section to: debug_power_{capture_num:03d}.png")

    # Try different preprocessing methods
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        power_section.save(tmp.name)
        temp_path = tmp.name

    methods = ['upscale', 'threshold', 'clahe']

    for method in methods:
        processed = ocr.preprocess_image(temp_path, method=method, crop_panel=False)

        # Try different PSM modes
        for psm in [3, 4, 6, 11, 12]:
            custom_config = f'--oem 1 --psm {psm} --dpi 300'
            text = pytesseract.image_to_string(processed, config=custom_config)

            info = ocr.parse_powerplay_info(text)
            power = info['controlling_power'] or info['opposing_power'] or '(none)'

            if power != '(none)':
                print(f"\n{method} + PSM {psm}:")
                print(f"  Power: {power}")
                print(f"  Raw text: {repr(text[:200])}")

    import os
    os.remove(temp_path)

if __name__ == "__main__":
    debug_power_section(1)
    debug_power_section(8)
