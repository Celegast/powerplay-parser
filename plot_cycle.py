"""
Plot powerplay data over time for the current cycle.
Generates graphs showing RF, UM, or both metrics for all powers.
"""

import os
import glob
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from summarize_powers import parse_powerplay_file, get_cycle_number, CYCLE_1_START


# Power colors (RGB values converted to matplotlib format)
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

METRIC_LABELS = {
    'reinforcement': 'Reinforcement (RF)',
    'undermining':   'Undermining (UM)',
    'decay':         'Decay',
}


def get_cycle_tick_time(reference_time):
    """Calculate the most recent Thursday 7am UTC tick before (or at) the reference time."""
    if reference_time.tzinfo is None:
        reference_utc = reference_time.replace(tzinfo=timezone.utc)
    else:
        reference_utc = reference_time.astimezone(timezone.utc)

    current_weekday = reference_utc.weekday()

    if current_weekday >= 3:
        days_since_thursday = current_weekday - 3
    else:
        days_since_thursday = current_weekday + 4

    last_thursday = reference_utc - timedelta(days=days_since_thursday)
    last_tick = last_thursday.replace(hour=7, minute=0, second=0, microsecond=0)

    if last_tick > reference_utc:
        last_tick = last_tick - timedelta(days=7)

    return last_tick


def get_cycle_files(output_dir='auto_capture_outputs'):
    """Get all capture files from the current cycle, sorted by timestamp."""
    pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
    files = glob.glob(pattern)

    if not files:
        return []

    current_tick = get_cycle_tick_time(datetime.now(timezone.utc))
    cycle_files = []

    local_tz = datetime.now().astimezone().tzinfo

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            timestamp_str = filename.replace('powerplay_auto_capture_', '').replace('.txt', '')
            file_time_local = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            file_time_local = file_time_local.replace(tzinfo=local_tz)
            file_time_utc = file_time_local.astimezone(timezone.utc)

            file_tick = get_cycle_tick_time(file_time_utc)
            if file_tick == current_tick:
                cycle_files.append((file_time_utc, filepath))
        except ValueError:
            continue

    cycle_files.sort(key=lambda x: x[0])
    return cycle_files


def collect_cycle_data():
    """Collect RF and UM for all powers across the current cycle.

    Returns:
        {power_name: [(utc_datetime, rf, um), ...]} or None if no data found.
    """
    cycle_files = get_cycle_files()

    if not cycle_files:
        print("No files found for current cycle")
        return None

    power_data = defaultdict(list)

    for file_time, filepath in cycle_files:
        powers, _systems, _ts = parse_powerplay_file(filepath)
        for power_name, data in powers.items():
            power_data[power_name].append((
                file_time,
                data.get('reinforcement', 0),
                data.get('undermining', 0),
            ))

    return power_data


def _annotate_points(ax, times, values, color):
    """Add value labels to data points above 100 k."""
    for t, v in zip(times, values):
        if v > 100:
            ax.annotate(
                f'{v:.0f}k',
                xy=(t, v),
                xytext=(0, 6),
                textcoords='offset points',
                ha='center',
                fontsize=7,
                color=color,
            )


def _style_ax(ax, cycle_tick, next_tick):
    """Apply shared axis styling (grid, spines, x-axis format)."""
    ax.set_xlim(cycle_tick, next_tick)
    ax.grid(True, linestyle='--', alpha=0.3, color='#666666')
    for spine in ax.spines.values():
        spine.set_edgecolor('#444444')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %H:%M', tz=timezone.utc))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    ax.tick_params(colors='#cccccc')


