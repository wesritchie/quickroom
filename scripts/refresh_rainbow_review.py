#!/usr/bin/env python3
"""
Rainbow Review Dashboard - Daily Data Refresh
Pulls all data the dashboard needs via the existing Apps Script proxy
(which already handles Dutchie + Lit Alerts auth server-side) and writes
it to rainbow-review-data.js as a pre-baked snapshot consumed by
loadFromPrebaked() in rainbow-review.html.

Runs as a GitHub Action on schedule - replaces the old Cowork
scheduled task that relied on Chrome MCP + window.name bridge.

Data shape produced matches exactly what loadFromPrebaked() expects:

  window.__PREBAKED_DATA__ = {
    buildTime: ISO timestamp,
    dutchie:   { daily, weekly, monthly, lastMonth } x { dracut, pepperell, groton },
    litAlerts: { daily, weekly, monthly, lastMonth } x { retailers, categories },
    products:  { "<storeId>": { data: [...] } } for all 14 stores,
    trend24m:  { market: [...], thStores: {...}, compStores: {...} }
  }
"""

import os
import re
import json
import time
import traceback
import urllib.parse
import requests
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------
PROXY_URL = "https://script.google.com/macros/s/AKfycbwa5m4itefDQbw9jhfm4RlMMF61K1oy4CCqIosHZQkXPdCIVNK8mgN3KxAMLBkbNIE4/exec"
STATE = "MA"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(REPO_ROOT, "rainbow-review.html")
DATA_FILE = os.path.join(REPO_ROOT, "rainbow-review-data.js")

MAX_RETRIES = 3
RETRY_DELAY = 30         # seconds between retries
REQUEST_TIMEOUT = 60     # seconds per HTTP call
BATCH_WORKERS = 6        # parallelism for store-level calls


# --------------------------------------------------------------
# STORE SCHEMA - parsed from rainbow-review.html so the HTML is the
# single source of truth. If new competitors get added to the HTML
# CONFIG.REGIONS block, the refresh picks them up automatically.
# --------------------------------------------------------------
def _load_store_schema():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # TH_STORES: 3 Tree House stores - (name, litId, laName)
    th_block = re.search(r"TH_STORES\s*:\s*\[(.*?)\]", html, re.DOTALL)
    if not th_block:
        raise RuntimeError("Could not find TH_STORES in rainbow-review.html")
    th_stores = []
    for m in re.finditer(
        r"\{\s*name:\s*'([^']+)'\s*,\s*id:\s*(\d+)\s*,\s*laName:\s*'([^']+)'\s*\}",
        th_block.group(1),
    ):
        th_stores.append({"name": m.group(1), "id": int(m.group(2)), "laName": m.group(3)})
    if len(th_stores) != 3:
        raise RuntimeError(f"Expected 3 TH stores, got {len(th_stores)}: {th_stores}")

    # REGIONS: competitors grouped by district - parse each region's comps[]
    comps = []
    regions_block = re.search(r"REGIONS\s*:\s*\{(.*?)\n\s*\}\s*,\s*CATEGORIES", html, re.DOTALL)
    if not regions_block:
        raise RuntimeError("Could not find REGIONS in rainbow-review.html")
    for region_match in re.finditer(
        r"(\w+)\s*:\s*\{\s*th:\s*\{[^}]+\}\s*,\s*comps:\s*\[(.*?)\]\s*\}",
        regions_block.group(1),
        re.DOTALL,
    ):
        region = region_match.group(1)
        for m in re.finditer(
            r"\{\s*name:\s*'([^']+)'\s*,\s*id:\s*(\d+)\s*\}",
            region_match.group(2),
        ):
            comps.append({"name": m.group(1), "id": int(m.group(2)), "region": region})
    if len(comps) < 8:
        raise RuntimeError(f"Expected >=8 competitor stores, got {len(comps)}: {comps}")

    # Dutchie store keys - map Lit Alerts ID to internal Dutchie proxy key
    lit_to_dutchie = {}
    for m in re.finditer(r"LIT_TO_DUTCHIE\s*=\s*\{([^}]+)\}", html):
        for km in re.finditer(r"(\d+):\s*'(\w+)'", m.group(1)):
            lit_to_dutchie[int(km.group(1))] = km.group(2)

    return th_stores, comps, lit_to_dutchie


