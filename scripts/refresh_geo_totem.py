#!/usr/bin/env python3
"""
Geo Totem Dashboard — Daily Data Refresh
Pulls Veriscan ID-scan data and updates geo-totem.html with fresh DATA, META, TREND, and CITY_TREND_STORE.
Runs as a GitHub Action on schedule.
"""

import os
import re
import json
import math
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
VERISCAN_BASE = "https://public.veriscancloud.com"
VERISCAN_TOKEN = os.environ.get("VERISCAN_TOKEN", "")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(REPO_ROOT, "geo-totem.html")

STORE_MAP = {
    "Dracut, MA": "dracut",
    "Pepperell - THCC": "pepperell",
    "GD-Groton Dispensary": "groton",
}

# Top cities tracked per store (must match the dashboard's existing city lists)
TRACKED_CITIES = {
    "dracut": [
        "METHUEN, MA", "MANCHESTER, NH", "SALEM, NH", "DERRY, NH",
        "LAWRENCE, MA", "LONDONDERRY, NH", "PELHAM, NH", "DRACUT, MA",
        "WINDHAM, NH", "UNKNOWN, USA", "LOWELL, MA", "CONCORD, NH"
    ],
    "pepperell": [
        "PEPPERELL, MA", "NASHUA, NH", "FITCHBURG, MA", "TOWNSEND, MA",
        "LEOMINSTER, MA", "LUNENBURG, MA", "GROTON, MA", "AYER, MA",
        "HOLLIS, NH", "MILFORD, NH", "GARDNER, MA", "UNKNOWN, USA"
    ],
    "groton": [
        "GROTON, MA", "PEPPERELL, MA", "AYER, MA", "TOWNSEND, MA",
        "LUNENBURG, MA", "FITCHBURG, MA", "LEOMINSTER, MA", "SHIRLEY, MA",
        "WESTFORD, MA", "LITTLETON, MA", "NASHUA, NH", "UNKNOWN, USA"
    ],
}

MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds


# ──────────────────────────────────────────────
# API HELPERS
# ──────────────────────────────────────────────
def veriscan_fetch(from_dt, to_dt):
    """Fetch all Veriscan history records for a date range, paginating."""
    headers = {
        "Authorization": f"Bearer {VERISCAN_TOKEN}",
        "Accept": "application/json",
    }
    all_items = []
    page = 1
    while True:
        params = {
            "From": from_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "To": to_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "PageSize": 400,
            "Page": page,
        }
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    f"{VERISCAN_BASE}/History",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"  Retry {attempt+1}/{MAX_RETRIES} for page {page}: {e}")
                    import time; time.sleep(RETRY_DELAY)
                else:
                    raise RuntimeError(f"Failed after {MAX_RETRIES} retries on page {page}: {e}")

        items = data.get("items", [])
        all_items.extend(items)
        if page >= data.get("totalPages", 1):
            break
        page += 1

    print(f"  Fetched {len(all_items)} records for {from_dt.date()} to {to_dt.date()}")
    return all_items


def classify_record(record):
    """Extract store key, city key, and state from a Veriscan record."""
    location = record.get("locationName", "")
    store = STORE_MAP.get(location)

    city = (record.get("city") or "").strip().upper()
    state = (record.get("jurisdictionCode") or "").strip().upper()
    if not city:
        city_key = "UNKNOWN, USA"
    elif state:
        city_key = f"{city}, {state}"
    else:
        city_key = f"{city}, USA"

    # Normalize state to MA, NH, or OTHER
    if state == "MA":
        state_bucket = "MA"
    elif state == "NH":
        state_bucket = "NH"
    else:
        state_bucket = "OTHER"

    return store, city_key, state_bucket


# ──────────────────────────────────────────────
# DATA AGGREGATION
# ──────────────────────────────────────────────
def aggregate_period(records):
    """Aggregate a list of Veriscan records into the DATA period shape."""
    total = len(records)
    by_store = defaultdict(int)
    by_state = defaultdict(int)
    by_store_by_state = defaultdict(lambda: defaultdict(int))
    city_counts_by_store = defaultdict(lambda: defaultdict(int))
    all_cities = set()

    for r in records:
        store, city_key, state_bucket = classify_record(r)
        if not store:
            continue
        by_store[store] += 1
        by_state[state_bucket] += 1
        by_store_by_state[store][state_bucket] += 1
        city_counts_by_store[store][city_key] += 1
        all_cities.add(city_key)

    # Build topCities per store (top 12)
    top_cities = {}
    for store_key in ["dracut", "pepperell", "groton"]:
        store_total = by_store.get(store_key, 0)
        counts = city_counts_by_store.get(store_key, {})
        sorted_cities = sorted(counts.items(), key=lambda x: -x[1])[:12]
        top_cities[store_key] = [
            {
                "rank": i + 1,
                "name": name,
                "count": count,
                "pct": f"{count/store_total*100:.1f}" if store_total > 0 else "0.0",
            }
            for i, (name, count) in enumerate(sorted_cities)
        ]

    return {
        "total": total,
        "uniqueCities": len(all_cities),
        "byStore": dict(by_store),
        "byState": dict(by_state),
        "byStoreByState": {k: dict(v) for k, v in by_store_by_state.items()},
        "topCities": top_cities,
    }


