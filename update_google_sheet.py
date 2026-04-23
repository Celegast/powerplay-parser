"""
Update the Antal Priorities Google Sheet with current powerplay data.

No Google Cloud account or billing required — this script talks to a small
Apps Script web app that lives inside the Google Sheet itself.

Setup (one-time, ~5 minutes):
  1. Open the Google Sheet → Extensions → Apps Script
  2. Paste the contents of antal_priorities_updater.gs, replacing any existing code
  3. Change SECRET_TOKEN in that script to any password you choose
  4. Click Deploy → New deployment → Web app
       Execute as:      Me
       Who has access:  Anyone
  5. Copy the deployment URL and paste it into WEB_APP_URL below
  6. Set SECRET_TOKEN below to the same value you chose in step 3

Typical workflow:
  1. python update_google_sheet.py --sync-input   # refresh input.txt from the sheet
  2. python auto_capture.py                        # capture screenshots in-game
  3. python update_google_sheet.py                 # push data + images to the sheet

Options:
  -c, --capture FILE   Capture file to read (default: powerplay_auto_capture.txt)
  --sync-input         Write the sheet's current system list to input.txt, then exit
  --no-images          Skip CP bar image updates (data only)
  --dry-run            Print what would change without modifying the sheet
"""

import os
import sys
import re
import glob
import base64
import argparse
from datetime import datetime, timezone

import requests
import cv2

from summarize_powers import parse_powerplay_file, get_cycle_number
import config


# ── Configuration ─────────────────────────────────────────────────────────────

WEB_APP_URL  = ''   # Paste the Apps Script deployment URL here
SECRET_TOKEN = ''   # Must match SECRET_TOKEN in antal_priorities_updater.gs

SHEET_NAME = f'This Cycle {get_cycle_number()}'

# CP bar region within the cropped panel image (at 740×646 reference size)
BAR_LEFT   = 16
BAR_TOP    = 568
BAR_RIGHT  = 735
BAR_BOTTOM = 609

# Fraction of the bar's left edge to discard (the grey "unoccupied" section)
BAR_CROP_LEFT_PCT = 0.24

# Target display width in the sheet (pixels); height is scaled proportionally
BAR_TARGET_WIDTH = 368

# Number of systems per POST request — keeps each call well under Apps Script's 6-min limit
POST_BATCH_SIZE = 10


# ── Capture data loading ───────────────────────────────────────────────────────

def load_capture_data(capture_file):
    """
    Returns (data_timestamp_str, system_map) where
    system_map: lowercase_name → {name, undermining, reinforcement, ...}
    """
    _, systems, data_timestamp = parse_powerplay_file(capture_file)
    system_map = {s['name'].lower(): s for s in systems}
    return data_timestamp, system_map


# ── OCR text file → capture index mapping ─────────────────────────────────────

def build_capture_index_map(ocr_text_dir='auto_capture/debug/ocr_text'):
    """
    Reads each ocr_text file for the line "CAPTURE #N - <system_name>".
    Returns dict: lowercase_name → capture_index (int)
    """
    index_map = {}
    for filepath in sorted(glob.glob(os.path.join(ocr_text_dir, 'capture_*.txt'))):
        try:
            with open(filepath, encoding='utf-8') as f:
                for line in f:
                    m = re.match(r'CAPTURE #(\d+) - (.+)', line.strip())
                    if m:
                        index_map[m.group(2).strip().lower()] = int(m.group(1))
                        break
        except Exception:
            pass
    return index_map


# ── CP bar image cropping ──────────────────────────────────────────────────────

