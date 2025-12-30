"""
Simple test to download EasyOCR models
"""
import sys
import io

# Fix Windows console encoding issue
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import easyocr

print("Initializing EasyOCR (will download models on first run)...")
reader = easyocr.Reader(['en'], gpu=False)
print("EasyOCR initialized successfully!")

# Test on capture #5
test_image = "live_demo_debug/cropped/capture_005.png"
result = reader.readtext(test_image)

print(f"\nEasyOCR Results for {test_image}:")
for (bbox, text, conf) in result:
    print(f"  {text} (confidence: {conf:.2f})")