def plot_cycle_data(metric=None, output_file=None):
    """Generate a plot of cycle data.

    Args:
        metric: 'reinforcement', 'undermining', or 'decay' for a single-panel plot.
                None (default) → two-panel plot showing both RF and UM.
        output_file: Path to save the figure; if None the plot is displayed.
    """
    power_data = collect_cycle_data()
    if not power_data:
        return

    cycle_tick = get_cycle_tick_time(datetime.now(timezone.utc))
    cycle_num  = get_cycle_number(cycle_tick)
    next_tick  = cycle_tick + timedelta(days=7)

    plt.style.use('dark_background')
    bg = '#1a1a2e'

    if metric is None:
        # ── Two-panel default: RF on top, UM on bottom ──────────────────────
        fig, (ax_rf, ax_um) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        fig.patch.set_facecolor(bg)

        for ax in (ax_rf, ax_um):
            ax.set_facecolor(bg)

        for power_name in sorted(power_data.keys()):
            pts   = power_data[power_name]
            times = [p[0] for p in pts]
            rf    = [p[1] / 1000 for p in pts]
            um    = [p[2] / 1000 for p in pts]
            color = POWER_COLORS.get(power_name, '#888888')

            ax_rf.plot(times, rf, marker='o', markersize=4, linewidth=2,
                       label=power_name, color=color)
            _annotate_points(ax_rf, times, rf, color)

            ax_um.plot(times, um, marker='o', markersize=4, linewidth=2,
                       label=power_name, color=color)
            _annotate_points(ax_um, times, um, color)

        for ax in (ax_rf, ax_um):
            _style_ax(ax, cycle_tick, next_tick)

        ax_rf.set_ylabel('Reinforcement (RF) (k)', fontsize=11, color='#cccccc')
        ax_um.set_ylabel('Undermining (UM) (k)',   fontsize=11, color='#cccccc')
        ax_um.set_xlabel('Time (UTC)',              fontsize=11, color='#cccccc')
        plt.setp(ax_um.xaxis.get_majorticklabels(), rotation=45, ha='right')

        fig.suptitle(
            f'Cycle {cycle_num} - Enclave - RF & UM over Time',
            fontsize=14, color='#ffffff', y=0.99
        )

        handles, labels = ax_rf.get_legend_handles_labels()
        fig.legend(handles, labels,
                   loc='lower center', ncol=6,
                   fontsize=9, facecolor='#2a2a3e', edgecolor='#444444',
                   labelcolor='#cccccc',
                   bbox_to_anchor=(0.5, 0.0))

        plt.tight_layout(rect=(0, 0.06, 1, 0.98))

    else:
        # ── Single-panel: one specific metric ───────────────────────────────
        metric_idx = {'reinforcement': 1, 'undermining': 2, 'decay': None}
        metric_label = METRIC_LABELS.get(metric, metric.capitalize())

        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)

        for power_name in sorted(power_data.keys()):
            pts   = power_data[power_name]
            times = [p[0] for p in pts]

            if metric in ('reinforcement', 'undermining'):
                idx    = metric_idx[metric]
                values = [p[idx] / 1000 for p in pts]
            else:
                # decay: re-parse to get the raw value (not stored in collect_cycle_data)
                values = []
                for _file_time, filepath in get_cycle_files():
                    powers, _, _ = parse_powerplay_file(filepath)
                    values.append(powers.get(power_name, {}).get('decay', 0) / 1000)

            color = POWER_COLORS.get(power_name, '#888888')
            ax.plot(times, values, marker='o', markersize=4, linewidth=2,
                    label=power_name, color=color)
            _annotate_points(ax, times, values, color)

        _style_ax(ax, cycle_tick, next_tick)
        plt.xticks(rotation=45, ha='right')

        ax.set_xlabel('Time (UTC)', fontsize=12, color='#cccccc')
        ax.set_ylabel(f'{metric_label} (k)', fontsize=12, color='#cccccc')
        ax.set_title(
            f'Cycle {cycle_num} - Enclave - {metric_label} over Time',
            fontsize=14, color='#ffffff'
        )
        ax.legend(loc='upper left', fontsize=9,
                  facecolor='#2a2a3e', edgecolor='#444444', labelcolor='#cccccc')

        plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Plot powerplay data over the current cycle'
    )
    parser.add_argument(
        '-m', '--metric',
        choices=['reinforcement', 'undermining', 'decay'],
        default=None,
        help='Metric to plot. If omitted (default), both RF and UM are shown.'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (e.g., cycle_plot.png). If not specified, displays the plot.'
    )

    args = parser.parse_args()
    plot_cycle_data(metric=args.metric, output_file=args.output)


if __name__ == '__main__':
    main()