def crop_cp_bar_b64(cropped_panel_path):
    """
    Crop the CP status bar from a cropped panel image, trim the grey
    unoccupied section on the left, and resize to BAR_TARGET_WIDTH.

    Returns (base64_png, width_px, height_px) or (None, 0, 0) on failure.
    """
    img = cv2.imread(cropped_panel_path)
    if img is None:
        return None, 0, 0

    h, w = img.shape[:2]
    scale_x = w / config.PANEL_WIDTH_STANDARD
    scale_y = h / config.PANEL_HEIGHT_STANDARD

    left   = int(BAR_LEFT   * scale_x)
    top    = int(BAR_TOP    * scale_y)
    right  = int(BAR_RIGHT  * scale_x)
    bottom = int(BAR_BOTTOM * scale_y)

    bar = img[top:bottom, left:right]
    if bar.size == 0:
        return None, 0, 0

    # Trim the grey "unoccupied" section from the left
    bar_w = bar.shape[1]
    trim  = int(bar_w * BAR_CROP_LEFT_PCT)
    bar   = bar[:, trim:]

    # Resize to target display width, preserving aspect ratio
    src_h, src_w = bar.shape[:2]
    tgt_h = max(1, int(src_h * BAR_TARGET_WIDTH / src_w))
    bar   = cv2.resize(bar, (BAR_TARGET_WIDTH, tgt_h), interpolation=cv2.INTER_AREA)

    _, buf = cv2.imencode('.png', bar)
    return base64.b64encode(buf).decode('ascii'), BAR_TARGET_WIDTH, tgt_h


# ── Sheet interaction via Apps Script ─────────────────────────────────────────

def _check_config():
    if not WEB_APP_URL:
        sys.exit(
            "ERROR: WEB_APP_URL is not set.\n"
            "Edit update_google_sheet.py and paste your Apps Script deployment URL."
        )
    if not SECRET_TOKEN:
        sys.exit(
            "ERROR: SECRET_TOKEN is not set.\n"
            "Edit update_google_sheet.py and set the same token as in antal_priorities_updater.gs."
        )


def _parse_response(resp, method):
    """Parse JSON from a response, printing helpful diagnostics on failure."""
    text = resp.text.strip()

    if not text:
        print(f"ERROR: {method} returned an empty response (HTTP {resp.status_code}).")
        print("Fix: Apps Script -> Deploy -> Manage deployments -> edit -> save new version.")
        sys.exit(1)

    if 'accounts.google.com' in text or 'signin' in text[:200].lower():
        print(f"ERROR: {method} redirected to Google sign-in (HTTP {resp.status_code}).")
        print("The deployment requires authentication. Fix:")
        print("  Apps Script -> Deploy -> Manage deployments")
        print("  -> edit the deployment -> set 'Who has access' to 'Anyone' -> deploy")
        sys.exit(1)

    try:
        return resp.json()
    except Exception:
        print(f"ERROR: {method} returned non-JSON (HTTP {resp.status_code}).")
        print("First 500 chars of response:")
        print(text[:500])
        print()
        print("Common causes:")
        print("  - Script has not been deployed (Deploy -> New deployment)")
        print("  - 'Who has access' is not set to 'Anyone'")
        print("  - There is a syntax error in antal_priorities_updater.gs")
        sys.exit(1)


def fetch_system_list():
    """GET the current system list from the Apps Script endpoint."""
    _check_config()
    resp = requests.get(WEB_APP_URL, params={'token': SECRET_TOKEN, 'sheet': SHEET_NAME}, timeout=30)
    resp.raise_for_status()
    data = _parse_response(resp, 'GET')
    if 'error' in data:
        sys.exit(f"Apps Script returned error: {data['error']}")
    systems = data['systems']
    # Honour the ---END marker that separates active systems from the rest of the sheet
    end = next((i for i, s in enumerate(systems) if s.strip() == '---END'), len(systems))
    return systems[:end]


def post_updates(systems_payload):
    """POST a list of system updates to the Apps Script endpoint."""
    _check_config()
    body = {
        'token':   SECRET_TOKEN,
        'sheet':   SHEET_NAME,
        'systems': systems_payload,
    }
    resp = requests.post(WEB_APP_URL, json=body, timeout=120)
    resp.raise_for_status()
    return _parse_response(resp, 'POST')


# ── Sync input.txt from sheet ─────────────────────────────────────────────────

def sync_input_txt(input_file='input.txt'):
    """
    Read the current system list from the Google Sheet and write it to input.txt
    so that auto_capture.py captures exactly the systems the sheet tracks.
    """
    print("Fetching system list from Google Sheet …")
    systems = fetch_system_list()
    with open(input_file, 'w', encoding='utf-8') as f:
        for name in systems:
            f.write(name + '\n')
    print(f"Wrote {len(systems)} systems to {input_file}")


# ── Main update logic ──────────────────────────────────────────────────────────

