#!/usr/bin/env python3
"""Test cycle detection logic"""

from datetime import datetime, timezone, timedelta
import sys
sys.path.insert(0, '.')
from auto_capture import get_cycle_tick_time

# Test cases
test_cases = [
    # (description, reference_time, expected_tick_date)
    # Note: Jan 1, 2026 = Thursday, Jan 2 = Friday, Jan 5 = Monday
    ("Monday Jan 5", datetime(2026, 1, 5, 15, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)),  # Last Thursday Jan 1
    ("Sunday Jan 4", datetime(2026, 1, 4, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)),  # Last Thursday Jan 1
    ("Thursday Jan 8 at 8am (after tick)", datetime(2026, 1, 8, 8, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 8, 7, 0, 0, tzinfo=timezone.utc)),  # Same day (this Thursday)
    ("Thursday Jan 8 at 6am (before tick)", datetime(2026, 1, 8, 6, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)),  # Last Thursday Jan 1
    ("Friday Jan 9", datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 8, 7, 0, 0, tzinfo=timezone.utc)),  # Previous Thursday Jan 8
    ("Tuesday Jan 6", datetime(2026, 1, 6, 12, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)),  # Last Thursday Jan 1
    ("Thursday Jan 1 at 7am exactly", datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc), datetime(2026, 1, 1, 7, 0, 0, tzinfo=timezone.utc)),  # This tick
]

print("Testing cycle detection logic:")
print("=" * 80)

all_passed = True
for desc, ref_time, expected in test_cases:
    result = get_cycle_tick_time(ref_time)
    passed = result == expected
    all_passed = all_passed and passed

    status = "PASS" if passed else "FAIL"
    print(f"\n{status}: {desc}")
    print(f"  Reference time: {ref_time.strftime('%A, %Y-%m-%d %H:%M UTC')}")
    print(f"  Expected tick:  {expected.strftime('%A, %Y-%m-%d %H:%M UTC')}")
    print(f"  Actual tick:    {result.strftime('%A, %Y-%m-%d %H:%M UTC')}")
    if not passed:
        print(f"  ERROR: Mismatch!")

print("\n" + "=" * 80)
if all_passed:
    print("All tests PASSED!")
else:
    print("Some tests FAILED!")
