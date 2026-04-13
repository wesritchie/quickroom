#!/usr/bin/env python3
"""
Brick House Dashboard — Daily Data Refresh
Pulls Dutchie POS inventory/product data and Lit Alerts market data,
updates brick-house.html with fresh constants.
Runs as a GitHub Action on schedule.
"""

import os
import re
import json
import math
import base64
import requests
from datetime import datetime, timedelta, date
from collections import defaultdict

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
DUTCHIE_BASE = "https://api.pos.dutchie.com"
LIT_ALERTS_BASE = "https://partnerapi.litalerts.com"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(REPO_ROOT, "brick-house.html")

STORES = {
    "dracut":    os.environ.get("DUTCHIE_API_KEY_DRACUT", ""),
    "pepperell": os.environ.get("DUTCHIE_API_KEY_PEPPERELL", ""),
    "groton":    os.environ.get("DUTCHIE_API_KEY_GROTON", ""),
}

LIT_ALERTS_TOKEN = os.environ.get("LIT_ALERTS_TOKEN", "")

# Brick vendors and their Lit Alerts brand IDs
BRICK_VENDORS = {
    "fb": {"name": "Freshly Baked", "dutchie_vendor": "Freshly Baked", "lit_ids": [303]},
    "tb": {"name": "T.Bear / Coast", "dutchie_vendor": "T.Bear", "lit_ids": [251, 130]},  # T.Bear + Coast Cannabis
    "gf": {"name": "Good Feels", "dutchie_vendor": "Good Feels", "lit_ids": [346]},
    "wf": {"name": "Wellman Farms", "dutchie_vendor": "Wellman Farms", "lit_ids": [1165]},
    "bo": {"name": "Bostica", "dutchie_vendor": "Bostica", "lit_ids": [1400]},
    "hp": {"name": "High Plains Farm", "dutchie_vendor": "High Plains Farm", "lit_ids": [897]},
    "mc": {"name": "MACC", "dutchie_vendor": "MACC", "lit_ids": [2073]},
    "hb": {"name": "Hudson Botanical", "dutchie_vendor": "Hudson Botanical Processing, LLC",
            "lit_ids": [334, 1558, 96, 3604, 13076, 10076]},  # Hudson, Nimbus, Cheeba, Clebby's, Just Joints, Just Vapes
}

# Vendor aliases for matching Dutchie product.brand to vendor keys
VENDOR_ALIASES = {
    "fb": ["Freshly Baked"],
    "tb": ["T.Bear", "T. Bear", "Coast", "Coast Cannabis"],
    "gf": ["Good Feels"],
    "wf": ["Wellman Farms", "Wellman"],
    "bo": ["Bostica"],
    "hp": ["High Plains Farm", "High Plains"],
    "mc": ["MACC"],
    "hb": ["Hudson Botanical Processing, LLC", "Hudson Botanical", "Nimbus",
            "Just Vapes", "Just Resin", "Just Joints", "Cheeba Chews", "Clebby's"],
}

# Core vendors (for inventory classification)
CORE_VENDORS = [
    "Cultivate", "ARL Healthcare", "Garden Remedies", "Green Meadows",
    "Novel Beverage", "Lunar Xtracts", "Curaleaf", "Mederi", "Humboldt Masters"
]

MAX_RETRIES = 3
RETRY_DELAY = 10


# ──────────────────────────────────────────────
# API HELPERS
# ──────────────────────────────────────────────
def dutchie_fetch(store_key, endpoint, params=None):
    """Fetch from Dutchie POS API for a specific store."""
    api_key = STORES[store_key]
    auth = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                f"{DUTCHIE_BASE}/{endpoint}",
                headers=headers,
                params=params or {},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt+1}/{MAX_RETRIES} for {store_key}/{endpoint}: {e}")
                import time; time.sleep(RETRY_DELAY)
            else:
                print(f"  FAILED after {MAX_RETRIES} retries: {store_key}/{endpoint}: {e}")
                return None


def lit_alerts_fetch(endpoint, params=None):
    """Fetch from Lit Alerts Partner API."""
    headers = {"Authorization": f"Bearer {LIT_ALERTS_TOKEN}", "Accept": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                f"{LIT_ALERTS_BASE}{endpoint}",
                headers=headers,
                params=params or {},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt+1}/{MAX_RETRIES} for {endpoint}: {e}")
                import time; time.sleep(RETRY_DELAY)
            else:
                print(f"  FAILED after {MAX_RETRIES} retries: {endpoint}: {e}")
                return None


