"""
Debug script to test status matching
"""
from powerplay_ocr import PowerplayOCR

# Test text from capture #3
test_text = """POWERPLAY INFORMATION (i)
COL 359 SECTOR BE-N B9-0 LAST UPDATED: =.
DISTANCE: 18.35LY 44 MINUTES AGO
VEXPLOTED [) |

Exploited systems have a low control score and need a Fortified |

| or Stronghold system nearby to maintain control. ©

TU OF WAR AA"""

ocr = PowerplayOCR()
info = ocr.parse_powerplay_info(test_text)

print("Parsed info:")
print(f"  System: {info['system_name']}")
print(f"  Power: {info['controlling_power']}")
print(f"  Status: '{info['system_status']}'")
print()

# Manual test of the fuzzy matching logic
import re
from difflib import SequenceMatcher

lines = test_text.split('\n')
status_keywords = ['STRONGHOLD', 'FORTIFIED', 'EXPLOITED', 'UNOCCUPIED']

print("Manual line-by-line check:")
for i, line in enumerate(lines):
    line_stripped = line.strip()
    line_upper = line_stripped.upper()

    # Skip if we've reached TUG OF WAR
    if any(x in line_upper for x in ['TUG OF WAR', 'OPPOSING POWERS']):
        print(f"Line {i}: Reached TUG OF WAR section, stopping")
        break

    for status in status_keywords:
        fuzzy_match = False
        if status in line_upper:
            fuzzy_match = True
        else:
            cleaned_line = re.sub(r'[^A-Z\s]', '', line_upper)
            for word in cleaned_line.split():
                if len(word) >= len(status) - 2 and len(word) <= len(status) + 2:
                    matches = sum(1 for a, b in zip(word, status) if a == b)
                    if matches >= len(status) - 2:
                        fuzzy_match = True
                        break

        if fuzzy_match and not any(x in line_upper for x in ['PENALTY', 'POINTS']):
            cleaned_line = re.sub(r'[^A-Z\s]', '', line_upper)
            has_lower = any(c.islower() for c in line_stripped)

            print(f"Line {i}: [{line_stripped}]")
            print(f"  Fuzzy match for '{status}': YES")
            print(f"  Has lowercase: {has_lower}")

            if has_lower:
                print(f"  SKIPPED (has lowercase)")
                continue

            found_status = False
            for word in cleaned_line.split():
                if word == status:
                    found_status = True
                    break
                if len(word) >= len(status) - 2 and len(word) <= len(status) + 2:
                    similarity = SequenceMatcher(None, word, status).ratio()
                    if similarity > 0.75:
                        print(f"  Word '{word}' matches '{status}' (similarity: {similarity:.2f})")
                        found_status = True
                        break

            if found_status:
                print(f"  STATUS DETECTED: {status}")
                break
