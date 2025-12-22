"""Test without cropping to see full OCR"""
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()

# Test Parse #2 without cropping
text = ocr.extract_text('screenshots/powerplay_20251214_114817.png', preprocess_method='upscale')

print("PARSE #2 - WITH CROPPING (current):")
print("=" * 80)
lines = text.strip().split('\n')
for i, line in enumerate(lines):
    print(f"{i:3d}: {line}")

print("\n\n")

# Now without cropping
image = ocr.preprocess_image('screenshots/powerplay_20251214_114817.png', method='upscale', crop_panel=False)
import pytesseract
custom_config = r'--oem 1 --psm 4'
text_nocrop = pytesseract.image_to_string(image, config=custom_config)

print("PARSE #2 - WITHOUT CROPPING:")
print("=" * 80)
lines = text_nocrop.strip().split('\n')
for i, line in enumerate(lines):
    if 'POWERPLAY' in line.upper() or 'FORTIFIED' in line.upper() or 'COL 359 SECTOR EK-L' in line.upper():
        print(f"{i:3d}: {line}")
