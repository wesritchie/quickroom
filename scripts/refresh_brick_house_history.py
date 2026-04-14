#!/usr/bin/env python3
"""
Brick House Dashboard — Monthly Revenue History Refresh
=======================================================

Rebuilds the `storeData` and `MONTHS` constants in brick-house.html from
Dutchie POS transaction history. Powers the Overview "Combined Revenue by
Vendor" chart and the Period label.

Why a separate script:
  refresh_brick_house.py runs DAILY and updates inventory/market/product
  data (fast, current snapshot). This script runs MONTHLY and rebuilds
  the full revenue-by-vendor-by-month-by-store timeline from transactions
  — a much heavier query that doesn't need daily rerunning.

Run modes:
  (default)   Top-up: re-pull previous+current month, merge into existing
              storeData. Safe to rerun; idempotent per month.
  --backfill  Full rebuild: pull Jan 2025 → current month from scratch.
              Use when first deploying, after adding a new vendor slot,
              or if the historical data gets corrupted.
  --since YYYY-MM   Pull everything from that month forward.

Data source:
  Dutchie `reporting/transactions?includeDetail=true&includeLineItems=true`
  Each transaction has an `items` array. Each item has `vendor` (string)
  and `totalPrice`. We aggregate `totalPrice` per (store, month, vendor_key)
  using the same alias/classify logic as the inventory script, so brick
  vendors (fb/tb/gf/wf/bo/hp/mc/hb) are bucketed identically.

Filtering:
  - Skip isVoid=true transactions
  - Skip items where isReturned=true or isCoupon=true
  - Group by transactionDate (local), not lastModifiedDate
  - API window uses lastModifiedDateUTC — we pull wider than we need and
    post-filter by transactionDate to be safe against late edits

Output:
  MONTHS = ["Jan25","Feb25",...,"<current>"]
  storeData = { dracut: { "Jan25": {FB:n,TB:n,...HB:n}, ... }, ... }

Vendor keys in storeData use UPPERCASE to match existing chart code.
"""
import os
import re
import sys
import json
import time
import base64
import argparse
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date, timedelta
from collections import defaultdict

# Reuse canonical schema + helpers from the daily refresh script.
# Keeping one source of truth for vendor aliases prevents drift.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refresh_brick_house import (  # noqa: E402
    BRICK_VENDORS,
    VENDOR_ALIASES,
    EXTRA_BRICK_BRANDS,
    classify_brand,
    replace_js_const,
    HTML_FILE,
)

DUTCHIE_BASE = "https://api.pos.dutchie.com"
STORES = {
    "dracut":    os.environ.get("DUTCHIE_API_KEY_DRACUT", ""),
    "pepperell": os.environ.get("DUTCHIE_API_KEY_PEPPERELL", ""),
    "groton":    os.environ.get("DUTCHIE_API_KEY_GROTON", ""),
}

# Cloudflare 1010 blocks the default Python-urllib UA. A browser-like UA
# matches what `requests` sends and is accepted by Dutchie's edge.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

MAX_RETRIES = 3
RETRY_DELAY = 10

MONTH_ABBRS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


# ──────────────────────────────────────────────
# HTTP
# ──────────────────────────────────────────────
def dutchie_get(store_key, endpoint, params):
    """GET against Dutchie POS with retries. Returns parsed JSON or None."""
    api_key = STORES[store_key]
    if not api_key:
        print(f"  DUTCHIE_ERR store={store_key} endpoint={endpoint} reason=MISSING_API_KEY")
        return None
    auth = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    url = f"{DUTCHIE_BASE}/{endpoint}?" + urllib.parse.urlencode(params)

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            preview = (e.read() or b"")[:200].decode("utf-8", "replace").replace("\n", " ")
            print(f"  DUTCHIE_ERR store={store_key} endpoint={endpoint} attempt={attempt+1} "
                  f"status={e.code} preview={preview}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  DUTCHIE_RETRY store={store_key} endpoint={endpoint} "
                      f"attempt={attempt+1}/{MAX_RETRIES} err={type(e).__name__}:{e}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  DUTCHIE_FAIL store={store_key} endpoint={endpoint} "
                      f"err={type(e).__name__}:{e}")
                return None


def fetch_transactions_window(store_key, window_start, window_end):
    """Fetch all transactions whose lastModifiedDateUTC falls in the window.
    Chunks by day to stay under Dutchie's per-response cap and to keep each
    request small enough to retry cheaply.
    """
    all_txn = []
    cursor = window_start
    while cursor <= window_end:
        day_end = cursor + timedelta(days=1)
        if day_end > window_end + timedelta(days=1):
            day_end = window_end + timedelta(days=1)
        params = {
            "fromLastModifiedDateUTC": cursor.strftime("%Y-%m-%dT00:00:00Z"),
            "toLastModifiedDateUTC":   day_end.strftime("%Y-%m-%dT00:00:00Z"),
            "includeDetail": "true",
            "includeLineItems": "true",
        }
        data = dutchie_get(store_key, "reporting/transactions", params)
        if data is None:
            # Soft-fail: log and continue. The per-month summary will flag missing days.
            print(f"  TXN_MISSING store={store_key} day={cursor.isoformat()}")
        elif isinstance(data, list):
            all_txn.extend(data)
        cursor = day_end
    return all_txn