# --------------------------------------------------------------
# DATE RANGES - mirrors getDateRanges() in the HTML
# --------------------------------------------------------------
def _mmddyyyy(d):
    return d.strftime("%m-%d-%Y")


def _fmt_label_range(begin, end):
    # Simple label - the HTML will re-render labels on load anyway
    return f"{begin.strftime('%b %d')} - {end.strftime('%b %d')}"


def _get_date_ranges():
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 7-day window ending yesterday
    weekly_begin = yesterday - timedelta(days=6)

    # Month-to-date: 1st of current month -> yesterday
    monthly_begin = date(today.year, today.month, 1)

    # Last complete month
    if today.month == 1:
        lm_year, lm_month = today.year - 1, 12
    else:
        lm_year, lm_month = today.year, today.month - 1
    last_month_begin = date(lm_year, lm_month, 1)
    if lm_month == 12:
        next_month_first = date(lm_year + 1, 1, 1)
    else:
        next_month_first = date(lm_year, lm_month + 1, 1)
    last_month_end = next_month_first - timedelta(days=1)

    # 30-day trend, last-month trend, 24-month trend
    trend30_begin = today - timedelta(days=30)

    return {
        "daily":      {"begin": yesterday,         "end": yesterday,          "label": yesterday.strftime("%b %d")},
        "weekly":     {"begin": weekly_begin,      "end": yesterday,          "label": _fmt_label_range(weekly_begin, yesterday)},
        "monthly":    {"begin": monthly_begin,     "end": yesterday,          "label": _fmt_label_range(monthly_begin, yesterday)},
        "lastMonth":  {"begin": last_month_begin,  "end": last_month_end,     "label": last_month_begin.strftime("%B %Y")},
        "trend30":    {"begin": trend30_begin,     "end": yesterday},
        "trendLastMonth": {"begin": last_month_begin, "end": last_month_end},
    }


# --------------------------------------------------------------
# PROXY FETCH - equivalent to the browser's apiFetch()/safeFetch()
# --------------------------------------------------------------
_session = requests.Session()


def proxy_fetch(path, params=None, *, include_state=True, include_dollar_values=True):
    """Call the Apps Script proxy. Returns parsed JSON, or None on failure.
    Mirrors the browser's apiFetch(): adds state=MA and returnDollarValues=true
    to every call that goes through /market/* or /retailer/*."""
    qs = {"path": path}
    if include_state:
        qs["state"] = STATE
    if include_dollar_values:
        qs["returnDollarValues"] = "true"
    if params:
        for k, v in params.items():
            if isinstance(v, date):
                qs[k] = _mmddyyyy(v)
            else:
                qs[k] = v

    url = PROXY_URL + "?" + urllib.parse.urlencode(qs)

    for attempt in range(MAX_RETRIES):
        try:
            resp = _session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code >= 400:
                preview = (resp.text or "")[:200].replace("\n", " ")
                print(f"  PROXY_ERR path={path} attempt={attempt+1} status={resp.status_code} preview={preview}")
                resp.raise_for_status()
            body = resp.json()
            if isinstance(body, dict) and body.get("error"):
                print(f"  PROXY_APP_ERR path={path} err={body['error']}")
                return None
            return body
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  PROXY_RETRY path={path} attempt={attempt+1}/{MAX_RETRIES} err={type(e).__name__}:{e}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  PROXY_FAIL path={path} err={type(e).__name__}:{e}")
                return None


# --------------------------------------------------------------
# SECTION FETCHERS
# --------------------------------------------------------------
def fetch_dutchie_periods(ranges):
    """4 period totals x 3 TH stores via /dutchie/all-stores-summary.
    Returns { daily: {dracut,pepperell,groton}, weekly: {...}, ... }"""
    print("\n[1/4] Dutchie period totals (4 periods, 1 call each)...")
    dutchie = {"daily": {}, "weekly": {}, "monthly": {}, "lastMonth": {}}
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        r = ranges[period]
        print(f"  {period}: {r['begin']} to {r['end']}")
        # Proxy expects ISO dates on /dutchie/all-stores-summary
        data = proxy_fetch("/dutchie/all-stores-summary", {
            "startDate": r["begin"].strftime("%Y-%m-%d"),
            "endDate":   r["end"].strftime("%Y-%m-%d"),
        }, include_state=False, include_dollar_values=False)
        if data and isinstance(data, dict) and data.get("stores"):
            # Expected shape: { stores: { dracut: {...}, pepperell: {...}, groton: {...} } }
            dutchie[period] = data["stores"]
            print(f"    OK - stores: {list(data['stores'].keys())}")
        else:
            print(f"    MISS - data was {type(data).__name__}")
    return dutchie


