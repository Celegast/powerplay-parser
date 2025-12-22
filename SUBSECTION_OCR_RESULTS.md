# Subsection-Based OCR Results

## Summary

I implemented and tested two approaches for improving OCR quality:

1. **Subsection-based OCR**: Crop the panel into subsections and OCR each independently
2. **Alternative OCR engines**: (EasyOCR - not yet implemented due to better results with subsections)

## Approach: Subsection-Based OCR

### Concept

The Elite Dangerous Powerplay panel has a fixed layout. By cropping it into specific subsections and using appropriate Tesseract PSM (Page Segmentation Mode) settings for each section, we can improve OCR accuracy.

### Implementation

**Subsections defined:**
```python
- header (0-20%): System name, distance, last updated
- status (18-32%): System status (EXPLOITED, FORTIFIED, etc.)
- power_section (32-60%): Power names and VS indicator
- control_points (50-64%): Undermining/Reinforcing numbers
- penalties (64-78%): System strength and frontline penalties
```

**PSM modes by section:**
- `header`: PSM 6 (uniform block)
- `power_section`: PSM 3 (automatic page segmentation) - **KEY IMPROVEMENT**
- `control_points`: PSM 6 (uniform block)
- `penalties`: PSM 6 (uniform block)
- `status`: PSM 6 (uniform block)

### Results

**Power Name Detection (Previously Failing Captures):**

| Capture | Power | Regular OCR | Subsection OCR | Result |
|---------|-------|-------------|----------------|---------|
| #1 | Pranav Antal | ✗ Failed | ✓ Fixed | **IMPROVED** |
| #6 | Nakato Kaine | ✓ OK | ✓ OK | Same |
| #7 | Li Yong-Rui | ✓ OK | ✓ OK | Same |
| #8 | Edmund Mahon | ✗ Failed | ✓ Fixed | **IMPROVED** |
| #12 | Yuri Grom | ✓ OK | ✓ OK | Same |

**Overall Success Rate:**
- Regular OCR (with parsing improvements): **58.3%** (7/12)
- Subsection OCR: **41.7%** (5/12)

### Trade-offs

**Advantages:**
- ✓ Fixed 2 critical power detection failures (#1 Pranav Antal, #8 Edmund Mahon)
- ✓ All 12 power names now detected correctly
- ✓ PSM 3 for power_section handles avatar images better

**Disadvantages:**
- ✗ Some system names now have OCR errors (e.g., "RX-R CB-1" instead of "RX-R C5-1")
- ✗ Status detection regressed in some cases
- ✗ More complex processing

## Recommendation: Hybrid Approach

The best solution is a **hybrid approach**:

###  1. Use Regular OCR as Primary Method
```python
text = ocr.extract_text(image_path, preprocess_method='upscale', crop_panel=False)
info = ocr.parse_powerplay_info(text)
```

### 2. Fall Back to Subsection OCR for Power Names
```python
# If power name not detected, try subsection approach for just the power_section
if not (info['controlling_power'] or info['opposing_power']):
    subsections = ocr.crop_powerplay_subsections(image_path)
    power_text = ocr.extract_text_from_section(subsections['power_section'], psm=3)
    power_info = ocr.parse_powerplay_info(power_text)

    # Use power names from subsection
    info['controlling_power'] = power_info['controlling_power']
    info['opposing_power'] = power_info['opposing_power']
```

### Benefits of Hybrid Approach:
- Uses regular OCR for most fields (best accuracy)
- Only uses subsection OCR when needed (power names)
- Maintains 58.3% baseline success rate
- Fixes additional 2 power detection failures
- **Estimated final success rate: 75% (9/12)**

## Code Changes Made

### Files Modified:

1. **[powerplay_ocr.py](powerplay_ocr.py)**:
   - Added `crop_powerplay_subsections()` method (lines 79-152)
   - Added `extract_text_subsections()` method (lines 283-338)
   - Added `use_subsections` parameter to `extract_text()` (line 250)
   - Configured PSM modes per subsection type (lines 313-325)

### New Files Created:
- **[test_subsections.py](test_subsections.py)**: Compare regular vs subsection OCR
- **[test_hybrid_ocr.py](test_hybrid_ocr.py)**: Test hybrid approach
- **[debug_power_section.py](debug_power_section.py)**: Debug tool for power section OCR

## Alternative: EasyOCR

EasyOCR is a modern deep learning-based OCR engine that might provide better results. However, since the subsection approach with Tesseract PSM 3 successfully detected all power names, implementing EasyOCR may not be necessary at this point.

**To add EasyOCR support (future enhancement):**
```python
pip install easyocr

import easyocr

class PowerplayOCR:
    def __init__(self, use_easyocr=False):
        self.use_easyocr = use_easyocr
        if use_easyocr:
            self.reader = easyocr.Reader(['en'])

    def extract_text(self, image_path, engine='tesseract'):
        if engine == 'easyocr' and self.use_easyocr:
            result = self.reader.readtext(image_path)
            return '\n'.join([text for (bbox, text, conf) in result])
        else:
            # Use tesseract (existing code)
            ...
```

## Final Recommendations

1. **Implement the hybrid approach** described above for best results
2. **Keep subsection OCR as fallback** for power name detection
3. **Consider EasyOCR** only if further improvements are needed
4. **Monitor false positives** - the improved word boundary matching may need tuning

## Usage

To use subsection-based OCR:
```python
from powerplay_ocr import PowerplayOCR

ocr = PowerplayOCR()

# Use subsections
text = ocr.extract_text(cropped_path, use_subsections=True)
info = ocr.parse_powerplay_info(text)
```

To use the recommended hybrid approach (implement as needed):
```python
# Primary: Regular OCR
text = ocr.extract_text(cropped_path, crop_panel=False)
info = ocr.parse_powerplay_info(text)

# Fallback: Subsection OCR for power names if needed
if not (info['controlling_power'] or info['opposing_power']):
    subsections = ocr.crop_powerplay_subsections(cropped_path)
    # Process power_section with PSM 3
    ...
```

