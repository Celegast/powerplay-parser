"""Debug Parse #2 and #3 specifically"""
from powerplay_ocr import PowerplayOCR
import re

ocr = PowerplayOCR()

for idx, path in [(2, 'screenshots/powerplay_20251214_114817.png'),
                  (3, 'screenshots/powerplay_20251214_114823.png')]:
    print(f"\n{'=' * 80}")
    print(f"PARSE #{idx}")
    print('=' * 80)

    text = ocr.extract_text(path)
    lines = text.strip().split('\n')

    print("\nLooking for POWERPLAY INFORMATION and following lines:")
    for i, line in enumerate(lines):
        if 'POWERPLAY INFORMATION' in line.upper():
            print(f"\nLine {i}: {repr(line)}")
            for j in range(1, 5):
                if i + j < len(lines):
                    print(f"Line {i+j}: {repr(lines[i+j])}")
            break

    # Check for status lines
    print("\n\nLooking for status keywords:")
    status_keywords = ['STRONGHOLD', 'FORTIFIED', 'EXPLOITED', 'UNOCCUPIED']
    for i, line in enumerate(lines):
        for status in status_keywords:
            if status in line.upper() and 'PENALTY' not in line.upper() and 'POINTS' not in line.upper():
                cleaned = re.sub(r'^[|VvYyWwPp=\+\-_*.\s]+', '', line.strip()).strip()
                cleaned = re.sub(r'[\s|]+$', '', cleaned)
                print(f"Line {i}: {repr(line.strip())}")
                print(f"  Cleaned: {repr(cleaned)}")
                print(f"  Match: {cleaned.upper() == status}")
                break