def fetch_lit_alerts_periods(ranges):
    """4 periods x (market/retailers, market/categories). Returns
    { daily: {retailers, categories}, weekly: {...}, ... }"""
    print("\n[2/4] Lit Alerts market data (4 periods x 2 endpoints)...")
    lit = {"daily": {}, "weekly": {}, "monthly": {}, "lastMonth": {}}
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        r = ranges[period]
        print(f"  {period}: {r['begin']} to {r['end']}")
        retailers = proxy_fetch("/market/retailers", {
            "beginDate": r["begin"],
            "endDate":   r["end"],
        })
        categories = proxy_fetch("/market/categories", {
            "beginDate": r["begin"],
            "endDate":   r["end"],
        })
        lit[period]["retailers"] = retailers or {"results": []}
        lit[period]["categories"] = categories or {"results": []}
        rc = len((retailers or {}).get("results", []) or [])
        cc = len((categories or {}).get("results", []) or [])
        print(f"    retailers={rc}, categories={cc}")
    return lit


def fetch_all_products(all_store_ids):
    """Products for all 14 stores via /retailers/{id}/products (plural path).
    Returns { "<id>": { data: [...] } } keyed by string ID."""
    print(f"\n[3/4] Products for {len(all_store_ids)} stores (parallel)...")
    results = {}

    def _one(sid):
        body = proxy_fetch(f"/retailers/{sid}/products")
        if body is None:
            return sid, None
        # Normalize to {data: [...]} - the HTML handles both shapes on load,
        # but we pick one consistent form here.
        if isinstance(body, list):
            return sid, {"data": body}
        if isinstance(body, dict) and "data" in body:
            return sid, {"data": body["data"] or []}
        if isinstance(body, dict) and "results" in body:
            return sid, {"data": body["results"] or []}
        return sid, {"data": []}

    with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as ex:
        futures = [ex.submit(_one, sid) for sid in all_store_ids]
        for f in as_completed(futures):
            sid, payload = f.result()
            if payload is None:
                print(f"    {sid}: FAIL (will retain prior data if exists)")
                continue
            results[str(sid)] = payload
            print(f"    {sid}: {len(payload['data'])} items")
    return results


