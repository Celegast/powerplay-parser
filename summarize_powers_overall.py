"""
Summarize powerplay data over all stored cycles.
For each cycle, all captured files are scanned in chronological order.
Each system's data is updated whenever it appears, so the final per-cycle
totals always reflect the most recent reading of every system seen that cycle.
Per-cycle numbers are then accumulated into overall totals per power.
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from summarize_powers import (
    parse_powerplay_file,
    get_cycle_number,
    format_kilo,
)


def get_cycle_tick_time(reference_time):
    """Most recent Thursday 7am UTC at or before reference_time."""
    if reference_time.tzinfo is None:
        reference_utc = reference_time.replace(tzinfo=timezone.utc)
    else:
        reference_utc = reference_time.astimezone(timezone.utc)

    weekday = reference_utc.weekday()  # Mon=0 … Sun=6; Thu=3
    days_back = (weekday - 3) % 7
    tick = (reference_utc - timedelta(days=days_back)).replace(
        hour=7, minute=0, second=0, microsecond=0
    )
    if tick > reference_utc:
        tick -= timedelta(days=7)
    return tick


def load_cycle_files(output_dir='auto_capture_outputs'):
    """
    Group all capture files by cycle.
    Returns an ordered list of (cycle_tick, [(file_utc, filepath), ...])
    sorted chronologically by cycle.
    """
    pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
    files = sorted(glob.glob(pattern))

    if not files:
        return []

    local_tz = datetime.now().astimezone().tzinfo
    cycle_files = defaultdict(list)  # cycle_tick -> [(file_utc, filepath), ...]

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            ts_str = filename.replace('powerplay_auto_capture_', '').replace('.txt', '')
            file_time_local = datetime.strptime(ts_str, '%Y%m%d_%H%M%S').replace(tzinfo=local_tz)
            file_time_utc = file_time_local.astimezone(timezone.utc)
        except ValueError:
            continue

        tick = get_cycle_tick_time(file_time_utc)
        cycle_files[tick].append((file_time_utc, filepath))

    return [
        (tick, sorted(cycle_files[tick], key=lambda x: x[0]))
        for tick in sorted(cycle_files.keys())
    ]


def build_cycle_snapshot(files):
    """
    Given all (file_utc, filepath) pairs for one cycle (in chronological order),
    walk them and keep the latest reading for every system seen.
    Returns a per-power aggregated dict identical in structure to what
    parse_powerplay_file returns for 'powers'.
    """
    system_latest = {}  # system_name -> system dict from parse_powerplay_file

    for _file_utc, filepath in files:
        try:
            _, systems, _ = parse_powerplay_file(filepath)
        except Exception as e:
            print(f"Warning: could not parse {os.path.basename(filepath)}: {e}",
                  file=sys.stderr)
            continue
        for sys_data in systems:
            system_latest[sys_data['name']] = sys_data

    # Aggregate latest system readings into per-power totals
    powers = defaultdict(lambda: {
        'reinforcement': 0,
        'undermining': 0,
        'decay': 0,
        'stronghold': 0,
        'fortified': 0,
        'exploited': 0,
    })
    for sys_data in system_latest.values():
        power = sys_data['power']
        powers[power]['reinforcement'] += sys_data['reinforcement']
        powers[power]['undermining']   += sys_data['undermining']
        powers[power]['decay']         += sys_data['decay']
        state = sys_data['state'].upper()
        if 'STRONGHOLD' in state:
            powers[power]['stronghold'] += 1
        elif 'FORTIFIED' in state:
            powers[power]['fortified'] += 1
        elif 'EXPLOITED' in state:
            powers[power]['exploited'] += 1

    powers_filtered = {
        power: data for power, data in powers.items()
        if data['reinforcement'] > 0 or data['undermining'] > 0
    }
    return powers_filtered, system_latest


def accumulate_cycle_data(cycle_files_list):
    """
    For each cycle, build a per-system-latest snapshot and accumulate totals.
    Returns:
      totals        – per-power dict with summed RF/UM/decay and cycle count
      system_totals – per-system dict with summed RF/UM/decay and last known state
      per_cycle     – list of {'cycle': int, 'powers': dict} for verbose output
    """
    totals = defaultdict(lambda: {
        'reinforcement': 0,
        'undermining': 0,
        'decay': 0,
        'stronghold': 0,
        'fortified': 0,
        'exploited': 0,
        'cycles': 0,
    })
    system_totals = {}  # system_name -> accumulated data
    per_cycle = []

    for cycle_tick, files in cycle_files_list:
        cycle_num = get_cycle_number(cycle_tick)
        powers, system_latest = build_cycle_snapshot(files)

        if not powers:
            continue

        per_cycle.append({'cycle': cycle_num, 'powers': powers})

        for power, data in powers.items():
            totals[power]['reinforcement'] += data['reinforcement']
            totals[power]['undermining']   += data['undermining']
            totals[power]['decay']         += data['decay']
            totals[power]['stronghold']    += data['stronghold']
            totals[power]['fortified']     += data['fortified']
            totals[power]['exploited']     += data['exploited']
            totals[power]['cycles']        += 1

        for name, sys_data in system_latest.items():
            if name not in system_totals:
                system_totals[name] = {
                    'power': sys_data['power'],
                    'last_state': sys_data['state'],
                    'reinforcement': 0,
                    'undermining': 0,
                    'decay': 0,
                }
            system_totals[name]['last_state']    = sys_data['state']
            system_totals[name]['reinforcement'] += sys_data['reinforcement']
            system_totals[name]['undermining']   += sys_data['undermining']
            system_totals[name]['decay']         += sys_data['decay']

    return totals, system_totals, per_cycle


def print_overall_summary(totals, per_cycle):
    """Print the accumulated overall summary table."""
    if not totals:
        print("No data to summarize.")
        return

    cycles = sorted(entry['cycle'] for entry in per_cycle)
    print(f"Overall Summary — Cycles {cycles[0]}–{cycles[-1]} ({len(cycles)} cycles) — Enclave")
    print()

    # Sort by total reinforcement descending
    sorted_powers = sorted(totals.keys(), key=lambda p: -totals[p]['reinforcement'])

    col_power = max(len("Power"), max(len(p) for p in totals))
    col_cyc   = max(len("C"), max(len(str(totals[p]['cycles'])) for p in totals))
    col_rf    = 9
    col_um    = 9
    col_pct   = 6
    col_dec   = 9

    total_width = col_power + col_cyc + col_rf + col_um + col_pct + col_dec + 5

    print(f"{'Power':<{col_power}} {'C':>{col_cyc}} {'RF':>{col_rf}} {'(net) UM':>{col_um}} {'UM%':>{col_pct}} {'~Decay':>{col_dec}}")
    print("-" * total_width)

    for power in sorted_powers:
        d = totals[power]
        um_pct = (d['undermining'] / d['reinforcement'] * 100) if d['reinforcement'] > 0 else 0
        print(
            f"{power:<{col_power}} "
            f"{d['cycles']:>{col_cyc}} "
            f"{format_kilo(d['reinforcement']):>{col_rf}} "
            f"{format_kilo(d['undermining']):>{col_um}} "
            f"{um_pct:>{col_pct - 1}.1f}% "
            f"{format_kilo(d['decay']):>{col_dec}}"
        )

    # Totals row
    print("-" * total_width)
    total_rf  = sum(d['reinforcement'] for d in totals.values())
    total_um  = sum(d['undermining']   for d in totals.values())
    total_dec = sum(d['decay']         for d in totals.values())
    total_um_pct = (total_um / total_rf * 100) if total_rf > 0 else 0
    print(
        f"{'TOTAL':<{col_power}} "
        f"{len(cycles):>{col_cyc}} "
        f"{format_kilo(total_rf):>{col_rf}} "
        f"{format_kilo(total_um):>{col_um}} "
        f"{total_um_pct:>{col_pct - 1}.1f}% "
        f"{format_kilo(total_dec):>{col_dec}}"
    )


def print_per_cycle_table(per_cycle):
    """Print a per-cycle breakdown showing each cycle's snapshot totals."""
    if not per_cycle:
        return

    print("\n\nPer-Cycle Breakdown")
    print("=" * 60)

    for entry in per_cycle:
        cycle_num = entry['cycle']
        powers    = entry['powers']
        if not powers:
            continue

        col_power = max(len("Power"), max(len(p) for p in powers))
        col_rf    = 7
        col_um    = 8
        col_pct   = 6
        row_width = col_power + col_rf + col_um + col_pct + 3

        print(f"\nCycle {cycle_num}:")
        print(f"  {'Power':<{col_power}} {'RF':>{col_rf}} {'(net) UM':>{col_um}} {'UM%':>{col_pct}}")
        print(f"  {'-' * row_width}")

        for power in sorted(powers, key=lambda p: -powers[p]['reinforcement']):
            d = powers[power]
            um_pct = (d['undermining'] / d['reinforcement'] * 100) if d['reinforcement'] > 0 else 0
            print(
                f"  {power:<{col_power}} "
                f"{format_kilo(d['reinforcement']):>{col_rf}} "
                f"{format_kilo(d['undermining']):>{col_um}} "
                f"{um_pct:>{col_pct - 1}.1f}%"
            )


