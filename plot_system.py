"""
Plot the control point history of a single system over all stored cycles.
Net CP (initial_cp + reinforcement - net_undermining) is drawn as a single
line, coloured by the power that owned the system at each data point.
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta, timezone

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.lines as mlines

from summarize_powers import parse_powerplay_file, get_cycle_number
from plot_overall import get_cycle_tick_time, POWER_COLORS


def load_system_data(system_name, output_dir='auto_capture_outputs'):
    """
    Scan all capture files and return every data point for the requested system.
    system_name is matched case-insensitively as a substring.

    Returns (matched_name, data_points) where:
      matched_name  – the full canonical system name, or None if not found,
                      or a list of names if the query is ambiguous
      data_points   – [(utc_datetime, power, net_cp, state), ...] sorted by time
    """
    pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
    files = sorted(glob.glob(pattern))

    if not files:
        return None, []

    local_tz = datetime.now().astimezone().tzinfo

    # First pass: collect all matching system names
    candidate_names = set()
    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            ts_str = filename.replace('powerplay_auto_capture_', '').replace('.txt', '')
            file_time_local = datetime.strptime(ts_str, '%Y%m%d_%H%M%S').replace(tzinfo=local_tz)
        except ValueError:
            continue
        try:
            _, systems, _ = parse_powerplay_file(filepath)
        except Exception:
            continue
        for sys_data in systems:
            if system_name.lower() in sys_data['name'].lower():
                candidate_names.add(sys_data['name'])

    if not candidate_names:
        return None, []

    # Resolve ambiguity: prefer exact match, otherwise report all candidates
    if len(candidate_names) > 1:
        exact = [n for n in candidate_names if n.lower() == system_name.lower()]
        if len(exact) == 1:
            candidate_names = {exact[0]}
        else:
            return sorted(candidate_names), []

    matched_name = next(iter(candidate_names))

    # Second pass: collect data points for the matched system
    data_points = []
    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            ts_str = filename.replace('powerplay_auto_capture_', '').replace('.txt', '')
            file_time_local = datetime.strptime(ts_str, '%Y%m%d_%H%M%S').replace(tzinfo=local_tz)
            file_time_utc = file_time_local.astimezone(timezone.utc)
        except ValueError:
            continue
        try:
            _, systems, _ = parse_powerplay_file(filepath)
        except Exception:
            continue
        for sys_data in systems:
            if sys_data['name'] == matched_name:
                # undermining is already decay-adjusted by parse_powerplay_file
                net_cp = (sys_data['initial_cp']
                          + sys_data['reinforcement']
                          - sys_data['undermining'])
                data_points.append((file_time_utc, sys_data['power'], net_cp,
                                    sys_data['state']))
                break

    data_points.sort(key=lambda x: x[0])
    return matched_name, data_points


def plot_system(system_name, output_file=None, output_dir='auto_capture_outputs'):
    matched_name, data_points = load_system_data(system_name, output_dir)

    if matched_name is None:
        print(f"System '{system_name}' not found in {output_dir}/")
        return 1

    if isinstance(matched_name, list):
        print(f"Ambiguous system name '{system_name}'. Did you mean:")
        for name in matched_name:
            print(f"  {name}")
        return 1

    if not data_points:
        print(f"No data points found for '{matched_name}'")
        return 1

    times   = [p[0]        for p in data_points]
    powers  = [p[1]        for p in data_points]
    cp_vals = [p[2] / 1000 for p in data_points]  # convert to k
    states  = [p[3]        for p in data_points]

    # Cycle tick boundaries — generate every weekly tick across the full date
    # range so all cycles appear at equal width, even if the system has no
    # captures in some cycles.
    first_tick = get_cycle_tick_time(times[0])
    last_tick  = get_cycle_tick_time(times[-1])
    ticks = []
    t = first_tick
    while t <= last_tick:
        ticks.append(t)
        t += timedelta(days=7)
    ticks_extended = ticks + [ticks[-1] + timedelta(days=7)]

    plt.style.use('dark_background')
    bg         = '#1a1a2e'
    grid_color = '#444466'

    fig, ax = plt.subplots(figsize=(16, 6))
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.grid(True, linestyle='--', alpha=0.35, color=grid_color)
    for spine in ax.spines.values():
        spine.set_edgecolor('#444444')

    # Shade contested time spans with a red background band.
    # A "contested run" is any sequence of CONTESTED points; we extend the band
    # slightly before the first and after the last point of each run.
    contested_run_start = None
    for i, (t, state) in enumerate(zip(times, states)):
        if state == 'CONTESTED':
            if contested_run_start is None:
                contested_run_start = t
            contested_run_end = t
            # Flush run if this is the last point
            if i == len(times) - 1:
                ax.axvspan(contested_run_start - timedelta(hours=12),
                           contested_run_end   + timedelta(hours=12),
                           alpha=0.15, color='red', zorder=0, label='_nolegend_')
        else:
            if contested_run_start is not None:
                ax.axvspan(contested_run_start - timedelta(hours=12),
                           contested_run_end   + timedelta(hours=12),
                           alpha=0.15, color='red', zorder=0, label='_nolegend_')
                contested_run_start = None

    # Horizontal threshold lines
    THRESHOLDS = [
        (350,  'Fortified',  '#44bb66'),
        (1000, 'Stronghold', '#aa44ff'),
    ]
    for level, label, color in THRESHOLDS:
        ax.axhline(level, color=color, linestyle='--', linewidth=0.8, alpha=0.5)
        # Label pinned to the right edge of the plot (x=1 in axes fraction, y in data)
        ax.text(0.998, level, label,
                transform=ax.get_yaxis_transform(),
                va='bottom', ha='right', fontsize=7, color=color, alpha=0.8)

    # Draw connecting line segments coloured by the power at the segment start
    for i in range(len(times) - 1):
        color = POWER_COLORS.get(powers[i], '#888888')
        ax.plot([times[i], times[i + 1]], [cp_vals[i], cp_vals[i + 1]],
                color=color, linewidth=1.5, solid_capstyle='round')

    # Draw markers: circle for normal, × for contested
    for t, pwr, cp, state in zip(times, powers, cp_vals, states):
        color = POWER_COLORS.get(pwr, '#888888')
        if state == 'CONTESTED':
            ax.plot(t, cp, marker='x', markersize=6, markeredgewidth=1.5,
                    color='red', zorder=6)
        else:
            ax.plot(t, cp, marker='o', markersize=3, color=color, zorder=5)

    # State abbreviations and colours for cycle labels
    STATE_ABBREV = {
        'STRONGHOLD': 'SH',
        'FORTIFIED':  'FF',
        'EXPLOITED':  'EX',
        'CONTESTED':  'C!',
    }
    STATE_COLOR = {
        'STRONGHOLD': '#aa44ff',
        'FORTIFIED':  '#44bb66',
        'EXPLOITED':  '#ff4444',
        'CONTESTED':  '#ff8800',
    }

    # Cycle tick boundaries + cycle number labels + per-cycle state
    for idx, tick in enumerate(ticks_extended):
        cycle_num = get_cycle_number(tick)
        ax.axvline(tick, color='#888888', linestyle=':', linewidth=0.8, alpha=0.7)
        if idx + 1 < len(ticks_extended):
            next_tick = ticks_extended[idx + 1]
            mid = tick + (next_tick - tick) / 2
            ax.text(mid, 1.11, f'C{cycle_num}',
                    ha='center', va='top', fontsize=8, color='#aaaaaa',
                    transform=ax.get_xaxis_transform(), clip_on=False)
            # Find the last data point in this cycle and show its state
            cycle_pts = [(t, s) for t, s in zip(times, states)
                         if tick <= t < next_tick]
            if cycle_pts:
                last_state = cycle_pts[-1][1].upper()
                abbrev = STATE_ABBREV.get(last_state, '?')
                color  = STATE_COLOR.get(last_state, '#aaaaaa')
                ax.text(mid, 1.05, abbrev,
                        ha='center', va='top', fontsize=7, color=color,
                        transform=ax.get_xaxis_transform(), clip_on=False)

    # Axes formatting
    ax.set_ylabel('Control Points (k)', fontsize=11, color='#cccccc')
    ax.set_xlabel('Date (UTC)',          fontsize=11, color='#cccccc')
    ax.tick_params(colors='#cccccc')
    ax.tick_params(right=True, labelright=True, colors='#cccccc')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d', tz=timezone.utc))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right', color='#cccccc')
    ax.set_xlim(times[0] - timedelta(hours=6), times[-1] + timedelta(hours=6))

    # Legend — only powers that actually appear in the data, plus contested marker
    seen_powers = sorted(set(powers))
    legend_handles = [
        mlines.Line2D([], [], color=POWER_COLORS.get(p, '#888888'),
                      linewidth=2, label=p)
        for p in seen_powers
    ]
    if 'CONTESTED' in states:
        legend_handles.append(
            mlines.Line2D([], [], color='red', marker='x', markersize=6,
                          markeredgewidth=1.5, linestyle='none', label='Contested')
        )
    ax.legend(handles=legend_handles,
              loc='upper left', fontsize=9,
              facecolor='#2a2a3e', edgecolor='#444444', labelcolor='#cccccc')

    first_cycle = get_cycle_number(ticks[0])  if ticks else '?'
    last_cycle  = get_cycle_number(ticks[-1]) if ticks else '?'
    fig.suptitle(
        f'Enclave — {matched_name} — CP History — C{first_cycle}–C{last_cycle}',
        fontsize=13, color='#ffffff', y=0.99
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Plot CP history for a single system across all stored cycles'
    )
    parser.add_argument(
        'system',
        help='System name or substring (case-insensitive)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (e.g., system.png). If omitted, displays the plot.'
    )
    parser.add_argument(
        '-d', '--dir',
        default='auto_capture_outputs',
        help='Directory containing capture files (default: auto_capture_outputs)'
    )
    args = parser.parse_args()
    return plot_system(args.system, output_file=args.output, output_dir=args.dir)


if __name__ == '__main__':
    sys.exit(main())