def fetch_trend24m(th_stores, comp_stores):
    """24 monthly chunks of /market/trend + /retailer/{id}/trend for
    each competitor, plus the Dutchie 24m snapshot for TH stores.
    Returns { market: [...], thStores: {dracut,pepperell,groton}, compStores: {"<id>":[...]} }"""
    print("\n[4/4] 24-month trend data...")
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Build list of completed calendar months going back 24 months
    months = []
    for i in range(24, 0, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        m_begin = date(y, m, 1)
        if m == 12:
            m_end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            m_end = date(y, m + 1, 1) - timedelta(days=1)
        if m_end <= yesterday:
            months.append({"begin": m_begin, "end": m_end, "label": m_begin.strftime("%b %Y")})

    print(f"  {len(months)} complete months to fetch")

    # Competitor store IDs
    comp_ids = [c["id"] for c in comp_stores]

    # Market daily trend across all 24 months, plus each competitor
    market_results_by_date = {}
    comp_results_by_id_by_date = {cid: {} for cid in comp_ids}

    # Parallelize per-month: 1 market call + N competitor calls
    def _fetch_month_market(mo):
        data = proxy_fetch("/market/trend", {"beginDate": mo["begin"], "endDate": mo["end"]})
        return mo["label"], (data or {}).get("results") or []

    def _fetch_month_comp(mo, cid):
        data = proxy_fetch(f"/retailer/{cid}/trend", {"beginDate": mo["begin"], "endDate": mo["end"]})
        return cid, mo["label"], (data or {}).get("results") or []

    # Do market first (light - 24 calls)
    with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as ex:
        market_futs = [ex.submit(_fetch_month_market, mo) for mo in months]
        for f in as_completed(market_futs):
            label, rows = f.result()
            for r in rows:
                d = r.get("date")
                if d and d not in market_results_by_date:
                    market_results_by_date[d] = r

    # Then competitors - chunked by month to avoid slamming the proxy
    for mo in months:
        with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as ex:
            futs = [ex.submit(_fetch_month_comp, mo, cid) for cid in comp_ids]
            for f in as_completed(futs):
                cid, label, rows = f.result()
                for r in rows:
                    d = r.get("date")
                    if d and d not in comp_results_by_id_by_date[cid]:
                        comp_results_by_id_by_date[cid][d] = r

    market_rows = sorted(market_results_by_date.values(), key=lambda r: r.get("date", ""))
    comp_rows = {
        str(cid): sorted(d.values(), key=lambda r: r.get("date", ""))
        for cid, d in comp_results_by_id_by_date.items()
    }
    print(f"  market: {len(market_rows)} daily points")
    for cid in comp_ids:
        print(f"  comp {cid}: {len(comp_rows[str(cid)])} daily points")

    # TH 24-month monthly rollup via dedicated Dutchie snapshot endpoint
    th_stores_24m = {"dracut": [], "pepperell": [], "groton": []}
    snap = proxy_fetch("/dutchie/24m-snapshot", include_state=False, include_dollar_values=False)
    if snap and isinstance(snap, dict) and snap.get("thStores"):
        for key in ["dracut", "pepperell", "groton"]:
            rows = snap["thStores"].get(key) or []
            th_stores_24m[key] = rows
            print(f"  TH {key}: {len(rows)} monthly points (source={snap.get('source', 'proxy')})")
    else:
        print("  TH 24m snapshot unavailable - thStores left empty (dashboard will fall back)")

    return {"market": market_rows, "thStores": th_stores_24m, "compStores": comp_rows}


# --------------------------------------------------------------
# PRIOR DATA FALLBACK - if a section fails, try to retain what was
# there last time. The current rainbow-review-data.js in the repo is
# just a stub, but if GH Actions ran before, a committed data file
# will be checked out in the workflow and we can reuse its shape.
# --------------------------------------------------------------
_PREBAKED_RE = re.compile(r"window\.__PREBAKED_DATA__\s*=\s*(\{.*?\});\s*$", re.DOTALL)


def load_prior_prebaked():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            text = f.read()
        m = _PREBAKED_RE.search(text)
        if not m:
            return None
        return json.loads(m.group(1))
    except Exception as e:
        print(f"  (could not parse prior data file: {type(e).__name__}: {e})")
        return None


def merge_with_prior(fresh, prior):
    """For any section that came back empty in `fresh`, substitute the prior
    snapshot's version so the dashboard never goes backwards on a partial
    failure."""
    if not prior:
        return fresh

    # Dutchie periods
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        if not fresh["dutchie"].get(period):
            fresh["dutchie"][period] = prior.get("dutchie", {}).get(period, {})

    # Lit Alerts periods - if retailers/categories are both empty, take prior
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        fp = fresh["litAlerts"][period]
        fresh_retailers = (fp.get("retailers") or {}).get("results") or []
        fresh_categories = (fp.get("categories") or {}).get("results") or []
        prior_p = (prior.get("litAlerts") or {}).get(period) or {}
        if not fresh_retailers and prior_p.get("retailers"):
            fp["retailers"] = prior_p["retailers"]
        if not fresh_categories and prior_p.get("categories"):
            fp["categories"] = prior_p["categories"]

    # Products - per-store fallback
    prior_products = prior.get("products") or {}
    for sid, prior_entry in prior_products.items():
        fresh_entry = fresh["products"].get(sid)
        fresh_items = (fresh_entry or {}).get("data") or []
        if not fresh_items and prior_entry:
            fresh["products"][sid] = prior_entry

    # Trend24m - section-level fallback
    t = fresh.get("trend24m", {})
    pt = prior.get("trend24m") or {}
    if not t.get("market") and pt.get("market"):
        t["market"] = pt["market"]
    for key in ["dracut", "pepperell", "groton"]:
        if not t.get("thStores", {}).get(key) and (pt.get("thStores") or {}).get(key):
            t.setdefault("thStores", {})[key] = pt["thStores"][key]
    for cid, rows in (pt.get("compStores") or {}).items():
        if not (t.get("compStores") or {}).get(cid) and rows:
            t.setdefault("compStores", {})[cid] = rows

    return fresh


# --------------------------------------------------------------
# OUTPUT WRITER
# --------------------------------------------------------------
HEADER = (
    "// Rainbow Review Pre-baked Data - Auto-generated {buildTime}\n"
    "// Refreshed daily by GitHub Actions (.github/workflows/refresh-dashboards.yml).\n"
    "// Consumed by loadFromPrebaked() in rainbow-review.html.\n"
    "window.__STATIC_SNAPSHOT__ = true;\n"
    "window.__PREBAKED_DATA__ = "
)


def write_data_file(prebaked):
    payload = HEADER.format(buildTime=prebaked["buildTime"]) + json.dumps(prebaked, ensure_ascii=True) + ";\n"
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(payload)
    size = os.path.getsize(DATA_FILE)
    print(f"\nWrote {DATA_FILE} ({size:,} bytes)")


# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------
def main():
    th_stores, comp_stores, lit_to_dutchie = _load_store_schema()
    print(f"Schema: {len(th_stores)} TH + {len(comp_stores)} competitors = {len(th_stores)+len(comp_stores)} total stores")

    ranges = _get_date_ranges()
    all_store_ids = [s["id"] for s in th_stores] + [c["id"] for c in comp_stores]

    # Load prior snapshot for fallback BEFORE we overwrite anything
    prior = load_prior_prebaked()
    if prior:
        print(f"Loaded prior snapshot (buildTime={prior.get('buildTime')}) for fallback")
    else:
        print("No prior snapshot available - any failed sections will be empty")

    # Fetch each section. A failure in one section returns {} / [] for that
    # section; merge_with_prior() then backfills from `prior`.
    fresh = {
        "buildTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.utcnow().microsecond//1000:03d}Z",
        "dutchie": {},
        "litAlerts": {},
        "products": {},
        "trend24m": {},
    }

    sections = [
        ("dutchie",    lambda: fetch_dutchie_periods(ranges)),
        ("litAlerts",  lambda: fetch_lit_alerts_periods(ranges)),
        ("products",   lambda: fetch_all_products(all_store_ids)),
        ("trend24m",   lambda: fetch_trend24m(th_stores, comp_stores)),
    ]

    errors = []
    for name, fn in sections:
        try:
            fresh[name] = fn()
        except Exception as e:
            print(f"\n!! Section '{name}' crashed: {type(e).__name__}: {e}")
            traceback.print_exc()
            errors.append(f"{name}: {type(e).__name__}: {e}")
            fresh[name] = {}  # fall through to merge_with_prior

    merged = merge_with_prior(fresh, prior)

    # Validation - don't write a file that's obviously broken
    validation_errors = []
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        if not merged["dutchie"].get(period):
            validation_errors.append(f"dutchie.{period} is empty (and no prior to fall back to)")
    if not merged["products"]:
        validation_errors.append("products is empty for all stores")
    if not merged["litAlerts"]:
        validation_errors.append("litAlerts is empty for all periods")

    if validation_errors:
        print("\nVALIDATION FAILED - not writing data file:")
        for e in validation_errors:
            print(f"  - {e}")
        raise SystemExit(1)

    write_data_file(merged)

    # Summary
    print("\n=== SUMMARY ===")
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        stores = merged["dutchie"].get(period, {})
        print(f"  dutchie.{period}: {len(stores)} stores")
    for period in ["daily", "weekly", "monthly", "lastMonth"]:
        la = merged["litAlerts"].get(period, {}) or {}
        rc = len((la.get("retailers") or {}).get("results", []) or [])
        cc = len((la.get("categories") or {}).get("results", []) or [])
        print(f"  litAlerts.{period}: {rc} retailers, {cc} categories")
    print(f"  products: {len(merged['products'])} stores, {sum(len((v or {}).get('data') or []) for v in merged['products'].values())} items")
    t = merged.get("trend24m") or {}
    print(f"  trend24m: market={len(t.get('market') or [])}, th={sum(len(v) for v in (t.get('thStores') or {}).values())}, comp={sum(len(v) for v in (t.get('compStores') or {}).values())}")
    if errors:
        print(f"\nNon-fatal section errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
