"""
Plot powerplay RF and UM data across all stored cycles.
Generates a two-panel figure (reinforcement + undermining) showing every
captured data point, with cycle-tick boundaries marked.
"""

import os
import glob
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from summarize_powers import parse_powerplay_file, get_cycle_number, CYCLE_1_START


POWER_COLORS = {
    'Aisling Duval':          '#05c5fe',
    'Pranav Antal':           '#fff800',
    'Nakato Kaine':           '#b3ff05',
    'Arissa Lavigny-Duval':   '#b505fd',
    'Yuri Grom':              '#ff8105',
    'Denton Patreus':         '#36dfdf',
    'Jerome Archer':          '#ff05fe',
    'Archon Delaine':         '#ff0000',
    'Edmund Mahon':           '#00ae1d',
    'Zemina Torval':          '#0080fe',
    'Felicia Winters':        '#ffb500',
    'Li Yong-Rui':            '#00fe94',
}


def get_cycle_tick_time(reference_time):
    """Most recent Thursday 7am UTC before (or at) reference_time."""
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


def load_all_data(output_dir='auto_capture_outputs'):
    """
    Load every capture file and return
      power_data[power] = [(utc_datetime, rf, um), ...]
    sorted chronologically, plus a list of all cycle-tick boundaries found.
    """
    pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
    files = sorted(glob.glob(pattern))

    if not files:
        return {}, []

    local_tz = datetime.now().astimezone().tzinfo
    power_data = defaultdict(list)
    tick_set = set()

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            ts_str = filename.replace('powerplay_auto_capture_', '').replace('.txt', '')
            file_time_local = datetime.strptime(ts_str, '%Y%m%d_%H%M%S').replace(tzinfo=local_tz)
            file_time_utc = file_time_local.astimezone(timezone.utc)
        except ValueError:
            continue

        tick_set.add(get_cycle_tick_time(file_time_utc))

        try:
            powers, _, _ = parse_powerplay_file(filepath)
        except Exception:
            continue

        for power_name, data in powers.items():
            power_data[power_name].append((
                file_time_utc,
                data.get('reinforcement', 0),
                data.get('undermining', 0),
            ))

    # Sort each power's series chronologically
    for power_name in power_data:
        power_data[power_name].sort(key=lambda x: x[0])

    ticks = sorted(tick_set)
    return power_data, ticks


