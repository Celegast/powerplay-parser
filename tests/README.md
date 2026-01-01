# Test and Debug Scripts

This folder contains various test and debug scripts used during development.

## Test Scripts

These scripts test specific functionality:

- `test_all_screenshots.py` - Test OCR on all screenshots in a directory
- `test_auto_detect.py` - Test automatic detection features
- `test_competitive.py` - Test competitive state parsing
- `test_complete_system.py` - Test complete system parsing
- `test_description_fallback.py` - Test description fallback logic
- `test_easyocr_simple.py` - Test EasyOCR implementation
- `test_excel_format.py` - Test Excel output formatting
- `test_hybrid_ocr.py` - Test hybrid OCR approach
- `test_initial_cp.py` - Test initial control points detection
- `test_nocrop.py` - Test OCR without cropping
- `test_ocr_improvements.py` - Test OCR improvements
- `test_parsing.py` - Test parsing logic
- `test_rank_debug.py` - Test rank detection debugging
- `test_subsection_parser.py` - Test subsection parsing
- `test_subsections.py` - Test subsection cropping

## Debug Scripts

These scripts were used for debugging specific issues:

- `debug_ocr_cropped.py` - Debug OCR with cropped images
- `debug_parse23.py` - Debug specific parsing case
- `debug_power_section.py` - Debug power section parsing
- `debug_status_match.py` - Debug status matching

## Utility Scripts

- `example_usage.py` - Example usage of the OCR library
- `regenerate_ocr.py` - Regenerate OCR output for existing screenshots

## Usage

These scripts are not required for normal operation of the PowerplayParser.
They are kept for reference and potential future debugging needs.

To use any test script:
```bash
cd tests
python test_script_name.py
```
