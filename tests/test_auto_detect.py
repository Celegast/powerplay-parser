"""
Test auto-detection of state types (standard vs competitive)
"""
from powerplay_ocr import PowerplayOCR
import os

def main():
    print("=" * 80)
    print("TESTING AUTO-DETECTION (MIXED STANDARD AND COMPETITIVE STATES)")
    print("=" * 80)

    ocr = PowerplayOCR()

    # Mix of standard and competitive states
    test_screenshots = [
        # Standard states
        ('screenshots/powerplay_20251221_122751.png', 'STANDARD'),
        ('screenshots/powerplay_20251221_122824.png', 'STANDARD'),
        # Competitive states
        ('screenshots/Screenshot 2025-12-30 132535.png', 'COMPETITIVE (CONTESTED)'),
        ('screenshots/Screenshot 2025-12-30 132552.png', 'COMPETITIVE (UNOCCUPIED)'),
    ]

    results = []

    for screenshot_path, expected_type in test_screenshots:
        if not os.path.exists(screenshot_path):
            print(f"\nSkipping: {screenshot_path} (not found)")
            continue

        print(f"\n{'=' * 80}")
        print(f"Testing: {screenshot_path}")
        print(f"Expected: {expected_type}")
        print("=" * 80)

        try:
            # Use auto-detection
            info = ocr.extract_powerplay_auto(screenshot_path)

            # Display results
            print(f"\n  System Name: {info['system_name']}")
            print(f"  System Status: {info['system_status']}")
            print(f"  Controlling Power: {info['controlling_power']}")

            # Check if this is competitive state (has 'powers' list)
            if 'powers' in info and info['powers']:
                print(f"\n  STATE TYPE: COMPETITIVE")
                print(f"  Powers competing:")
                for power_data in info['powers']:
                    rank_str = f"{power_data['rank']}" if power_data['rank'] else "?"
                    print(f"    {rank_str}. {power_data['name']}: {power_data['score']:,}")
                if info.get('your_power'):
                    print(f"  Your Power: {info['your_power']} (Rank: {info['your_rank']})")
            else:
                print(f"\n  STATE TYPE: STANDARD")
                print(f"  Undermining: {info['undermining_points']:,}")
                print(f"  Reinforcing: {info['reinforcing_points']:,}")

            # Validation
            is_valid = ocr.is_valid_powerplay_data(info)
            print(f"\n  Valid: {'[OK] YES' if is_valid else '[X] NO'}")

            results.append({
                'path': screenshot_path,
                'expected': expected_type,
                'system': info['system_name'],
                'status': info['system_status'],
                'valid': is_valid
            })

        except Exception as e:
            print(f"\n  ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'path': screenshot_path,
                'expected': expected_type,
                'error': str(e)
            })

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for result in results:
        if 'error' in result:
            print(f"[X] {result['expected']}: ERROR - {result['error']}")
        else:
            status = '[OK]' if result['valid'] else '[X]'
            print(f"{status} {result['expected']}: {result['system']} ({result['status']})")

    print("\n" + "=" * 80)
    print(f"Total: {len(results)} tests")
    valid_count = sum(1 for r in results if r.get('valid', False))
    print(f"Valid: {valid_count}/{len(results)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
