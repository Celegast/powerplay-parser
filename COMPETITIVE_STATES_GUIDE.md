# Competitive States Support (EXPANSION/CONTESTED/UNOCCUPIED)

## Overview

The PowerplayParser now supports parsing EXPANSION, CONTESTED, and UNOCCUPIED system states in addition to the standard EXPLOITED, FORTIFIED, and STRONGHOLD states.

## What's Different

### Panel Size
- **Standard states** (EXPLOITED, FORTIFIED, STRONGHOLD): 740×646 pixels
- **Competitive states** (EXPANSION, CONTESTED, UNOCCUPIED): 742×840 pixels (taller to accommodate multiple powers)

### Data Structure
Competitive states show:
- System name
- System status (CONTESTED, EXPANSION, or UNOCCUPIED)
- Multiple competing powers with their control scores
- Your power's name and rank (if participating)

Unlike standard states, competitive states don't have "undermining" and "reinforcing" points - instead they show multiple powers competing with control scores.

## Usage

### Manual Testing

Use the test script to verify parsing:

```bash
python test_competitive.py
```

This will process the example screenshots and save debug subsections.

### API Usage

```python
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()

# Extract competitive state data
info = ocr.extract_powerplay_competitive('screenshots/Screenshot 2025-12-30 132535.png')

print(f"System: {info['system_name']}")
print(f"Status: {info['system_status']}")
print(f"Controlling Power: {info['controlling_power']}")
print(f"Opposing Power: {info['opposing_power']}")

# Powers list contains all competing powers
for power_info in info['powers']:
    print(f"  {power_info['rank']}. {power_info['name']}: {power_info['score']:,}")

# Your participation
print(f"Your Power: {info['your_power']}")
print(f"Your Rank: {info['your_rank']}")
```

### Return Data Structure

```python
{
    'system_name': 'COL 359 SECTOR FK-L B10-1',
    'system_status': 'CONTESTED',
    'controlling_power': 'Denton Patreus',      # 1st ranked power
    'opposing_power': 'Nakato Kaine',           # 2nd ranked power
    'your_power': 'Pranav Antal',
    'your_rank': '5th',
    'powers': [
        {'name': 'Denton Patreus', 'score': 174028, 'rank': 1},
        {'name': 'Nakato Kaine', 'score': 110125, 'rank': 2},
        {'name': 'Pranav Antal', 'score': 32556, 'rank': None}
    ],
    'undermining_points': -1,   # Not applicable
    'reinforcing_points': -1    # Not applicable
}
```

## System States

### CONTESTED
Systems with multiple Powers actively competing to acquire them.

### EXPANSION
Systems being expanded into by one or more Powers.

### UNOCCUPIED
Systems that have not been expanded into by any Power (but may have expansion attempts).

## Implementation Details

### Subsection Coordinates

For the extended 742×840 panel:

- System name: (14, 56) - (552, 96)
- System status: (14, 212) - (734, 272) [wider than standard]
- 1st power name: (106, 330) - (412, 360)
- 1st power score: (416, 330) - (738, 360)
- 2nd power name: (106, 464) - (412, 494)
- 2nd power score: (416, 464) - (738, 494)
- Your power name: (106, 692) - (412, 722)
- Your power score: (416, 692) - (738, 722)
- Your power rank: (108, 646) - (170, 674)

### Methods

- `crop_powerplay_panel(image_path, extended=True)` - Crop the 742×840 panel
- `crop_powerplay_subsections_competitive(image_path)` - Extract subsections
- `extract_powerplay_competitive(image_path)` - Parse all competitive data

## Known OCR Challenges

### Rank Detection
The rank text (e.g., "5th") is very small and OCR sometimes misreads:
- "5th" → "Sth" or "oth"

The implementation includes fallback patterns to handle these common errors.

## Test Results

### Screenshot 2025-12-30 132535.png (CONTESTED)
✓ System Name: COL 359 SECTOR FK-L B10-1
✓ Status: CONTESTED
✓ Powers: Denton Patreus (174,028), Nakato Kaine (110,125), Pranav Antal (32,556)
✓ Your Power: Pranav Antal
✓ Your Rank: 5th

### Screenshot 2025-12-30 132552.png (UNOCCUPIED)
✓ System Name: COL 359 SECTOR FK-L B10-3
✓ Status: UNOCCUPIED
✓ Powers: Aisling Duval (106,622), Pranav Antal (15,626)
✓ No active participation (Your Power and Rank empty)

## Excel Output Format

The parser automatically formats both standard and competitive states for Excel output:

### Standard States (EXPLOITED, FORTIFIED, STRONGHOLD)
```
System Name              Power            State      Undermining  Reinforcement
COL 359 SECTOR QX-R C5-11  Pranav Antal   FORTIFIED  668          3348
```

### Competitive States (CONTESTED, EXPANSION, UNOCCUPIED)
```
System Name              Power              State          Undermining  Reinforcement
COL 359 SECTOR FK-L B10-1  Denton Patreus  Nakato Kaine   110125       174028
```

**Column Mapping for Competitive States:**
- **Power** = 1st ranked power name (leading power)
- **State** = 2nd ranked power name (opposing power)
- **Undermining** = 2nd power's control points
- **Reinforcement** = 1st power's control points

This allows you to easily compare competitive states with standard states in the same spreadsheet.

## Auto-Detection

Use `extract_powerplay_auto()` to automatically detect and parse both state types:

```python
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()
info = ocr.extract_powerplay_auto(screenshot_path)  # Auto-detects state type
excel_line = ocr.format_for_excel(info)  # Formats appropriately for Excel
```

The auto-detection:
1. Peeks at the status description text
2. Checks for competitive keywords (CONTESTED, EXPANSION, UNOCCUPIED)
3. Routes to the appropriate parser
4. Validates the results
5. Formats for Excel output
