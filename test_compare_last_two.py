#!/usr/bin/env python3
"""Test comparing the last two auto capture files"""

import os
import glob
from datetime import datetime
from auto_capture import get_cycle_tick_time, load_previous_capture

# Find all capture files
output_dir = 'auto_capture_outputs'
pattern = os.path.join(output_dir, 'powerplay_auto_capture_*.txt')
files = sorted(glob.glob(pattern))

if len(files) < 2:
    print(f"ERROR: Need at least 2 capture files, found {len(files)}")
    print(f"Files in {output_dir}:")
    for f in files:
        print(f"  - {os.path.basename(f)}")
    exit(1)

# Get the last two files
prev_file = files[-2]
current_file = files[-1]

print("=" * 80)
print("COMPARING LAST TWO AUTO CAPTURE FILES")
print("=" * 80)
print(f"\nPrevious file: {os.path.basename(prev_file)}")
print(f"Current file:  {os.path.basename(current_file)}")

# Extract timestamps from filenames
def extract_timestamp(filename):
    basename = os.path.basename(filename)
    timestamp_str = basename.replace('powerplay_auto_capture_', '').replace('.txt', '')
    return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

prev_time = extract_timestamp(prev_file)
current_time = extract_timestamp(current_file)

print(f"\nPrevious timestamp: {prev_time.strftime('%Y-%m-%d %H:%M:%S')} ({prev_time.strftime('%A')})")
print(f"Current timestamp:  {current_time.strftime('%Y-%m-%d %H:%M:%S')} ({current_time.strftime('%A')})")

# Calculate cycle ticks
prev_tick = get_cycle_tick_time(prev_time)
current_tick = get_cycle_tick_time(current_time)

print(f"\nPrevious cycle tick: {prev_tick.strftime('%Y-%m-%d %H:%M UTC')} ({prev_tick.strftime('%A')})")
print(f"Current cycle tick:  {current_tick.strftime('%Y-%m-%d %H:%M UTC')} ({current_tick.strftime('%A')})")

is_same_cycle = (prev_tick == current_tick)
print(f"\nSame cycle? {is_same_cycle}")

# Load previous data using the load_previous_capture function
print("\n" + "=" * 80)
print("LOADING PREVIOUS CAPTURE DATA")
print("=" * 80)

# Temporarily create current file to test load_previous_capture
previous_data, is_same_cycle_from_func = load_previous_capture(output_dir, current_time)

print(f"\nFunction returned is_same_cycle: {is_same_cycle_from_func}")
print(f"Manual calculation is_same_cycle: {is_same_cycle}")
print(f"Match: {is_same_cycle_from_func == is_same_cycle}")

# Load current data
print("\n" + "=" * 80)
print("COMPARING CP VALUES")
print("=" * 80)

current_data = {}
try:
    with open(current_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('-') or line.startswith('='):
            continue

        parts = line.split('\t')
        if len(parts) >= 6:
            system_name = parts[0]
            try:
                undermining = int(parts[4].replace(',', '')) if parts[4] else -1
                reinforcing = int(parts[5].replace(',', '')) if parts[5] else -1
                current_data[system_name] = {'undermining': undermining, 'reinforcing': reinforcing}
            except (ValueError, IndexError):
                continue
except Exception as e:
    print(f"Error loading current file: {e}")
    exit(1)

print(f"\nLoaded {len(previous_data)} systems from previous capture")
print(f"Loaded {len(current_data)} systems from current capture")

# Compare values
violations = []
increases = []

for system_name in sorted(current_data.keys()):
    if system_name not in previous_data:
        print(f"\nNew system (not in previous): {system_name}")
        continue

    current = current_data[system_name]
    previous = previous_data[system_name]

    current_u = current.get('undermining', -1)
    current_r = current.get('reinforcing', -1)
    prev_u = previous.get('undermining', -1)
    prev_r = previous.get('reinforcing', -1)

    # Check for changes
    if current_u >= 0 and prev_u >= 0 and current_u != prev_u:
        change = current_u - prev_u
        if change < 0:
            violations.append({
                'system': system_name,
                'type': 'Undermining',
                'prev': prev_u,
                'curr': current_u,
                'change': change
            })
        else:
            increases.append({
                'system': system_name,
                'type': 'Undermining',
                'prev': prev_u,
                'curr': current_u,
                'change': change
            })

    if current_r >= 0 and prev_r >= 0 and current_r != prev_r:
        change = current_r - prev_r
        if change < 0:
            violations.append({
                'system': system_name,
                'type': 'Reinforcing',
                'prev': prev_r,
                'curr': current_r,
                'change': change
            })
        else:
            increases.append({
                'system': system_name,
                'type': 'Reinforcing',
                'prev': prev_r,
                'curr': current_r,
                'change': change
            })

if violations:
    print(f"\n{'='*80}")
    print(f"VIOLATIONS FOUND: {len(violations)} CP DECREASES (potential OCR errors)")
    print(f"{'='*80}\n")
    print(f"{'System Name':<40} {'Type':<15} {'Previous':<12} {'Current':<12} {'Change'}")
    print("-" * 100)
    for v in violations:
        name_short = v['system'][:38] if len(v['system']) > 38 else v['system']
        print(f"{name_short:<40} {v['type']:<15} {v['prev']:>10,}   {v['curr']:>10,}   {v['change']:>+10,}")
else:
    print(f"\nNo violations found (no CP decreases)")

if increases:
    print(f"\n{'='*80}")
    print(f"CP INCREASES FOUND: {len(increases)} changes")
    print(f"{'='*80}\n")
    print(f"{'System Name':<40} {'Type':<15} {'Previous':<12} {'Current':<12} {'Change'}")
    print("-" * 100)
    for v in increases:
        name_short = v['system'][:38] if len(v['system']) > 38 else v['system']
        print(f"{name_short:<40} {v['type']:<15} {v['prev']:>10,}   {v['curr']:>10,}   {v['change']:>+10,}")

unchanged_count = len([s for s in current_data.keys() if s in previous_data]) - len(violations) - len(increases)
print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Total systems compared: {len([s for s in current_data.keys() if s in previous_data])}")
print(f"  Unchanged:    {unchanged_count}")
print(f"  Increased:    {len(increases)}")
print(f"  DECREASED:    {len(violations)} {'<-- POTENTIAL OCR ERRORS' if violations else ''}")
print(f"{'='*80}")