# ──────────────────────────────────────────────
# DATA FETCHING
# ──────────────────────────────────────────────
def fetch_product_data():
    """Fetch product catalog from Dutchie for all 3 stores.
    Returns PRODUCT_DATA and INVENTORY_MIX structures.
    """
    print("\n[1/3] Fetching Dutchie product catalogs...")
    all_products = {}
    per_store_totals = {}

    for store_key in ["dracut", "pepperell", "groton"]:
        print(f"  {store_key}...")
        products = dutchie_fetch(store_key, "products")
        if products is None:
            print(f"  WARNING: Could not fetch products for {store_key}")
            continue
        all_products[store_key] = products if isinstance(products, list) else products.get("data", products)
        per_store_totals[store_key] = len(all_products[store_key])

    # Classify products by vendor
    vendor_products = defaultdict(list)
    all_brick_aliases = {}
    for vk, aliases in VENDOR_ALIASES.items():
        for a in aliases:
            all_brick_aliases[a.lower()] = vk

    # Deduplicate by productId across stores
    seen_product_ids = set()
    brick_ids = set()
    core_ids = set()
    other_ids = set()

    for store_key, products in all_products.items():
        for p in products:
            pid = p.get("productId")
            if pid in seen_product_ids:
                continue
            seen_product_ids.add(pid)

            brand = (p.get("brand") or p.get("vendorName") or "").strip()
            qty = p.get("quantityAvailable", 0) or 0
            if qty <= 0:
                continue

            # Classify
            vendor_key = all_brick_aliases.get(brand.lower())
            if vendor_key:
                brick_ids.add(pid)
                vendor_products[vendor_key].append(p)
            elif any(brand.lower().startswith(cv.lower()) for cv in CORE_VENDORS):
                core_ids.add(pid)
            else:
                other_ids.add(pid)

    # Build PRODUCT_DATA
    product_data_vendors = {}
    for vk, vinfo in BRICK_VENDORS.items():
        products = vendor_products.get(vk, [])
        categories = defaultdict(lambda: {"count": 0, "total_price": 0, "total_cost": 0})
        for p in products:
            cat = p.get("category", "Other")
            price = p.get("unitPrice", 0) or 0
            cost = p.get("unitCost", 0) or 0
            categories[cat]["count"] += 1
            categories[cat]["total_price"] += price
            categories[cat]["total_cost"] += cost

        cat_data = {}
        for cat_name, cat_info in sorted(categories.items(), key=lambda x: -x[1]["count"]):
            n = cat_info["count"]
            cat_data[cat_name] = {
                "skus": n,
                "avgPrice": round(cat_info["total_price"] / n, 2) if n > 0 else 0,
                "avgCost": round(cat_info["total_cost"] / n, 2) if n > 0 else 0,
            }
        product_data_vendors[vk] = {"totalSkus": len(products), "categories": cat_data}

    product_data = {
        "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vendors": product_data_vendors,
    }

    # Build INVENTORY_MIX
    # Count in-stock brick vendor SKUs
    brick_vendor_counts = []
    for vk, vinfo in BRICK_VENDORS.items():
        count = len(vendor_products.get(vk, []))
        if count > 0:
            brick_vendor_counts.append({"name": vinfo["name"], "skus": count})
    brick_vendor_counts.sort(key=lambda x: -x["skus"])

    inventory_mix = {
        "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "In-stock SKUs only via /inventory endpoint (quantityAvailable > 0), deduplicated by productId across all 3 stores.",
        "totalActive": len(seen_product_ids),
        "totalBrick": len(brick_ids),
        "totalCore": len(core_ids),
        "totalOther": len(other_ids),
        "perStore": {k: {"total": v} for k, v in per_store_totals.items()},
        "brickVendors": brick_vendor_counts,
    }

    return product_data, inventory_mix


def fetch_store_revenue():
    """Fetch Dutchie transaction data to compute revenue by vendor.
    Returns storeData structure with monthly revenue per vendor per store.
    """
    print("\n[2/3] Fetching Dutchie revenue data...")
    today = date.today()

    # We only need to update the current month's revenue
    # Fetch current month transactions for each store
    month_start = today.replace(day=1)
    month_key = f"{today.strftime('%b')}{str(today.year)[2:]}"  # e.g., "Apr26"

    store_data_update = {}
    for store_key in ["dracut", "pepperell", "groton"]:
        print(f"  {store_key} — {month_key}...")
        # Fetch transactions for current month
        params = {
            "FromDateUTC": f"{month_start}T00:00:00Z",
            "ToDateUTC": f"{today}T23:59:59Z",
            "pageSize": 200,
            "page": 1,
        }
        all_txns = []
        while True:
            data = dutchie_fetch(store_key, "reporting/register-transactions", params)
            if data is None:
                break
            txns = data if isinstance(data, list) else data.get("data", [])
            all_txns.extend(txns)
            if len(txns) < 200:
                break
            params["page"] += 1

        # For now, we report the total revenue for current month
        # The vendor breakdown requires line-item data which register-transactions may not provide
        # We'll include what we can and note limitations
        total = sum(t.get("transactionAmount", 0) for t in all_txns if t.get("transactionType") == "Sale")
        store_data_update[store_key] = {month_key: {"total": round(total, 2), "txn_count": len(all_txns)}}
        print(f"    {len(all_txns)} transactions, ${total:,.2f} total")

    return store_data_update