def print_system_details(system_totals, power_name='Pranav Antal'):
    """Print accumulated system details for a specific power."""
    power_systems = {
        name: data for name, data in system_totals.items()
        if data['power'] == power_name
    }

    if not power_systems:
        print(f"\nNo systems found for {power_name}")
        return

    col_name  = max(len("System"), max(len(n) for n in power_systems)) + 1
    col_state = max(len("State"), max(len(d['last_state']) for d in power_systems.values()))
    col_rf    = 7
    col_um    = 9
    col_pct   = 6
    col_dec   = 8

    total_width = col_name + col_state + col_rf + col_um + col_pct + col_dec + 5

    print(f"\n\n{'=' * total_width}")
    print(f"{power_name} — System Details (accumulated)")
    print(f"{'=' * total_width}\n")

    print(f"{'System':<{col_name}} {'State':<{col_state}} {'RF':>{col_rf}} {'(net) UM':>{col_um}} {'UM%':>{col_pct}} {'~Decay':>{col_dec}}")
    print("-" * total_width)

    state_priority = {'STRONGHOLD': 0, 'FORTIFIED': 1, 'EXPLOITED': 2}
    sorted_systems = sorted(
        power_systems.items(),
        key=lambda kv: (state_priority.get(kv[1]['last_state'].upper(), 99), kv[0])
    )

    for name, d in sorted_systems:
        state  = d['last_state'].capitalize()
        rf     = d['reinforcement']
        um     = d['undermining']
        decay  = d['decay']
        um_pct = (um / rf * 100) if rf > 0 else 0
        print(f"{name:<{col_name}} {state:<{col_state}} {format_kilo(rf):>{col_rf}} {format_kilo(um):>{col_um}} {um_pct:>{col_pct - 1}.1f}% {format_kilo(decay):>{col_dec}}")

    print("-" * total_width)
    total_rf  = sum(d['reinforcement'] for d in power_systems.values())
    total_um  = sum(d['undermining']   for d in power_systems.values())
    total_dec = sum(d['decay']         for d in power_systems.values())
    total_um_pct = (total_um / total_rf * 100) if total_rf > 0 else 0
    print(f"{'TOTAL':<{col_name}} {'':<{col_state}} {format_kilo(total_rf):>{col_rf}} {format_kilo(total_um):>{col_um}} {total_um_pct:>{col_pct - 1}.1f}% {format_kilo(total_dec):>{col_dec}}")


