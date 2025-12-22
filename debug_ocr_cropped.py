"""Debug OCR output with cropping"""
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()

screenshots = [
    'screenshots/powerplay_20251214_114812.png',
    'screenshots/powerplay_20251214_114817.png',
    'screenshots/powerplay_20251214_114823.png',
]

for idx, path in enumerate(screenshots, 1):
    print(f"\n{'=' * 80}")
    print(f"PARSE #{idx}: {path}")
    print('=' * 80)

    text = ocr.extract_text(path, preprocess_method='upscale')

    print("OCR TEXT:")
    print("-" * 80)
    print(text)
    print("-" * 80)