def plot_overall(output_file=None, powers=None):
    """
    Args:
        output_file: Path to save the figure; if None the plot is displayed.
        powers: Optional list of power name substrings (case-insensitive) to include.
                If None or empty, all powers are shown.
    """
    power_data, ticks = load_all_data()

    if not power_data:
        print("No data found in auto_capture_outputs/")
        return

    # Filter to requested powers (case-insensitive substring match)
    if powers:
        filters = [p.lower() for p in powers]
        power_data = {
            name: pts for name, pts in power_data.items()
            if any(f in name.lower() for f in filters)
        }
        if not power_data:
            print(f"No data found for powers matching: {', '.join(powers)}")
            print(f"Available powers: {', '.join(sorted(POWER_COLORS))}")
            return

    # Determine time range
    all_times = [pt[0] for pts in power_data.values() for pt in pts]
    t_min = min(all_times)
    t_max = max(all_times)

    # One extra tick boundary beyond the last data point (for the right edge label)
    if ticks and ticks[-1] <= t_max:
        ticks_extended = ticks + [ticks[-1] + timedelta(days=7)]
    else:
        ticks_extended = ticks

    plt.style.use('dark_background')
    bg = '#1a1a2e'
    grid_color = '#444466'

    fig, (ax_rf, ax_um) = plt.subplots(2, 1, figsize=(18, 10), sharex=True)
    fig.patch.set_facecolor(bg)

    for ax in (ax_rf, ax_um):
        ax.set_facecolor(bg)
        ax.grid(True, linestyle='--', alpha=0.35, color=grid_color)
        for spine in ax.spines.values():
            spine.set_edgecolor('#444444')

    # Plot lines and annotate the last captured point of each cycle
    for power_name in sorted(power_data.keys()):
        pts = power_data[power_name]
        times = [p[0] for p in pts]
        rf_vals = [p[1] / 1000 for p in pts]
        um_vals = [p[2] / 1000 for p in pts]
        color = POWER_COLORS.get(power_name, '#888888')

        ax_rf.plot(times, rf_vals, marker='o', markersize=3, linewidth=1.5,
                   label=power_name, color=color)
        ax_um.plot(times, um_vals, marker='o', markersize=3, linewidth=1.5,
                   label=power_name, color=color)

        # Annotate the last data point of each cycle (shows end-of-cycle totals)
        for i, (t, rf, um) in enumerate(zip(times, rf_vals, um_vals)):
            is_last_in_cycle = (
                i == len(times) - 1
                or get_cycle_tick_time(times[i + 1]) != get_cycle_tick_time(t)
            )
            if not is_last_in_cycle:
                continue
            if rf >= 100:
                ax_rf.annotate(f'{rf:.0f}k', xy=(t, rf),
                               xytext=(0, 5), textcoords='offset points',
                               ha='center', fontsize=6, color=color)
            if um >= 100:
                ax_um.annotate(f'{um:.0f}k', xy=(t, um),
                               xytext=(0, 5), textcoords='offset points',
                               ha='center', fontsize=6, color=color)

    # Cycle tick boundary lines + cycle number labels
    # get_xaxis_transform(): x in data coords, y in axes fraction (0=bottom, 1=top)
    for idx, tick in enumerate(ticks_extended):
        cycle_num = get_cycle_number(tick)
        for ax in (ax_rf, ax_um):
            ax.axvline(tick, color='#888888', linestyle=':', linewidth=0.8, alpha=0.7)
        # Label centred in the cycle band, pinned near the top of the RF axes
        if idx + 1 < len(ticks_extended):
            mid = tick + (ticks_extended[idx + 1] - tick) / 2
            ax_rf.text(mid, 0.97,
                       f'C{cycle_num}', ha='center', va='top',
                       fontsize=8, color='#aaaaaa',
                       transform=ax_rf.get_xaxis_transform())

    # Axes formatting
    ax_rf.set_ylabel('Reinforcement (k)', fontsize=11, color='#cccccc')
    ax_um.set_ylabel('Undermining (k)',   fontsize=11, color='#cccccc')
    ax_um.set_xlabel('Date (UTC)',        fontsize=11, color='#cccccc')

    for ax in (ax_rf, ax_um):
        ax.tick_params(colors='#cccccc')

    ax_um.xaxis.set_major_formatter(mdates.DateFormatter('%b %d', tz=timezone.utc))
    ax_um.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax_um.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#cccccc')

    ax_rf.set_xlim(t_min - timedelta(hours=6), t_max + timedelta(hours=6))

    # Title
    first_cycle = get_cycle_number(ticks[0]) if ticks else '?'
    last_cycle  = get_cycle_number(ticks[-1]) if ticks else '?'
    n = len(power_data)
    if n == len(POWER_COLORS) or powers is None:
        power_subtitle = 'All Powers'
    elif n <= 3:
        power_subtitle = ' / '.join(sorted(power_data.keys()))
    else:
        power_subtitle = f'{n} Powers'
    fig.suptitle(
        f'Enclave — Cycle {first_cycle}–{last_cycle} — RF & UM — {power_subtitle}',
        fontsize=14, color='#ffffff', y=0.99
    )

    # Shared legend below the figure (columns scale with number of powers shown)
    handles, labels = ax_rf.get_legend_handles_labels()
    ncol = min(n, 6)
    fig.legend(handles, labels,
               loc='lower center', ncol=ncol,
               fontsize=9, facecolor='#2a2a3e', edgecolor='#444444',
               labelcolor='#cccccc',
               bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.06, 1, 0.98])

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plot RF and UM across all stored cycle data'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (e.g., overall.png). If omitted, displays the plot.'
    )
    parser.add_argument(
        '-p', '--powers',
        nargs='+',
        metavar='POWER',
        help=(
            'One or more power name substrings to plot (case-insensitive). '
            'E.g.: -p "Pranav Antal" Nakato  →  shows Pranav Antal and Nakato Kaine. '
            'If omitted, all powers are shown.'
        )
    )
    args = parser.parse_args()
    plot_overall(output_file=args.output, powers=args.powers)


if __name__ == '__main__':
    main()
