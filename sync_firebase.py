"""
Sync powerplay capture data directly to the Firebase Realtime Database
backing E:\\ED\\ed-powerplay-tracker.

No authentication required — the database path used by the web app
allows public read/write.

Options:
  -c, --capture FILE   Capture file to read (default: powerplay_auto_capture.txt)
  --system SYSTEM      Only sync the system whose name contains SYSTEM (case-insensitive)
  --dry-run            Print what would change without writing to the database
"""

import os
import re
import sys
import argparse
from datetime import datetime, timezone

import requests

from summarize_powers import parse_powerplay_file, get_cycle_number
import credentials


# ── Configuration ─────────────────────────────────────────────────────────────

FIREBASE_BASE = 'https://ed-powerplay-tracker-default-rtdb.europe-west1.firebasedatabase.app'
FIREBASE_PATH = f'sq/{credentials.FIREBASE_DB_KEY}/systems'


# ── Key sanitization ───────────────────────────────────────────────────────────

def make_system_key(name):
    """Object key stored in the system document (spaces->_, strip quotes/backslashes)."""
    k = re.sub(r'\s+', '_', name)
    k = re.sub(r"['\"/\\]", '', k)
    return k


def make_url_key(system_key):
    """URL-safe Firebase path segment (additionally replace . # $ [ ] / space)."""
    return re.sub(r'[.#$\[\]/ ]', '_', system_key)


def firebase_url(name):
    system_key = make_system_key(name)
    url_key    = make_url_key(system_key)
    return f'{FIREBASE_BASE}/{FIREBASE_PATH}/{url_key}.json', system_key


# ── Firebase helpers ───────────────────────────────────────────────────────────

def fb_get(url):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()  # None when Firebase has nothing at this path


def fb_put(url, data):
    resp = requests.put(url, json=data, timeout=15)
    resp.raise_for_status()


# ── Data merging ───────────────────────────────────────────────────────────────

def build_data_point(sys_data, timestamp_str):
    um = sys_data['undermining_raw']
    rf = sys_data['reinforcement']
    cp = sys_data['initial_cp'] + rf - um
    return {
        'timestamp':    timestamp_str,
        'undermining':  um,
        'reinforcement': rf,
        'cp':           cp,
    }


def merge_system(existing_doc, sys_data, system_key, cycle_str, timestamp_str):
    """
    Insert a new data point into an existing system document (or create the doc).
    Returns (updated_doc, was_added).
    """
    if existing_doc is None:
        doc = {'name': sys_data['name'], 'key': system_key, 'cycles': {}}
    else:
        doc = existing_doc

    doc.setdefault('cycles', {})

    if cycle_str not in doc['cycles']:
        doc['cycles'][cycle_str] = {
            'power':                   sys_data['power'],
            'state':                   sys_data['state'].lower(),
            'initialCP':               sys_data['initial_cp'],
            'underminingThreshold':    0,
            'reinforcementThreshold':  0,
            'data':                    [],
        }
    else:
        cycle = doc['cycles'][cycle_str]
        cycle['power'] = sys_data['power']
        cycle['state'] = sys_data['state'].lower()

    cycle = doc['cycles'][cycle_str]
    cycle.setdefault('data', [])

    # Skip duplicate timestamps
    existing_ts = {d.get('timestamp') for d in cycle['data']}
    data_point  = build_data_point(sys_data, timestamp_str)
    if data_point['timestamp'] in existing_ts:
        return doc, False

    cycle['data'].append(data_point)
    return doc, True


# ── Main sync logic ────────────────────────────────────────────────────────────

def sync_firebase(system_map, data_timestamp, system_filter=None, dry_run=False):
    cycle_num = get_cycle_number()
    cycle_str = str(cycle_num)

    if data_timestamp:
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', data_timestamp)
        ts_str = (f"{m.group(1)}T{m.group(2)}:00.000Z" if m
                  else datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'))
    else:
        ts_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

    systems = list(system_map.values())

    if system_filter:
        needle  = system_filter.lower()
        matches = [s for s in systems if needle in s['name'].lower()]
        if not matches:
            sys.exit(f"ERROR: no system in capture matches '{system_filter}'")
        if len(matches) > 1:
            print(f"Ambiguous filter '{system_filter}' matches {len(matches)} systems:")
            for s in matches:
                print(f"  {s['name']}")
            sys.exit("Use a more specific substring.")
        systems = matches

    print(f"Syncing {len(systems)} system(s) to Firebase  "
          f"(cycle {cycle_num}, timestamp {ts_str})")
    if dry_run:
        print("(dry-run - no writes will be sent)")
    print()

    added = skipped = errors = 0

    for sys_data in systems:
        name = sys_data['name']
        url, system_key = firebase_url(name)

        try:
            existing       = fb_get(url)
            doc, was_added = merge_system(existing, sys_data, system_key, cycle_str, ts_str)

            if was_added and not dry_run:
                fb_put(url, doc)

            tag    = '[DRY]' if dry_run else ('[+]  ' if was_added else '[=]  ')
            detail = 'added' if was_added else 'skipped (duplicate timestamp)'
            print(f"  {tag} {name[:55]:<55}  {detail}")

            if was_added:
                added += 1
            else:
                skipped += 1

        except Exception as exc:
            print(f"  [ERR] {name[:55]:<55}  {exc}")
            errors += 1

    print()
    print(f"Done: {added} added, {skipped} skipped (duplicate), {errors} errors")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Sync powerplay capture data to the Firebase Realtime Database'
    )
    parser.add_argument(
        '-c', '--capture',
        default='powerplay_auto_capture.txt',
        help='Capture file to read (default: powerplay_auto_capture.txt)'
    )
    parser.add_argument(
        '--system',
        metavar='SYSTEM',
        default=None,
        help='Only sync the system whose name contains SYSTEM (case-insensitive substring)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would change without writing to the database'
    )
    args = parser.parse_args()

    if not os.path.isfile(args.capture):
        sys.exit(f"ERROR: Capture file not found: {args.capture}")

    print(f"Reading capture data from {args.capture} ...")
    _, systems_list, data_timestamp = parse_powerplay_file(args.capture)
    system_map = {s['name'].lower(): s for s in systems_list}
    print(f"  {len(system_map)} systems loaded"
          + (f", timestamp: {data_timestamp}" if data_timestamp else ''))
    print()

    sync_firebase(
        system_map,
        data_timestamp,
        system_filter=args.system,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