def aggregate_city_trend_week(records, store_key):
    """Aggregate records for a single store's weekly city trend entry."""
    total = len([r for r in records if STORE_MAP.get(r.get("locationName")) == store_key])
    city_counts = defaultdict(int)
    for r in records:
        store, city_key, _ = classify_record(r)
        if store != store_key:
            continue
        city_counts[city_key] += 1

    tracked = TRACKED_CITIES.get(store_key, [])
    cities_dict = {c: city_counts.get(c, 0) for c in tracked}
    return {"total": total, "cities": cities_dict}


# ──────────────────────────────────────────────
# DATE HELPERS
# ──────────────────────────────────────────────
def compute_date_anchors(today):
    """Compute all date ranges needed for the refresh."""
    yesterday = today - timedelta(days=1)

    # Last completed Mon-Sun week
    dow = today.weekday()  # Mon=0, Sun=6
    days_since_monday = dow
    if days_since_monday == 0:
        # Today is Monday — last completed week is the previous Mon-Sun
        last_sunday = yesterday
        last_monday = last_sunday - timedelta(days=6)
    else:
        last_sunday = today - timedelta(days=dow)
        last_monday = last_sunday - timedelta(days=6)

    month_start = today.replace(day=1)

    return {
        "today": today,
        "yesterday": yesterday,
        "last_monday": last_monday,
        "last_sunday": last_sunday,
        "month_start": month_start,
    }


def format_week_label(monday, sunday):
    """Format week label like 'Mar 30-Apr 5' or 'Apr 7-13'."""
    if monday.month == sunday.month:
        return f"{monday.strftime('%b')} {monday.day}\u2013{sunday.day}"
    else:
        return f"{monday.strftime('%b')} {monday.day}\u2013{sunday.strftime('%b')} {sunday.day}"


def format_month_label(dt):
    """Format month label like 'Apr 26'."""
    return f"{dt.strftime('%b')} {str(dt.year)[2:]}"


# ──────────────────────────────────────────────
# HTML UPDATE
# ──────────────────────────────────────────────
def json_dumps_compact(obj, indent=None):
    """Compact JSON serialization with no trailing spaces."""
    return json.dumps(obj, separators=(",", ":") if indent is None else (",", ": "), indent=indent, ensure_ascii=True)