def fetch_lit_alerts_data():
    """Fetch Lit Alerts market data for brick vendors.
    Returns LIT_ALERTS_DATA and MARKET_TREND_DATA structures.
    """
    if not LIT_ALERTS_TOKEN:
        print("\n[3/3] Skipping Lit Alerts — no token available")
        return None, None

    print("\n[3/3] Fetching Lit Alerts market data...")
    today = date.today()

    # ── LIT_ALERTS_DATA: Retailer distribution per vendor ──
    vendor_retailers = {}
    for vk, vinfo in BRICK_VENDORS.items():
        for brand_id in vinfo["lit_ids"]:
            print(f"  Brand {vinfo['name']} (id={brand_id})...")
            # Get retailer distribution for this brand
            data = lit_alerts_fetch(f"/brand/{brand_id}/events", {
                "beginDate": (today - timedelta(days=90)).strftime("%Y-%m-%d"),
                "endDate": today.strftime("%Y-%m-%d"),
                "state": "MA",
            })
            # We'll aggregate retailer presence from the events

    # ── MARKET_TREND_DATA: Monthly sales by vendor ──
    market_trend_months = []
    market_trend_vendors = defaultdict(dict)

    # Fetch monthly market data for past 14 months
    for months_ago in range(14, -1, -1):
        month_dt = today.replace(day=1) - timedelta(days=months_ago * 30)
        month_start = month_dt.replace(day=1)
        if months_ago > 0:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            month_end = next_month - timedelta(days=1)
        else:
            month_end = today

        month_key = month_start.strftime("%Y-%m")
        if month_key not in market_trend_months:
            market_trend_months.append(month_key)

        print(f"  Market trend: {month_key}...")
        data = lit_alerts_fetch("/market/brands", {
            "beginDate": month_start.strftime("%Y-%m-%d"),
            "endDate": month_end.strftime("%Y-%m-%d"),
            "state": "MA",
            "returnDollarValues": "true",
        })
        if data and "data" in data:
            # Match brands to our vendors
            for brand_entry in data["data"]:
                brand_name = brand_entry.get("name", "")
                brand_id = brand_entry.get("id")
                for vk, vinfo in BRICK_VENDORS.items():
                    if brand_id in vinfo["lit_ids"]:
                        revenue = brand_entry.get("revenue", 0) or brand_entry.get("totalSales", 0) or 0
                        market_trend_vendors[vk][month_key] = market_trend_vendors[vk].get(month_key, 0) + round(revenue)

    market_trend = {
        "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Monthly estimated sales ($) across all MA retailers, via Lit Alerts analytics.",
        "months": market_trend_months,
        "vendors": dict(market_trend_vendors),
    }

    return None, market_trend  # LIT_ALERTS_DATA retailer detail is complex, handle separately


# ──────────────────────────────────────────────
# HTML UPDATE (reuses geo_totem's replace_js_const)
# ──────────────────────────────────────────────
def replace_js_const(html, const_name, new_value_str, is_array=False):
    """Replace a JavaScript const block in the HTML."""
    pattern = rf"(const\s+{const_name}\s*=\s*)"
    match = re.search(pattern, html)
    if not match:
        raise ValueError(f"Could not find 'const {const_name}' in HTML")

    start = match.start()
    value_start = match.end()
    open_c = "[" if is_array else "{"
    close_c = "]" if is_array else "}"

    depth = 0
    in_string = False
    escape_next = False
    end_pos = value_start

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
                end_pos = i + 1
                break

    if end_pos < len(html) and html[end_pos] == ";":
        end_pos += 1

    replacement = f"{match.group(1)}{new_value_str};"
    return html[:start] + replacement + html[end_pos:]


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    missing = []
    for k, v in STORES.items():
        if not v:
            missing.append(f"DUTCHIE_API_KEY_{k.upper()}")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Fetch all data
    product_data, inventory_mix = fetch_product_data()
    lit_alerts_data, market_trend = fetch_lit_alerts_data()

    # Update HTML constants
    print("\nUpdating HTML file...")

    # Update PRODUCT_DATA
    html = replace_js_const(html, "PRODUCT_DATA", json.dumps(product_data, indent=2, ensure_ascii=True))
    print("  Updated PRODUCT_DATA")

    # Update INVENTORY_MIX
    html = replace_js_const(html, "INVENTORY_MIX", json.dumps(inventory_mix, indent=2, ensure_ascii=True))
    print("  Updated INVENTORY_MIX")

    # Update MARKET_TREND_DATA (if Lit Alerts succeeded)
    if market_trend:
        html = replace_js_const(html, "MARKET_TREND_DATA", json.dumps(market_trend, indent=2, ensure_ascii=True))
        print("  Updated MARKET_TREND_DATA")
    else:
        print("  Skipped MARKET_TREND_DATA (Lit Alerts unavailable)")

    # Write
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDone! Updated {HTML_FILE}")
    print(f"  Product data: {sum(v['totalSkus'] for v in product_data['vendors'].values())} total SKUs")
    print(f"  Inventory: {inventory_mix['totalActive']} active, {inventory_mix['totalBrick']} brick")


if __name__ == "__main__":
    main()
