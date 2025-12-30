"""
Debug script to test rank OCR
"""
from powerplay_ocr import PowerplayOCR
import pytesseract

ocr = PowerplayOCR()

# Test the rank subsection
subsections = ocr.crop_powerplay_subsections_competitive('screenshots/Screenshot 2025-12-30 132535.png')

rank_img = subsections['power_your_rank']

# Save for inspection
rank_img.save('test_rank.png')

# Try different preprocessing methods
print("Testing rank OCR with different methods:")
print("=" * 60)

import tempfile
import os

with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
    tmp_path = tmp.name
    rank_img.save(tmp_path)

for method in ['none', 'upscale', 'threshold', 'enhanced']:
    print(f"\nMethod: {method}")
    print("-" * 60)

    processed = ocr.preprocess_image(tmp_path, method=method, crop_panel=False)
    processed.save(f'test_rank_{method}.png')

    text = pytesseract.image_to_string(
        processed,
        config='--oem 3 --psm 7 --dpi 300'
    ).strip()

    print(f"Raw text: '{text}'")
    print(f"Upper: '{text.upper()}'")

    # Test the regex
    import re
    rank_match = re.search(r'(\d+)(ST|ND|RD|TH)', text.upper())
    if rank_match:
        print(f"Rank match: {rank_match.group(1)}{rank_match.group(2).lower()}")
    else:
        print("No rank match")

try:
    os.unlink(tmp_path)
except:
    pass
