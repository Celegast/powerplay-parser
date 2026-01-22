"""
Summarize powerplay data by power
Creates a summary table with total reinforcement/undermining points and system counts
Calculates decay based on system state and initial CP using known formulas
"""

import sys
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone


# Cycle 64 started on Thursday 2026-01-15 at 7:00 UTC
# So cycle 1 started 63 weeks before that
CYCLE_1_START = datetime(2024, 10, 31, 7, 0, 0, tzinfo=timezone.utc)


def get_cycle_number():
    """Calculate the current powerplay cycle number."""
    now = datetime.now(timezone.utc)
    weeks_since_cycle_1 = (now - CYCLE_1_START).days // 7
    return 1 + weeks_since_cycle_1


def calculate_decay(state, initial_cp):
    """
    Calculate decay based on system state and initial CP.
    Formulas:
    - Stronghold: decay = (initial_cp - 1250000) * (5/24), only if initial_cp >= 1250000
    - Fortified: decay = (initial_cp - 512500) * (4/24), only if initial_cp >= 512500
    - Exploited: decay = (initial_cp - 87500) * (2/24), only if initial_cp >= 87500
    Returns 0 if below threshold or unknown state.
    """
    state_upper = state.upper()

    if 'STRONGHOLD' in state_upper:
        if initial_cp >= 1250000:
            return int((initial_cp - 1250000) * (5 / 24))
    elif 'FORTIFIED' in state_upper:
        if initial_cp >= 512500:
            return int((initial_cp - 512500) * (4 / 24))
    elif 'EXPLOITED' in state_upper:
        if initial_cp >= 87500:
            return int((initial_cp - 87500) * (2 / 24))

    return 0


def parse_powerplay_file(filepath):
    """Parse the powerplay_auto_capture.txt file, calculating decay from initial CP"""
    powers = defaultdict(lambda: {
        'undermining': 0,
        'reinforcement': 0,
        'stronghold': 0,
        'fortified': 0,
        'exploited': 0,
        'decay': 0
    })

    data_timestamp = None  # Store as timestamp string

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # First line might be data age in one of two formats:
        # 1. "X minutes ago" (old format)
        # 2. "YYYY-MM-DD HH:MM UTC" (new format)
        if i == 0:
            # Try old format: "X minutes ago"
            match = re.search(r'(\d+)\s*minutes?\s*ago', line.lower())
            if match:
                data_age_minutes = int(match.group(1))
                # Convert to timestamp
                data_time = datetime.now(timezone.utc) - timedelta(minutes=data_age_minutes)
                data_timestamp = data_time.strftime("%Y-%m-%d %H:%M UTC")
                continue

            # Try new format: "YYYY-MM-DD HH:MM UTC"
            match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*UTC', line)
            if match:
                data_timestamp = line.strip()
                continue

        # Skip header line
        if line.startswith('System Name'):
            continue

        # Parse data line: System Name\tPower\tState\t\tUndermining\tReinforcement\tInitial CP
        parts = line.split('\t')
        if len(parts) < 6:
            continue

        # Handle the double-tab between State and Undermining
        # Parts: [System Name, Power, State, '', Undermining, Reinforcement, Initial CP]
        system_name = parts[0].strip()
        power = parts[1].strip()
        state = parts[2].strip().upper()

        # Find undermining, reinforcement, and initial_cp values (skip empty parts)
        numeric_parts = [p for p in parts[3:] if p.strip()]
        if len(numeric_parts) >= 3:
            try:
                undermining = int(numeric_parts[0].replace(',', ''))
                reinforcement = int(numeric_parts[1].replace(',', ''))
                initial_cp = int(numeric_parts[2].replace(',', ''))
            except ValueError:
                continue
        else:
            continue

        if not power:
            continue

        # Calculate decay from state and initial CP
        decay = calculate_decay(state, initial_cp)
        undermining_adjusted = max(0, undermining - decay)

        # Accumulate totals
        powers[power]['undermining'] += undermining_adjusted
        powers[power]['reinforcement'] += reinforcement
        powers[power]['decay'] += decay

        # Count system states
        if 'STRONGHOLD' in state:
            powers[power]['stronghold'] += 1
        elif 'FORTIFIED' in state:
            powers[power]['fortified'] += 1
        elif 'EXPLOITED' in state:
            powers[power]['exploited'] += 1

    return powers, data_timestamp


def format_number(n):
    """Format number with thousand separators"""
    return f"{n:,}"


def format_kilo(n):
    """Format number in kilo (k) format, rounded to nearest 1000"""
    rounded = round(n / 1000) * 1000
    return f"{rounded // 1000}k"


def print_summary(powers, data_timestamp=None):
    """Print summary table"""
    # Print info line: Cycle X - Enclave - timestamp
    if data_timestamp is not None:
        cycle_num = get_cycle_number()
        print(f"Cycle {cycle_num} - Enclave - {data_timestamp}")
        print()

    # Header: Power, SH/FF/EX, RF, UM (net), UM%, ~Decay
    print(f"{'Power':<25} {'SH/FF/EX':>10} {'RF':>10} {'(net) UM':>10} {'UM%':>7} {'~Decay':>10}")
    print("-" * 78)

    # Sort by systems: Stronghold (desc), Fortified (desc), Exploited (desc)
    sorted_powers = sorted(powers.keys(), key=lambda p: (
        -powers[p]['stronghold'],
        -powers[p]['fortified'],
        -powers[p]['exploited']
    ))

    for power in sorted_powers:
        data = powers[power]
        systems = f"{data['stronghold']}/{data['fortified']}/{data['exploited']}"
        um_pct = (data['undermining'] / data['reinforcement'] * 100) if data['reinforcement'] > 0 else 0
        print(f"{power:<25} {systems:>10} {format_kilo(data['reinforcement']):>10} {format_kilo(data['undermining']):>10} {um_pct:>6.1f}% {format_kilo(data['decay']):>10}")

    # Totals
    print("-" * 78)
    total_und = sum(p['undermining'] for p in powers.values())
    total_rei = sum(p['reinforcement'] for p in powers.values())
    total_dec = sum(p['decay'] for p in powers.values())
    total_s = sum(p['stronghold'] for p in powers.values())
    total_f = sum(p['fortified'] for p in powers.values())
    total_e = sum(p['exploited'] for p in powers.values())
    systems_total = f"{total_s}/{total_f}/{total_e}"
    total_um_pct = (total_und / total_rei * 100) if total_rei > 0 else 0
    print(f"{'TOTAL':<25} {systems_total:>10} {format_kilo(total_rei):>10} {format_kilo(total_und):>10} {total_um_pct:>6.1f}% {format_kilo(total_dec):>10}")


def main():
    # Default file path
    filepath = 'powerplay_auto_capture.txt'

    # Allow custom file path as argument
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    try:
        powers, data_age = parse_powerplay_file(filepath)

        if not powers:
            print(f"No data found in {filepath}")
            return 1

        print_summary(powers, data_age)
        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