def replace_js_const(html, const_name, new_value_str, is_array=False):
    """Replace a JavaScript const block in the HTML.
    Handles both object ({...}) and array ([...]) constants.
    """
    open_char = r"\[" if is_array else r"\{"
    close_char = "]" if is_array else "}"

    # Match: const NAME = { ... }; or const NAME = [ ... ];
    # Use a brace/bracket counting approach for reliability
    pattern = rf"(const\s+{const_name}\s*=\s*)"
    match = re.search(pattern, html)
    if not match:
        raise ValueError(f"Could not find 'const {const_name}' in HTML")

    start = match.start()
    value_start = match.end()

    # Find the matching closing brace/bracket
    depth = 0
    in_string = False
    escape_next = False
    open_c = "[" if is_array else "{"
    close_c = close_char
    i = value_start

    for i in range(value_start, len(html)):
        c = html[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                break

    end = i + 1
    # Include trailing semicolon if present
    if end < len(html) and html[end] == ";":
        end += 1

    replacement = f"{match.group(1)}{new_value_str};"
    return html[:start] + replacement + html[end:]


def build_meta(dates, week_label, trend):
    """Build the META constant.

    monthLabel and trendLabel always reference the LAST COMPLETED month.
    We still include the in-progress (proj) entry as the last element of trend
    for chart rendering, but the user-facing text labels anchor on completed data
    so the dashboard never says 'Apr 26' on April 13 (confusing, looks stale).
    """
    yesterday = dates["yesterday"]
    today = dates["today"]
    month_start = dates["month_start"]

    # Last COMPLETED month = day before the current month_start
    last_completed_month_dt = month_start - timedelta(days=1)
    last_completed_label = format_month_label(last_completed_month_dt)  # e.g. "Mar 26"

    # Trend range: first entry label to last COMPLETED month
    # (ignore any trailing '(proj)' entry for labeling purposes)
    trend_start = trend[0]["label"] if trend else "?"

    # City window end = last_sunday formatted
    city_end = dates["last_sunday"].strftime("%b %d, %Y").replace(" 0", " ")

    # Previous week for movers comparison
    prev_monday = dates["last_monday"] - timedelta(days=7)
    prev_sunday = dates["last_sunday"] - timedelta(days=7)

    return {
        "generatedAt": today.strftime("%Y-%m-%d"),
        "asOfDate": yesterday.strftime("%b %d, %Y").replace(" 0", " ").replace("  ", " "),
        "yesterdayDate": yesterday.strftime("%b %-d"),
        "weekLabel": week_label,
        "monthLabel": last_completed_label,
        "trendLabel": f"{trend_start} \\u2013 {last_completed_label}",
        "cityWindowEnd": city_end,
        "cityWindowWeeks": 12,
        "moversCurrent": week_label,
        "moversPrior": format_week_label(prev_monday, prev_sunday),
    }


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    if not VERISCAN_TOKEN:
        raise RuntimeError("VERISCAN_TOKEN environment variable is required")

    # Read current HTML
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Parse existing TREND to preserve history
    trend_match = re.search(r"const\s+TREND\s*=\s*(\[[\s\S]*?\]);", html)
    if not trend_match:
        raise RuntimeError("Could not parse existing TREND from HTML")
    # Use a safer approach: extract and eval-like parse
    existing_trend = json.loads(
        re.sub(r"(\w+):", r'"\1":', trend_match.group(1))
        .replace("'", '"')
    )

    # Parse existing CITY_TREND_STORE to preserve history
    # We'll handle this with regex extraction per store

    today = datetime.now(timezone.utc).date()
    # Convert to naive date for arithmetic
    from datetime import date
    today = date.today()

    dates = compute_date_anchors(today)
    yesterday = dates["yesterday"]
    last_monday = dates["last_monday"]
    last_sunday = dates["last_sunday"]
    month_start = dates["month_start"]
    week_label = format_week_label(last_monday, last_sunday)
    month_label = format_month_label(today)

    print(f"=== Geo Totem Refresh — {today} ===")
    print(f"  Yesterday: {yesterday}")
    print(f"  Week: {last_monday} to {last_sunday} ({week_label})")
    print(f"  Month: {month_start} to {yesterday}")

    # ── STEP 1: Fetch yesterday's data ──
    print("\n[1/4] Fetching yesterday's data...")
    yesterday_start = datetime.combine(yesterday, datetime.min.time())
    yesterday_end = datetime.combine(yesterday, datetime.max.time())
    yesterday_records = veriscan_fetch(yesterday_start, yesterday_end)
    yesterday_data = aggregate_period(yesterday_records)

    # ── STEP 2: Fetch week data ──
    print("[2/4] Fetching weekly data...")
    week_start = datetime.combine(last_monday, datetime.min.time())
    week_end = datetime.combine(last_sunday, datetime.max.time())
    week_records = veriscan_fetch(week_start, week_end)
    week_data = aggregate_period(week_records)

    # ── STEP 3: Fetch month-to-date data ──
    print("[3/4] Fetching month-to-date data...")
    month_dt_start = datetime.combine(month_start, datetime.min.time())
    month_dt_end = datetime.combine(yesterday, datetime.max.time())
    month_records = veriscan_fetch(month_dt_start, month_dt_end)
    month_data = aggregate_period(month_records)

    # ── STEP 4: Update TREND (monthly projection) ──
    print("[4/4] Computing monthly projection and updating TREND...")
    days_elapsed = (yesterday - month_start).days + 1
    # Project to 30-day month
    factor = 30 / max(days_elapsed, 1)

    trend_entry = {
        "label": f"{month_label} (proj)",
        "total": round(month_data["total"] * factor),
        "byState": {
            "MA": round(month_data["byState"].get("MA", 0) * factor),
            "NH": round(month_data["byState"].get("NH", 0) * factor),
            "OTHER": round(month_data["byState"].get("OTHER", 0) * factor),
        },
        "byStore": {
            "dracut": round(month_data["byStore"].get("dracut", 0) * factor),
            "pepperell": round(month_data["byStore"].get("pepperell", 0) * factor),
            "groton": round(month_data["byStore"].get("groton", 0) * factor),
        },
    }

    # Update or append the current month's projection
    current_month_prefix = month_label  # e.g., "Apr 26"
    updated = False
    for i, entry in enumerate(existing_trend):
        if entry["label"].startswith(current_month_prefix):
            existing_trend[i] = trend_entry
            updated = True
            break
    if not updated:
        existing_trend.append(trend_entry)
        if len(existing_trend) > 18:
            existing_trend.pop(0)

    # ── STEP 5: Update CITY_TREND_STORE weekly rollover ──
    # Check if this week already exists
    # Parse existing weeks from HTML for each store
    city_trend_match = re.search(
        r"const\s+CITY_TREND_STORE\s*=\s*(\{[\s\S]*?\});\s*(?=\n\s*//|const\s)",
        html
    )
    if city_trend_match:
        # We need to check if the current week_label is already in the data
        if f'"{week_label}"' not in html and week_label not in html:
            print(f"  Adding new week to CITY_TREND_STORE: {week_label}")
            # Build new week entry for each store
            new_city_weeks = {}
            for store_key in ["dracut", "pepperell", "groton"]:
                new_city_weeks[store_key] = aggregate_city_trend_week(week_records, store_key)
                new_city_weeks[store_key]["label"] = week_label
            # We'll inject this when we rebuild the constant
        else:
            print(f"  Week {week_label} already present in CITY_TREND_STORE, skipping rollover")
            new_city_weeks = None
    else:
        print("  WARNING: Could not parse CITY_TREND_STORE")
        new_city_weeks = None

    # ── BUILD DATA CONSTANT ──
    data_obj = {
        "yesterday": yesterday_data,
        "week": week_data,
        "month": month_data,
    }

    # ── BUILD META CONSTANT ──
    meta_obj = build_meta(dates, week_label, existing_trend)

    # ── SERIALIZE AND REPLACE ──
    print("\nUpdating HTML file...")

    # Replace META (or insert before DATA if it doesn't exist yet)
    meta_str = json.dumps(meta_obj, indent=2, ensure_ascii=True)
    if re.search(r"const\s+META\s*=", html):
        html = replace_js_const(html, "META", meta_str)
    else:
        # Insert META block before const DATA
        data_match = re.search(r"(\n[ \t]*)const\s+DATA\s*=", html)
        if data_match:
            indent = data_match.group(1)
            insertion = f"{indent}const META = {meta_str};\n"
            html = html[:data_match.start()] + "\n" + insertion + html[data_match.start():]
            print("  Injected new const META before const DATA")
        else:
            raise ValueError("Could not find const DATA to anchor META injection")

    # Replace DATA
    data_str = json.dumps(data_obj, indent=2, ensure_ascii=True)
    html = replace_js_const(html, "DATA", data_str)

    # Replace TREND
    trend_str = json.dumps(existing_trend, indent=2, ensure_ascii=True)
    html = replace_js_const(html, "TREND", trend_str, is_array=True)

    # Update CITY_TREND_STORE if we have a new week
    if new_city_weeks:
        # Parse existing CITY_TREND_STORE, add new week to each store, trim to 12
        # For simplicity, we'll do targeted string insertion
        for store_key in ["dracut", "pepperell", "groton"]:
            new_week_json = json.dumps(new_city_weeks[store_key], ensure_ascii=True)
            # Find the store's weeks array and append
            # Pattern: after the last entry in weeks array for this store
            store_pattern = rf'("{store_key}":\s*\{{[^}}]*?"weeks":\s*\[)'
            store_match = re.search(store_pattern, html, re.DOTALL)
            if store_match:
                # Find the closing ] of the weeks array
                weeks_start = store_match.end()
                bracket_depth = 1
                pos = weeks_start
                while pos < len(html) and bracket_depth > 0:
                    if html[pos] == "[":
                        bracket_depth += 1
                    elif html[pos] == "]":
                        bracket_depth -= 1
                    pos += 1
                weeks_end = pos - 1  # position of the closing ]

                # Insert new week before the closing ]
                insert_pos = weeks_end
                # Check if there's content before (need a comma)
                before = html[weeks_start:insert_pos].strip()
                if before:
                    new_content = f",\n      {new_week_json}"
                else:
                    new_content = f"\n      {new_week_json}"

                html = html[:insert_pos] + new_content + html[insert_pos:]

    # Write updated HTML
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDone! Updated {HTML_FILE}")
    print(f"  Yesterday: {yesterday_data['total']} scans")
    print(f"  Week: {week_data['total']} scans")
    print(f"  Month: {month_data['total']} scans")
    print(f"  Trend projection: {trend_entry['total']} scans/month")


if __name__ == "__main__":
    main()