# ──────────────────────────────────────────────
# AGGREGATION
# ──────────────────────────────────────────────
def month_key(dt):
    """YYYY-MM-DD or ISO datetime → 'Jan25' style."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "").split(".")[0])
    return f"{MONTH_ABBRS[dt.month-1]}{str(dt.year)[2:]}"


def iter_months(start, end):
    """Yield month_key strings from start date to end date, inclusive."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield f"{MONTH_ABBRS[m-1]}{str(y)[2:]}"
        m += 1
        if m == 13:
            m = 1
            y += 1


def classify_item_vendor(item_vendor_str):
    """Line-item `vendor` string → brick vendor key (fb/tb/...) or None.

    Reuses classify_brand() from refresh_brick_house.py. We only care about
    'brick_tab' matches here — extra-brick and core vendors aren't charted
    on the Overview line graph. If you want Green Harbor to have its own
    line, add a `gh:` entry to VENDORS + vendorAliases in brick-house.html
    and this will pick it up automatically via BRICK_VENDORS.
    """
    kind, vk = classify_brand(item_vendor_str, vendor_name=item_vendor_str)
    return vk if kind == "brick_tab" else None


def aggregate_month(transactions, target_month_key):
    """Sum line-item totalPrice per brick vendor code for transactions whose
    transactionDate falls in target_month_key. Returns dict {vendor_key_upper: int}.
    """
    totals = defaultdict(float)
    seen_txn = 0
    kept_txn = 0
    for txn in transactions:
        if txn.get("isVoid"):
            continue
        tx_date_str = txn.get("transactionDate") or txn.get("transactionDateLocalTime")
        if not tx_date_str:
            continue
        if month_key(tx_date_str) != target_month_key:
            continue
        seen_txn += 1
        items = txn.get("items") or []
        if not items:
            continue
        kept_txn += 1
        for it in items:
            if it.get("isReturned") or it.get("isCoupon"):
                continue
            vk = classify_item_vendor(it.get("vendor", ""))
            if not vk:
                continue
            price = it.get("totalPrice")
            if price is None:
                continue
            totals[vk.upper()] += float(price)
    return {k: int(round(v)) for k, v in totals.items()}, seen_txn, kept_txn


# ──────────────────────────────────────────────
# HTML I/O
# ──────────────────────────────────────────────
def read_existing_store_data(html):
    """Best-effort parse the current storeData JS object. Used for merging
    in top-up mode. If parsing fails, return empty dict — caller should
    then decide whether to abort or rebuild from scratch.
    """
    m = re.search(r"const\s+storeData\s*=\s*\{", html)
    if not m:
        return {}
    # Strip JS-style property names (unquoted identifiers like `dracut:`) to JSON.
    # This is a pragmatic parser — storeData is a simple nested structure with
    # string/number values only, so we can safely coerce it.
    start = m.end() - 1
    depth, i = 0, start
    while i < len(html):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    else:
        return {}
    raw = html[start:end]
    # Quote bare keys: dracut: → "dracut":  /  Jan25: → "Jan25":  /  FB: → "FB":
    raw_json = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', raw)
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"  WARN could not parse existing storeData: {e}")
        return {}


def render_store_data_js(store_data, months):
    """Render storeData dict → pretty JS matching the hand-authored style."""
    lines = ["{"]
    for store_key in ("dracut", "pepperell", "groton"):
        if store_key not in store_data:
            continue
        lines.append(f"    {store_key}: {{")
        for mk in months:
            entry = store_data[store_key].get(mk, {})
            if not entry:
                lines.append(f'        "{mk}":{{}},')
                continue
            parts = ",".join(f"{vk}:{v}" for vk, v in entry.items())
            lines.append(f'        "{mk}":{{{parts}}},')
        # Trim trailing comma on last entry
        if lines[-1].endswith(","):
            lines[-1] = lines[-1][:-1]
        lines.append("    },")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")
    return "\n".join(lines)


def render_months_js(months):
    return "[" + ",".join(f'"{m}"' for m in months) + "]"


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def parse_args():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--backfill", action="store_true",
                   help="Rebuild from Jan 2025 to current month")
    g.add_argument("--since", metavar="YYYY-MM",
                   help="Pull from this month forward (e.g. 2025-07)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print results but don't write HTML")
    return ap.parse_args()


