"""
Regenerate OCR text files with improved preprocessing
"""
from powerplay_ocr import PowerplayOCR
import os

def regenerate_ocr_for_captures():
    """Regenerate OCR for all captures using hybrid approach"""
    ocr = PowerplayOCR()

    print("Regenerating OCR text files with hybrid preprocessing...")
    print()

    for i in range(1, 13):
        capture_num = f"{i:03d}"
        cropped_path = f"live_demo_debug/cropped/capture_{capture_num}.png"

        if not os.path.exists(cropped_path):
            continue

        print(f"Processing capture #{i}...", end=' ')

        # Extract using hybrid approach (best results - 100% success target)
        # This uses upscale for numbers + threshold for system names + subsection fallback
        info = ocr.extract_text_hybrid(cropped_path, preprocess_method='upscale')

        # Also get the raw text for debugging
        text = ocr.extract_text(cropped_path, preprocess_method='upscale', crop_panel=False, use_subsections=False)

        # Save to OCR text file
        ocr_text_path = f"live_demo_debug/ocr_text/capture_{capture_num}.txt"
        with open(ocr_text_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"CAPTURE #{i}\n")
            f.write("=" * 80 + "\n\n")
            f.write("RAW OCR TEXT:\n")
            f.write("-" * 80 + "\n")
            f.write(text)
            f.write("\n" + "-" * 80 + "\n\n")
            f.write("PARSED DATA:\n")
            f.write(f"  System Name: '{info['system_name']}'\n")
            f.write(f"  Controlling Power: '{info['controlling_power']}'\n")
            f.write(f"  Opposing Power: '{info['opposing_power']}'\n")
            f.write(f"  System Status: '{info['system_status']}'\n")
            f.write(f"  Undermining Points: {info['undermining_points']}\n")
            f.write(f"  Reinforcing Points: {info['reinforcing_points']}\n")
            f.write(f"  Distance: {info['distance_ly']} LY\n")

        power = info['controlling_power'] or info['opposing_power'] or '(none)'
        print(f"Power: {power}, Points: {info['undermining_points']}/{info['reinforcing_points']}")

    print("\nDone!")

if __name__ == "__main__":
    regenerate_ocr_for_captures()
