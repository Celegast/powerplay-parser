"""
Test that description-based status detection works as a fallback
"""
from powerplay_ocr import PowerplayOCR

# Test cases where the status keyword is missing but description is present
test_cases = [
    {
        'text': """POWERPLAY INFORMATION
COL 359 SECTOR TEST-1
Exploited systems have a low control score and need a Fortified
or Stronghold system nearby to maintain control.""",
        'expected': 'EXPLOITED'
    },
    {
        'text': """POWERPLAY INFORMATION
COL 359 SECTOR TEST-2
Fortified systems have a high level of reinforcement and
maintain control over nearby Exploited systems.""",
        'expected': 'FORTIFIED'
    },
    {
        'text': """POWERPLAY INFORMATION
COL 359 SECTOR TEST-3
Stronghold systems have a very high level of reinforcement
and maintain control over nearby Exploited systems.""",
        'expected': 'STRONGHOLD'
    }
]

ocr = PowerplayOCR()

print("Testing description-based status detection fallback:\n")
all_passed = True

for i, test in enumerate(test_cases, 1):
    info = ocr.parse_powerplay_info(test['text'])
    status = info['system_status']
    expected = test['expected']

    if status == expected:
        print(f"Test {i}: PASSED - Detected '{status}' from description")
    else:
        print(f"Test {i}: FAILED - Expected '{expected}', got '{status}'")
        all_passed = False

print()
if all_passed:
    print("All description fallback tests passed!")
else:
    print("Some tests failed.")