def main():
    args = parse_args()
    missing = [f"DUTCHIE_API_KEY_{k.upper()}" for k, v in STORES.items() if not v]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    today = date.today()
    # Only render completed months. The current month is partial and would
    # show a misleading drop on the Overview chart. We still pull the
    # current month window so late-arriving transactions get captured when
    # the month closes, but we exclude it from the rendered output.
    if today.month == 1:
        last_completed = date(today.year - 1, 12, 1)
    else:
        last_completed = date(today.year, today.month - 1, 1)

    if args.backfill:
        start_month = date(2025, 1, 1)
    elif args.since:
        y, m = [int(x) for x in args.since.split("-")]
        start_month = date(y, m, 1)
    else:
        # Monthly top-up: re-pull last-completed + the month before it
        # (catches any late-edited transactions). On May 1 cron, that's
        # March + April. Only April goes into the chart as newly completed.
        if last_completed.month == 1:
            start_month = date(last_completed.year - 1, 12, 1)
        else:
            start_month = date(last_completed.year, last_completed.month - 1, 1)

    end_month = last_completed
    months_to_pull = list(iter_months(start_month, end_month))
    # API lastModified window: start of first month, end of today (inclusive)
    window_start = start_month
    window_end = today

    print(f"\n=== Brick House history refresh ===")
    print(f"Mode:   {'backfill' if args.backfill else ('since '+args.since if args.since else 'top-up')}")
    print(f"Months: {months_to_pull[0]} → {months_to_pull[-1]} ({len(months_to_pull)} months)")
    print(f"API window (lastModified): {window_start} → {window_end}")
    print(f"Stores: {', '.join(STORES)}")
    print()

    # Pull all transactions per store across the full window, then aggregate
    # per month. This is cheaper than pulling month-by-month because a single
    # late-edited transaction would otherwise slip through the cracks.
    new_store_data = {}
    for store_key in STORES:
        print(f"─── {store_key} ───")
        t0 = time.time()
        txns = fetch_transactions_window(store_key, window_start, window_end)
        elapsed = time.time() - t0
        print(f"  fetched {len(txns)} transactions in {elapsed:.1f}s")
        new_store_data[store_key] = {}
        for mk in months_to_pull:
            totals, seen, kept = aggregate_month(txns, mk)
            new_store_data[store_key][mk] = totals
            total_rev = sum(totals.values())
            print(f"  {mk}: txn_in_month={seen:>5d} with_items={kept:>5d} "
                  f"revenue=${total_rev:>10,.0f} vendors={len(totals)}")

    # In top-up mode, merge into existing storeData so older months stay.
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    if args.backfill:
        merged = new_store_data
        all_months = months_to_pull
    else:
        existing = read_existing_store_data(html)
        merged = existing or {}
        for sk, months_dict in new_store_data.items():
            merged.setdefault(sk, {})
            for mk, totals in months_dict.items():
                merged[sk][mk] = totals
        # Union of existing + new months, chronologically sorted
        all_months_set = set(months_to_pull)
        for sk in merged:
            all_months_set.update(merged[sk].keys())
        all_months = sorted(all_months_set, key=lambda mk: (int(mk[-2:]), MONTH_ABBRS.index(mk[:3])))

    # Prune any month after last_completed (e.g. a partial current month
    # left over from a prior run). This keeps the Overview chart from
    # showing an artificial drop at the right edge.
    last_key = month_key(datetime(last_completed.year, last_completed.month, 1))
    last_idx = (last_completed.year, last_completed.month)
    def _mk_tuple(mk):
        yy = 2000 + int(mk[-2:])
        mm = MONTH_ABBRS.index(mk[:3]) + 1
        return (yy, mm)
    dropped = [mk for mk in all_months if _mk_tuple(mk) > last_idx]
    if dropped:
        print(f"Pruning partial/future months from output: {dropped}")
    all_months = [mk for mk in all_months if _mk_tuple(mk) <= last_idx]
    for sk in merged:
        for mk in dropped:
            merged[sk].pop(mk, None)

    print(f"\nTotal months in output: {len(all_months)} ({all_months[0]} → {all_months[-1]})")

    if args.dry_run:
        print("\n--dry-run specified; not writing HTML.")
        return

    new_store_data_js = render_store_data_js(merged, all_months)
    new_months_js = render_months_js(all_months)

    html = replace_js_const(html, "storeData", new_store_data_js, is_array=False)
    html = replace_js_const(html, "MONTHS", new_months_js, is_array=True)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nWrote {HTML_FILE}")
    print(f"  storeData: {len(merged)} stores, {len(all_months)} months")
    print(f"  MONTHS:    {all_months}")


if __name__ == "__main__":
    main()