def main():
    parser = argparse.ArgumentParser(
        description='Summarize powerplay totals accumulated across all stored cycles'
    )
    parser.add_argument(
        '-d', '--dir',
        default='auto_capture_outputs',
        help='Directory containing capture files (default: auto_capture_outputs)'
    )
    parser.add_argument(
        '-c', '--cycles',
        nargs=2,
        type=int,
        metavar=('START', 'END'),
        help='Restrict to a cycle range, e.g. -c 61 64'
    )
    parser.add_argument(
        '-p', '--power',
        default='Pranav Antal',
        help='Power name for detailed system view (default: Pranav Antal)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Also print per-cycle breakdown'
    )

    args = parser.parse_args()

    cycle_files_list = load_cycle_files(args.dir)
    if not cycle_files_list:
        print(f"No capture files found in {args.dir}/")
        return 1

    if args.cycles:
        start_c, end_c = args.cycles
        cycle_files_list = [
            (tick, files) for tick, files in cycle_files_list
            if start_c <= get_cycle_number(tick) <= end_c
        ]
        if not cycle_files_list:
            print(f"No data found for cycles {start_c}–{end_c}")
            return 1

    totals, system_totals, per_cycle = accumulate_cycle_data(cycle_files_list)

    if not totals:
        print("No data to summarize.")
        return 1

    print_overall_summary(totals, per_cycle)
    print_system_details(system_totals, args.power)

    if args.verbose:
        print_per_cycle_table(per_cycle)

    return 0


if __name__ == '__main__':
    sys.exit(main())