def update_sheet(system_map, data_timestamp, update_images=True, dry_run=False):
    # Format timestamp as ISO 8601 so Apps Script can parse it as a Date object,
    # which satisfies the date-validation rule on column C.
    if data_timestamp:
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', data_timestamp)
        ts_str = f"{m.group(1)}T{m.group(2)}:00Z" if m else datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        ts_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Build capture index map for images
    capture_index_map = build_capture_index_map() if update_images else {}

    # Fetch system list from the sheet (sheet is source of truth)
    print("Fetching system list from Google Sheet …")
    sheet_systems = fetch_system_list()
    print(f"  {len(sheet_systems)} systems in sheet")
    print()

    # Build the payload
    payload   = []
    unmatched = []

    for system_name in sheet_systems:
        sys_data = system_map.get(system_name.lower())
        if sys_data is None:
            unmatched.append(system_name)
            continue

        entry = {
            'name':      system_name,
            'timestamp': ts_str,
            'um':        sys_data['undermining'],
            'rf':        sys_data['reinforcement'],
        }

        if update_images:
            cap_idx = capture_index_map.get(system_name.lower())
            if cap_idx is not None:
                cropped_path = f'auto_capture/debug/cropped/capture_{cap_idx:03d}.png'
                if os.path.isfile(cropped_path):
                    b64, img_w, img_h = crop_cp_bar_b64(cropped_path)
                    if b64:
                        entry['bar_b64']    = b64
                        entry['bar_width']  = img_w
                        entry['bar_height'] = img_h

        payload.append(entry)

        has_img = 'bar_b64' in entry and entry['bar_b64']
        print(f"  {'[DRY]' if dry_run else '[OK] '} {system_name[:45]:<45} "
              f"UM={sys_data['undermining']:>8,}  RF={sys_data['reinforcement']:>8,}"
              + ("  [+img]" if has_img else ""))

    print()
    print(f"Matched: {len(payload)} / {len(sheet_systems)}")
    if unmatched:
        print(f"Not in capture ({len(unmatched)}): {', '.join(unmatched[:5])}"
              + (f' … +{len(unmatched) - 5}' if len(unmatched) > 5 else ''))

    if dry_run:
        print("\n(dry-run — no changes sent to the sheet)")
        return

    if not payload:
        print("Nothing to update.")
        return

    batches = [payload[i:i + POST_BATCH_SIZE] for i in range(0, len(payload), POST_BATCH_SIZE)]
    print(f"\nSending updates to Google Sheet in {len(batches)} batch(es) of ≤{POST_BATCH_SIZE} …")

    total_updated = 0
    all_not_found = []
    all_image_errors = []

    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)} ({len(batch)} systems) …", end=' ', flush=True)
        result = post_updates(batch)
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        else:
            n = result.get('updated', 0)
            total_updated += n
            print(f"ok ({n} updated)")
            all_not_found.extend(result.get('notFound') or [])
            all_image_errors.extend(result.get('imageErrors') or [])

    print(f"\nSheet updated: {total_updated} systems total")
    if all_not_found:
        print(f"Not found in sheet: {', '.join(all_not_found)}")
    if all_image_errors:
        print(f"Image errors:")
        for e in all_image_errors:
            print(f"  {e}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Update Antal Priorities Google Sheet from powerplay capture data'
    )
    parser.add_argument(
        '-c', '--capture',
        default='powerplay_auto_capture.txt',
        help='Capture file to read (default: powerplay_auto_capture.txt)'
    )
    parser.add_argument(
        '--sync-input',
        action='store_true',
        help='Write the sheet\'s current system list to input.txt, then exit'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Skip CP bar image updates'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would change without modifying the sheet'
    )
    args = parser.parse_args()

    if args.sync_input:
        sync_input_txt()
        return

    if not os.path.isfile(args.capture):
        sys.exit(f"ERROR: Capture file not found: {args.capture}")

    print(f"Reading capture data from {args.capture} …")
    data_timestamp, system_map = load_capture_data(args.capture)
    print(f"  {len(system_map)} systems loaded"
          + (f", timestamp: {data_timestamp}" if data_timestamp else ''))
    print()

    update_sheet(
        system_map,
        data_timestamp,
        update_images=not args.no_images,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
