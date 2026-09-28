"""
Quick OCR check: screenshot the open Powerplay panel and print what the parser reads.

    python tests/snap_ocr.py            # 5 s to switch to the game, then screenshot
    python tests/snap_ocr.py 10         # custom delay
    python tests/snap_ocr.py shot.png   # re-run OCR on a saved screenshot

Screenshot and subsection crops are kept in screenshots/ for inspection.
"""
import os
import sys
import time
from pprint import pprint

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()
arg = sys.argv[1] if len(sys.argv) > 1 else '5'
if arg.isdigit():
    print(f"Switch to Elite Dangerous - screenshot in {arg}s ...")
    time.sleep(int(arg))
    path = ocr.take_screenshot()
else:
    path = arg
print(f"Image: {path}\n")

t = time.time()
info = ocr.extract_powerplay_auto(path)
secs = time.time() - t
pprint(info, sort_dicts=False)
print(f"\nExcel line: {ocr.format_for_excel(info)}")
print(f"OCR took {secs:.1f}s")

competitive = info.get('system_status', '').upper() in ('CONTESTED', 'EXPANSION', 'UNOCCUPIED')
crop = ocr.crop_powerplay_subsections_competitive if competitive else ocr.crop_powerplay_subsections
stem = os.path.splitext(path)[0]
for name, img in crop(path).items():
    img.save(f"{stem}_{name}.png")
print(f"Subsection crops saved as {stem}_*.png")
