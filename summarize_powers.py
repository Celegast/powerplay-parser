"""
Summarize powerplay data by power
Creates a summary table with total reinforcement/undermining points and system counts
Calculates decay based on system state and initial CP using known formulas
"""

import sys
import re
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone


# Cycle 64 started on Thursday 2026-01-15 at 7:00 UTC
# So cycle 1 started 63 weeks before that
CYCLE_1_START = datetime(2024, 10, 31, 7, 0, 0, tzinfo=timezone.utc)


def get_cycle_number(reference_time=None):
    """Calculate the powerplay cycle number for a given time."""
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    weeks_since_cycle_1 = (reference_time - CYCLE_1_START).days // 7
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

    # Also store per-system data
    systems = []

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

        # Store per-system data
        systems.append({
            'name': system_name,
            'power': power,
            'state': state,
            'reinforcement': reinforcement,
            'undermining': undermining_adjusted,
            'decay': decay,
            'initial_cp': initial_cp
        })

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

    return powers, systems, data_timestamp


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
        # Parse timestamp to calculate correct cycle number
        # Format: "YYYY-MM-DD HH:MM UTC"
        match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', data_timestamp)
        if match:
            data_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            data_time = data_time.replace(tzinfo=timezone.utc)
            cycle_num = get_cycle_number(data_time)
        else:
            cycle_num = get_cycle_number()
        print(f"Cycle {cycle_num} - Enclave - {data_timestamp}")
        print()

    # Calculate column widths
    col_power = max(len("Power"), max(len(p) for p in powers.keys()))

    # Sort by systems: Stronghold (desc), Fortified (desc), Exploited (desc)
    sorted_powers = sorted(powers.keys(), key=lambda p: (
        -powers[p]['stronghold'],
        -powers[p]['fortified'],
        -powers[p]['exploited']
    ))

    # Calculate totals for systems column width
    total_s = sum(p['stronghold'] for p in powers.values())
    total_f = sum(p['fortified'] for p in powers.values())
    total_e = sum(p['exploited'] for p in powers.values())
    systems_total = f"{total_s}/{total_f}/{total_e}"

    col_sys = max(len("SH/FF/EX"), len(systems_total),
                  max(len(f"{powers[p]['stronghold']}/{powers[p]['fortified']}/{powers[p]['exploited']}") for p in powers.keys()))

    # Fixed widths for numeric columns
    col_rf = 6
    col_um = 8
    col_pct = 6
    col_dec = 7

    total_width = col_power + col_sys + col_rf + col_um + col_pct + col_dec + 5  # 5 spaces between columns

    # Header
    print(f"{'Power':<{col_power}} {'SH/FF/EX':>{col_sys}} {'RF':>{col_rf}} {'(net) UM':>{col_um}} {'UM%':>{col_pct}} {'~Decay':>{col_dec}}")
    print("-" * total_width)

    for power in sorted_powers:
        data = powers[power]
        systems = f"{data['stronghold']}/{data['fortified']}/{data['exploited']}"
        um_pct = (data['undermining'] / data['reinforcement'] * 100) if data['reinforcement'] > 0 else 0
        print(f"{power:<{col_power}} {systems:>{col_sys}} {format_kilo(data['reinforcement']):>{col_rf}} {format_kilo(data['undermining']):>{col_um}} {um_pct:>{col_pct - 1}.1f}% {format_kilo(data['decay']):>{col_dec}}")

    # Totals
    print("-" * total_width)
    total_und = sum(p['undermining'] for p in powers.values())
    total_rei = sum(p['reinforcement'] for p in powers.values())
    total_dec = sum(p['decay'] for p in powers.values())
    total_um_pct = (total_und / total_rei * 100) if total_rei > 0 else 0
    print(f"{'TOTAL':<{col_power}} {systems_total:>{col_sys}} {format_kilo(total_rei):>{col_rf}} {format_kilo(total_und):>{col_um}} {total_um_pct:>{col_pct - 1}.1f}% {format_kilo(total_dec):>{col_dec}}")


def print_power_details(systems, power_name="Pranav Antal"):
    """Print detailed system information for a specific power"""
    # Filter systems for this power
    power_systems = [s for s in systems if s['power'] == power_name]

    if not power_systems:
        print(f"\nNo systems found for {power_name}")
        return

    # Calculate column widths
    col_name = max(len("System"), max(len(s['name']) for s in power_systems)) + 1
    col_state = max(len("State"), max(len(s['state']) for s in power_systems))

    # Fixed widths for numeric columns
    col_rf = 6
    col_um = 8
    col_pct = 6
    col_dec = 7

    total_width = col_name + col_state + col_rf + col_um + col_pct + col_dec + 5

    print(f"\n\n{'=' * total_width}")
    print(f"{power_name} - System Details")
    print(f"{'=' * total_width}\n")

    # Header
    print(f"{'System':<{col_name}} {'State':<{col_state}} {'RF':>{col_rf}} {'(net) UM':>{col_um}} {'UM%':>{col_pct}} {'~Decay':>{col_dec}}")
    print("-" * total_width)

    # Sort by state priority (Stronghold > Fortified > Exploited), then by name
    state_priority = {'STRONGHOLD': 0, 'FORTIFIED': 1, 'EXPLOITED': 2}
    sorted_systems = sorted(power_systems, key=lambda s: (
        state_priority.get(s['state'], 99),
        s['name']
    ))

    for sys_data in sorted_systems:
        name = sys_data['name']
        state = sys_data['state'].capitalize()
        rf = sys_data['reinforcement']
        um = sys_data['undermining']
        decay = sys_data['decay']
        um_pct = (um / rf * 100) if rf > 0 else 0
        print(f"{name:<{col_name}} {state:<{col_state}} {format_kilo(rf):>{col_rf}} {format_kilo(um):>{col_um}} {um_pct:>{col_pct - 1}.1f}% {format_kilo(decay):>{col_dec}}")

    # Totals for this power
    print("-" * total_width)
    total_rf = sum(s['reinforcement'] for s in power_systems)
    total_um = sum(s['undermining'] for s in power_systems)
    total_decay = sum(s['decay'] for s in power_systems)
    total_um_pct = (total_um / total_rf * 100) if total_rf > 0 else 0
    print(f"{'TOTAL':<{col_name}} {'':<{col_state}} {format_kilo(total_rf):>{col_rf}} {format_kilo(total_um):>{col_um}} {total_um_pct:>{col_pct - 1}.1f}% {format_kilo(total_decay):>{col_dec}}")


def main():
    parser = argparse.ArgumentParser(
        description='Summarize powerplay data by power with detailed system breakdown'
    )
    parser.add_argument(
        'filepath',
        nargs='?',
        default='powerplay_auto_capture.txt',
        help='Path to the powerplay capture file (default: powerplay_auto_capture.txt)'
    )
    parser.add_argument(
        '-p', '--power',
        default='Pranav Antal',
        help='Power name for detailed system view (default: Pranav Antal)'
    )

    args = parser.parse_args()

    try:
        powers, systems, data_timestamp = parse_powerplay_file(args.filepath)

        if not powers:
            print(f"No data found in {args.filepath}")
            return 1

        print_summary(powers, data_timestamp)
        print_power_details(systems, args.power)
        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {args.filepath}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
