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

# Brick vendors WITH their own dashboard tab/tile. Keys must match the
# `VENDORS` object in brick-house.html (fb/tb/gf/wf/bo/hp/mc).
#
# SINGLE SOURCE OF TRUTH: brick-house.html is the canonical schema. The
# Python schema below is loaded at runtime by parsing three blocks out of
# the HTML — VENDORS (display names), brandIds (Lit Alerts IDs), and
# vendorAliases.dutchie (Dutchie brand-name aliases). This prevents drift:
# update the HTML once, and the refresh script picks it up next run.
#
# Hard fail on parse error — never fall back to stale constants, because
# silently running with a degraded schema would corrupt vendor totals.
def _load_vendor_schema_from_html():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # 1) Display names from `VENDORS = { fb: { name: "Freshly Baked", ... }, ... }`
    vendors_block = re.search(
        r"\bVENDORS\s*=\s*\{(.*?)\}\s*;", html, re.DOTALL
    )
    if not vendors_block:
        raise RuntimeError("Could not locate VENDORS block in brick-house.html")
    names = dict(re.findall(
        r'(\w+)\s*:\s*\{\s*name\s*:\s*"([^"]+)"', vendors_block.group(1)
    ))

    # 2) Dutchie aliases + Lit Alerts brand IDs, both from the single
    # `vendorAliases = { fb: { dutchie: [...], litAlerts: [{id:N,...}], ... } }`
    # block. One source of truth, no drift possible.
    aliases_block = re.search(
        r"vendorAliases\s*=\s*\{(.*?)\}\s*;", html, re.DOTALL
    )
    if not aliases_block:
        raise RuntimeError("Could not locate vendorAliases block in brick-house.html")
    aliases = {}
    lit_ids = {}
    for vk, body in re.findall(
        r"(\w+)\s*:\s*\{(.*?)\}\s*(?=,\s*\w+\s*:\s*\{|\Z)",
        aliases_block.group(1), re.DOTALL,
    ):
        dutchie_match = re.search(r'dutchie\s*:\s*\[(.*?)\]', body, re.DOTALL)
        if dutchie_match:
            aliases[vk] = re.findall(r'"([^"]+)"', dutchie_match.group(1))
        lit_match = re.search(r'litAlerts\s*:\s*\[(.*?)\]', body, re.DOTALL)
        if lit_match:
            lit_ids[vk] = [int(i) for i in re.findall(r"id\s*:\s*(\d+)", lit_match.group(1))]

    # Cross-check: every key that has a name must also have lit_ids and aliases
    missing = [k for k in names if k not in lit_ids or k not in aliases]
    if missing:
        raise RuntimeError(
            f"brick-house.html schema incomplete for vendors: {missing} "
            f"(names={list(names)}, lit_ids={list(lit_ids)}, aliases={list(aliases)})"
        )

    brick_vendors = {
        vk: {"name": names[vk], "lit_ids": lit_ids[vk]} for vk in names
    }
    return brick_vendors, aliases


BRICK_VENDORS, VENDOR_ALIASES = _load_vendor_schema_from_html()

# Additional brick-classified brands that COUNT toward brick inventory totals
# but don't have their own dashboard tab. Shown in brickVendors lists only.
EXTRA_BRICK_BRANDS = {
    "Hudson Botanical": [
        "Hudson Botanical", "Hudson Botanical Processing, LLC", "Nimbus",
        "Just Vapes", "Just Resin", "Just Joints", "Cheeba Chews", "Clebby's",
    ],
}

# Core vendors (for inventory classification). Matched as case-insensitive prefix.
CORE_VENDORS = [
    "Cultivate", "ARL Healthcare", "Garden Remedies", "Green Meadows",
    "Novel Beverage", "Lunar Xtracts", "Curaleaf", "Mederi", "Humboldt Masters",
]

# Map Dutchie product.category → dashboard category group shown in byCategory.
# Keys matched case-insensitively; falls through to 'Merch / Accessories'.
CATEGORY_GROUPS = {
    # Flower
    "bud": "Flower", "pre ground": "Flower", "shake": "Flower", "seeds": "Flower",
    # Pre-Rolls  (singles, multipacks, infused variants)
    "single": "Pre-Rolls", "multipack": "Pre-Rolls",
    "single infused": "Pre-Rolls", "multipack infused": "Pre-Rolls",
    # Vapes
    "510 cart": "Vapes", "disposable": "Vapes", "vaporizers": "Vapes",
    "retire - vape cartridges": "Vapes",
    # Edibles
    "gummies": "Edibles", "chocolate": "Edibles", "baked goods": "Edibles",
    "tablet": "Edibles", "dried fruit": "Edibles", "snacks": "Edibles",
    "retire - edible": "Edibles",
    # Beverages
    "drink mix": "Beverages", "seltzer": "Beverages",
    # Concentrates
    "live rosin": "Concentrates", "concentrate": "Concentrates",
    "cured resin": "Concentrates", "kief": "Concentrates",
    # Topicals
    "topicals": "Topicals", "salve": "Topicals",
    # Everything else (apparel, accessories, gift cards, bundles, pet, glass,
    # grinders, rolling papers, non-thc, prizes, gifts, display, sample, retire-prerolls)
    # falls through to 'Merch / Accessories' via classify_category()
}

# Categories to exclude entirely from byCategory/vendor-count aggregation
# (internal ops bookkeeping, not real inventory the dashboard cares about).
EXCLUDE_CATEGORIES = {"sample", "display", "prizes"}

MAX_RETRIES = 3
RETRY_DELAY = 10


# ──────────────────────────────────────────────
# API HELPERS
# ──────────────────────────────────────────────
def dutchie_fetch(store_key, endpoint, params=None):
    """Fetch from Dutchie POS API for a specific store."""
    api_key = STORES[store_key]
    if not api_key:
        print(f"  DUTCHIE_ERR store={store_key} endpoint={endpoint} reason=MISSING_API_KEY")
        return None
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
            status = resp.status_code
            if status >= 400:
                preview = (resp.text or "")[:200].replace("\n", " ")
                print(f"  DUTCHIE_ERR store={store_key} endpoint={endpoint} attempt={attempt+1} status={status} preview={preview}")
                resp.raise_for_status()
            body = resp.json()
            count = len(body) if isinstance(body, list) else (len(body.get("data", [])) if isinstance(body, dict) else 0)
            print(f"  DUTCHIE_OK store={store_key} endpoint={endpoint} status={status} count={count}")
            return body
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  DUTCHIE_RETRY store={store_key} endpoint={endpoint} attempt={attempt+1}/{MAX_RETRIES} err={type(e).__name__}:{e}")
                import time; time.sleep(RETRY_DELAY)
            else:
                print(f"  DUTCHIE_FAIL store={store_key} endpoint={endpoint} err={type(e).__name__}:{e}")
                return None


def lit_alerts_probe():
    """Minimal auth probe: call the simplest possible endpoint and print full diagnostics."""
    if not LIT_ALERTS_TOKEN:
        print("  LIT_PROBE reason=NO_TOKEN_IN_ENV")
        return False
    tok = LIT_ALERTS_TOKEN
    # Decode JWT header+payload (no verify) to see claims — helps diagnose expiry/scope.
    try:
        import base64 as _b64, json as _json
        parts = tok.split(".")
        def _pad(s): return s + "=" * (-len(s) % 4)
        hdr = _json.loads(_b64.urlsafe_b64decode(_pad(parts[0])).decode("utf-8", "replace")) if len(parts) >= 2 else {}
        pl = _json.loads(_b64.urlsafe_b64decode(_pad(parts[1])).decode("utf-8", "replace")) if len(parts) >= 2 else {}
        print(f"  LIT_PROBE token_len={len(tok)} alg={hdr.get('alg')} typ={hdr.get('typ')} exp={pl.get('exp')} iss={pl.get('iss')} sub={pl.get('sub')} role={pl.get('role') or pl.get('roles')}")
    except Exception as _e:
        print(f"  LIT_PROBE token_decode_err={type(_e).__name__}:{_e} token_len={len(tok)}")
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    # CRITICAL: Lit Alerts expects MM-DD-YYYY date format, NOT YYYY-MM-DD.
    # Using YYYY-MM-DD returns HTTP 500 with empty body (no helpful error message).
    # Confirmed by Lit Alerts support (Austin) 2026-04. Ticket in their backlog to improve errors.
    dr_short = {"beginDate": "03-01-2026", "endDate": "03-15-2026", "state": "MA"}
    dr_old = {"beginDate": "10-01-2025", "endDate": "10-31-2025", "state": "MA"}
    dr_wide = {"beginDate": "01-01-2026", "endDate": "03-31-2026", "state": "MA"}
    # Pick a known retailer id if available in BRICK_VENDORS has lit_ids? use 1 as a smoke-test
    probe_list = [
        ("/retailers", {"state": "MA"}),
        ("/brands", {"state": "MA"}),
        ("/market/brands", dr_short),
        ("/market/brands", dr_old),
        ("/market/brands", dr_wide),
        ("/market/retailers", dr_short),
        ("/market/categories", dr_short),
        ("/market/trend", dr_short),
        # Brand-scoped analytics (we've confirmed /brand/{id}/retailers works in prod run)
        ("/brand/303/trend", dr_short),
        ("/brand/303/categories", dr_short),
        ("/brand/303/retailers", dr_short),
    ]
    for ep, params in probe_list:
        try:
            r = requests.get(f"{LIT_ALERTS_BASE}{ep}", headers=headers, params=params, timeout=15)
            body = (r.text or "")[:400].replace("\n", " ")
            hdrs = {k: v for k, v in r.headers.items() if k.lower() in ("www-authenticate", "x-request-id", "x-correlation-id", "content-type", "content-length", "server")}
            print(f"  LIT_PROBE endpoint={ep} status={r.status_code} headers={hdrs} body={body}")
        except Exception as e:
            print(f"  LIT_PROBE endpoint={ep} err={type(e).__name__}:{e}")
    return True


def lit_alerts_fetch(endpoint, params=None):
    """Fetch from Lit Alerts Partner API."""
    if not LIT_ALERTS_TOKEN:
        print(f"  LIT_ERR endpoint={endpoint} reason=MISSING_TOKEN")
        return None
    headers = {"Authorization": f"Bearer {LIT_ALERTS_TOKEN}", "Accept": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                f"{LIT_ALERTS_BASE}{endpoint}",
                headers=headers,
                params=params or {},
                timeout=30,
            )
            status = resp.status_code
            if status >= 400:
                preview = (resp.text or "")[:400].replace("\n", " ")
                extra_hdrs = {k: v for k, v in resp.headers.items() if k.lower() in ("www-authenticate", "x-request-id", "x-correlation-id", "content-type", "content-length")}
                print(f"  LIT_ERR endpoint={endpoint} attempt={attempt+1} status={status} headers={extra_hdrs} body_len={len(resp.text or '')} preview={preview}")
                resp.raise_for_status()
            body = resp.json()
            count = len(body) if isinstance(body, list) else (len(body.get("data", [])) if isinstance(body, dict) else 0)
            print(f"  LIT_OK endpoint={endpoint} status={status} count={count}")
            return body
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  LIT_RETRY endpoint={endpoint} attempt={attempt+1}/{MAX_RETRIES} err={type(e).__name__}:{e}")
                import time; time.sleep(RETRY_DELAY)
            else:
                print(f"  LIT_FAIL endpoint={endpoint} err={type(e).__name__}:{e}")
                return None


# ──────────────────────────────────────────────
# CLASSIFICATION HELPERS
# ──────────────────────────────────────────────
def _build_alias_map():
    """Map lowercased brand fragment → vendor_key for dashboard-tab brick vendors.
    Longest aliases first so 'T. Bear' wins over 'Bear' etc.
    """
    m = {}
    for vk, aliases in VENDOR_ALIASES.items():
        for a in aliases:
            m[a.lower()] = vk
    return m


def _build_extra_brick_map():
    """Map normalized brand fragment → display name for extra-brick (non-tab) brands."""
    m = {}
    for display, aliases in EXTRA_BRICK_BRANDS.items():
        for a in aliases:
            m[_norm(a)] = display
    return m


def _norm(s):
    """Normalize a brand string for matching: lowercase, strip all non-alphanumeric
    chars (periods, commas, spaces, hyphens, etc.). So 'T. Bear', 'T.Bear', 'T Bear',
    'T-Bear' all canonicalize to 'tbear'. Handles formatting drift in Dutchie
    vendor strings without requiring us to enumerate every variant in the alias list."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _rebuild_alias_map():
    """Rebuild alias map using normalized keys (punctuation/whitespace insensitive)."""
    m = {}
    for vk, aliases in VENDOR_ALIASES.items():
        for a in aliases:
            m[_norm(a)] = vk
    return m


def classify_brand(brand):
    """Return ('brick_tab', vendor_key) | ('brick_extra', display) | ('core', vendor_name) | ('other', None).
    Matching is punctuation/whitespace-insensitive via _norm()."""
    if not brand:
        return ("other", None)
    bn = _norm(brand)
    tabs = _rebuild_alias_map()
    for alias, vk in tabs.items():
        if alias and alias in bn:
            return ("brick_tab", vk)
    extras = _build_extra_brick_map()
    for alias, display in extras.items():
        if alias and alias in bn:
            return ("brick_extra", display)
    for cv in CORE_VENDORS:
        if bn.startswith(_norm(cv)):
            return ("core", cv)
    return ("other", None)


def classify_category(cat):
    """Map raw Dutchie category → one of the 8 dashboard groups, or None to exclude."""
    if not cat:
        return "Merch / Accessories"
    cl = cat.strip().lower()
    if cl in EXCLUDE_CATEGORIES:
        return None  # caller should drop
    return CATEGORY_GROUPS.get(cl, "Merch / Accessories")


def _sorted_vendor_list(counter, top_n=None):
    """Turn {name: count} → [{name, skus}] sorted desc, optionally truncated."""
    lst = [{"name": n, "skus": c} for n, c in counter.items() if c > 0]
    lst.sort(key=lambda x: (-x["skus"], x["name"]))
    return lst[:top_n] if top_n else lst


# ──────────────────────────────────────────────
# DATA FETCHING
# ──────────────────────────────────────────────
def fetch_inventory_data():
    """Fetch product catalogs from Dutchie for all 3 stores and compute the full
    PRODUCT_DATA, INVENTORY_MIX (aggregate), and STORE_INVENTORY (per-store)
    structures that brick-house.html expects.

    Keys in PRODUCT_DATA.vendors are LIMITED to BRICK_VENDORS (dashboard tabs).
    Hudson Botanical and other extra-brick brands count toward brick totals
    but do NOT get their own PRODUCT_DATA entry (would break vendor rendering).
    """
    # Use /inventory, NOT /products. Per Dutchie v001 swagger:
    #   /products   → ProductDetail   (catalog master; has NO quantity field)
    #   /inventory  → InventoryItem   (per-package stock; has quantityAvailable:number)
    # The old /products call returned 7,400+ catalog rows with no stock info, so
    # `quantityAvailable > 0` matched zero rows every time. /inventory is the
    # authoritative source for on-hand stock and carries brandName/category/productId.
    print("\n[1/2] Fetching Dutchie inventory (3 stores)...  [endpoint=/inventory]")
    raw_by_store = {}
    for store_key in ["dracut", "pepperell", "groton"]:
        print(f"  {store_key}...")
        inventory = dutchie_fetch(store_key, "inventory")
        if inventory is None:
            print(f"  WARNING: Could not fetch inventory for {store_key}")
            raw_by_store[store_key] = []
            continue
        lst = inventory if isinstance(inventory, list) else inventory.get("data", inventory)
        # Filter to in-stock only (field exists on InventoryItem schema).
        # /inventory returns per-package rows; multiple rows per productId are
        # deduped downstream via store_seen/seen_pids sets in the classifier pass.
        raw_by_store[store_key] = [p for p in lst if (p.get("quantityAvailable", 0) or 0) > 0]
        print(f"    {len(raw_by_store[store_key])} in-stock inventory rows")

    # ── Per-store aggregation containers ──
    # aggregate (across all stores, deduped by productId)
    seen_pids = set()
    agg_brick_vendor = defaultdict(int)   # display name → SKU count
    agg_core_vendor = defaultdict(int)
    agg_other_vendor = defaultdict(int)
    agg_by_cat = defaultdict(lambda: {
        "brick": 0, "core": 0, "other": 0,
        "brickVendors": defaultdict(int), "coreVendors": defaultdict(int),
    })
    total_brick = total_core = total_other = 0

    # Per-tab-vendor PRODUCT_DATA aggregation (across all stores, deduped)
    tab_vendor_cats = {vk: defaultdict(lambda: {"count": 0, "price_sum": 0, "cost_sum": 0})
                       for vk in BRICK_VENDORS}
    tab_vendor_total = {vk: 0 for vk in BRICK_VENDORS}

    # Per-store containers
    store_inventory = {}
    for store_key in ["dracut", "pepperell", "groton"]:
        store_inventory[store_key] = {
            "total": 0, "brick": 0, "core": 0, "other": 0,
            "brick_vendor": defaultdict(int),
            "core_vendor": defaultdict(int),
            "other_vendor": defaultdict(int),
            "by_cat": defaultdict(lambda: {"brick": 0, "core": 0, "other": 0}),
        }

    # ── Pass 1: classify every product ──
    for store_key, products in raw_by_store.items():
        s = store_inventory[store_key]
        # Per-store dedup (same productId can appear multiple times in /products)
        store_seen = set()
        for p in products:
            pid = p.get("productId")
            if pid in store_seen:
                continue
            store_seen.add(pid)

            # InventoryItem schema exposes BOTH "brandName" (consumer brand, e.g. "Coast",
            # "Bostica", "High Plains Farm") AND "vendor" (licensee/operator name, e.g.
            # "T. Bear", "Bostica, LLC", "27 Broom Street, LLC"). vendorAliases in
            # brick-house.html lists the operator names — so we MUST check both fields
            # together. Joining them into one matching string lets classify_brand() hit
            # an alias regardless of which field carries the match. Verified via live
            # /inventory probe on 2026-04-14: tb needs vendor="T. Bear", wf needs
            # vendor="Wellman Farm, Inc.", hp needs vendor="27 Broom Street, LLC".
            brand_name = (p.get("brandName") or p.get("brand") or "").strip()
            vendor_name = (p.get("vendor") or p.get("vendorName") or "").strip()
            brand = " | ".join(x for x in (brand_name, vendor_name) if x)
            raw_cat = p.get("category") or ""
            group = classify_category(raw_cat)
            if group is None:
                continue  # drop SAMPLE / DISPLAY / Prizes entirely

            tier, tier_key = classify_brand(brand)

            # Per-store totals
            s["total"] += 1
            if tier == "brick_tab":
                s["brick"] += 1
                s["brick_vendor"][BRICK_VENDORS[tier_key]["name"]] += 1
                s["by_cat"][group]["brick"] += 1
            elif tier == "brick_extra":
                s["brick"] += 1
                s["brick_vendor"][tier_key] += 1
                s["by_cat"][group]["brick"] += 1
            elif tier == "core":
                s["core"] += 1
                s["core_vendor"][tier_key] += 1
                s["by_cat"][group]["core"] += 1
            else:
                s["other"] += 1
                if brand:
                    s["other_vendor"][brand] += 1
                s["by_cat"][group]["other"] += 1

            # Aggregate dedupe across stores
            if pid in seen_pids:
                continue
            seen_pids.add(pid)

            if tier == "brick_tab":
                total_brick += 1
                name = BRICK_VENDORS[tier_key]["name"]
                agg_brick_vendor[name] += 1
                agg_by_cat[group]["brick"] += 1
                agg_by_cat[group]["brickVendors"][name] += 1
                # PRODUCT_DATA detail for this tab-vendor
                tab_vendor_total[tier_key] += 1
                price = p.get("unitPrice", 0) or 0
                cost = p.get("unitCost", 0) or 0
                tab_vendor_cats[tier_key][raw_cat]["count"] += 1
                tab_vendor_cats[tier_key][raw_cat]["price_sum"] += price
                tab_vendor_cats[tier_key][raw_cat]["cost_sum"] += cost
            elif tier == "brick_extra":
                total_brick += 1
                agg_brick_vendor[tier_key] += 1
                agg_by_cat[group]["brick"] += 1
                agg_by_cat[group]["brickVendors"][tier_key] += 1
            elif tier == "core":
                total_core += 1
                agg_core_vendor[tier_key] += 1
                agg_by_cat[group]["core"] += 1
                agg_by_cat[group]["coreVendors"][tier_key] += 1
            else:
                total_other += 1
                if brand:
                    agg_other_vendor[brand] += 1
                agg_by_cat[group]["other"] += 1

    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Build PRODUCT_DATA (tab vendors only) ──
    product_data_vendors = {}
    for vk in BRICK_VENDORS:
        cat_map = tab_vendor_cats[vk]
        cat_out = {}
        for cat_name, d in sorted(cat_map.items(), key=lambda x: -x[1]["count"]):
            n = d["count"]
            if n == 0:
                continue
            cat_out[cat_name] = {
                "skus": n,
                "avgPrice": round(d["price_sum"] / n, 2),
                "avgCost":  round(d["cost_sum"] / n, 2),
            }
        product_data_vendors[vk] = {"totalSkus": tab_vendor_total[vk], "categories": cat_out}

    product_data = {"lastUpdated": now_iso, "vendors": product_data_vendors}

    # ── Build INVENTORY_MIX (aggregate) ──
    byCategory = []
    # Keep the same display order the dashboard expects
    cat_order = ["Merch / Accessories", "Pre-Rolls", "Vapes", "Flower",
                 "Edibles", "Beverages", "Concentrates", "Topicals"]
    for cg in cat_order:
        c = agg_by_cat.get(cg)
        if not c:
            byCategory.append({"group": cg, "brick": 0, "core": 0, "other": 0,
                               "coreVendors": {}, "brickVendors": {}})
            continue
        byCategory.append({
            "group": cg,
            "brick": c["brick"], "core": c["core"], "other": c["other"],
            "coreVendors": dict(sorted(c["coreVendors"].items(), key=lambda x: -x[1])),
            "brickVendors": dict(sorted(c["brickVendors"].items(), key=lambda x: -x[1])),
        })

    # Unmatched-brand diagnostic — surfaces Dutchie vendor strings that didn't
    # classify as brick_tab / brick_extra / core. Review after each run: if a
    # real brick/core vendor is slipping through under a formatting variant, add
    # the alias to brick-house.html (vendorAliases.dutchie) with high confidence.
    top_unmatched = sorted(agg_other_vendor.items(), key=lambda x: -x[1])[:20]
    if top_unmatched:
        print(f"\n[DIAGNOSTIC] Top 20 unmatched Dutchie brand strings ({len(agg_other_vendor)} distinct total):")
        for name, cnt in top_unmatched:
            print(f"   • {cnt:>4} SKUs  |  {name!r}")
        print("   ↳ If any of these should be brick/core, add alias to brick-house.html vendorAliases.dutchie")

    other_full_list = _sorted_vendor_list(agg_other_vendor)
    inventory_mix = {
        "lastUpdated": now_iso,
        "note": "In-stock SKUs via Dutchie /products (quantityAvailable > 0), deduplicated by productId across all 3 stores. SAMPLE / DISPLAY / Prizes excluded.",
        "totalActive": total_brick + total_core + total_other,
        "totalBrick": total_brick,
        "totalCore": total_core,
        "totalOther": total_other,
        "perStore": {sk: {"total": store_inventory[sk]["total"]}
                     for sk in ["dracut", "pepperell", "groton"]},
        "brickVendors": _sorted_vendor_list(agg_brick_vendor),
        "coreVendors": _sorted_vendor_list(agg_core_vendor),
        "otherVendors": other_full_list[:22],  # dashboard shows top ~22
        "otherVendorsFull": len(other_full_list),
        "missingCore": [cv for cv in CORE_VENDORS if cv not in agg_core_vendor],
        "byCategory": byCategory,
    }

    # ── Build STORE_INVENTORY (per-store, same shape) ──
    store_inv_out = {}
    for sk in ["dracut", "pepperell", "groton"]:
        s = store_inventory[sk]
        other_lst = _sorted_vendor_list(s["other_vendor"])
        by_cat_out = []
        for cg in cat_order:
            c = s["by_cat"].get(cg, {"brick": 0, "core": 0, "other": 0})
            by_cat_out.append({"group": cg, "brick": c["brick"], "core": c["core"], "other": c["other"]})
        store_inv_out[sk] = {
            "total": s["total"], "brick": s["brick"], "core": s["core"], "other": s["other"],
            "brickVendors": _sorted_vendor_list(s["brick_vendor"]),
            "coreVendors":  _sorted_vendor_list(s["core_vendor"]),
            "otherVendors": other_lst[:15],
            "otherVendorsFull": len(other_lst),
            "byCategory": by_cat_out,
        }

    return product_data, inventory_mix, store_inv_out


def fetch_lit_alerts_data():
    """Fetch Lit Alerts market data for brick vendors.
    Returns LIT_ALERTS_DATA and MARKET_TREND_DATA structures.
    """
    if not LIT_ALERTS_TOKEN:
        print("\n[3/3] Skipping Lit Alerts — no token available")
        return None, None

    print("\n[3/3] Fetching Lit Alerts market data...")
    # One-time diagnostic probe so we can see what the server is returning on 500s.
    lit_alerts_probe()
    today = date.today()

    # ── LIT_ALERTS_DATA: Retailer distribution per vendor ──
    vendor_retailers = {}
    for vk, vinfo in BRICK_VENDORS.items():
        for brand_id in vinfo["lit_ids"]:
            print(f"  Brand {vinfo['name']} (id={brand_id})...")
            # Get retailer distribution for this brand
            # Correct endpoint: /brand/{brandId}/retailers (NOT /brand/{id}/events — that path doesn't exist)
            # NO `returnDollarValues` param. In run #17's log, /market/brands
            # with {beginDate, endDate, state} returned full results with
            # estimatedAmount populated (probe); adding returnDollarValues=true
            # to the same endpoint emptied the response. estimatedAmount is
            # included by default.
            data = lit_alerts_fetch(f"/brand/{brand_id}/retailers", {
                "beginDate": (today - timedelta(days=90)).strftime("%m-%d-%Y"),
                "endDate": today.strftime("%m-%d-%Y"),
                "state": "MA",
            })
            # Aggregate retailer presence for this vendor.
            # Lit Alerts uses "results" as the list key (NOT "data"); rows have estimatedAmount (NOT revenue/totalSales).
            rows = None
            if isinstance(data, dict):
                rows = data.get("results") or data.get("data")
            if rows:
                vendor_retailers.setdefault(vk, {}).setdefault(brand_id, rows)

    # ── MARKET_TREND_DATA: Monthly sales by vendor ──
    # IMPORTANT: iterate using calendar-month arithmetic, NOT days=30*n.
    # The old approach drifted (30 days != 1 month) and could skip an entire
    # calendar month — that's why March 2026 went missing on Apr 13.
    market_trend_months = []
    market_trend_vendors = defaultdict(dict)

    # Build list of (year, month) tuples for the last 15 months (14 completed + current MTD)
    def add_months(y, m, delta):
        idx = y * 12 + (m - 1) + delta
        return idx // 12, (idx % 12) + 1

    cur_y, cur_m = today.year, today.month
    month_pairs = []
    for back in range(14, -1, -1):
        month_pairs.append(add_months(cur_y, cur_m, -back))

    for (y, m) in month_pairs:
        month_start = date(y, m, 1)
        # Last day of this month
        next_y, next_m = add_months(y, m, 1)
        next_month_start = date(next_y, next_m, 1)
        last_day = next_month_start - timedelta(days=1)
        # Don't query past today — for the current month, cap at today
        month_end = min(last_day, today)

        month_key = month_start.strftime("%Y-%m")
        if month_key not in market_trend_months:
            market_trend_months.append(month_key)

        print(f"  Market trend: {month_key}...")
        # See note above — no returnDollarValues param.
        data = lit_alerts_fetch("/market/brands", {
            "beginDate": month_start.strftime("%m-%d-%Y"),
            "endDate": month_end.strftime("%m-%d-%Y"),
            "state": "MA",
        })
        # Lit Alerts response shape: {"results": [{"name":..., "id":..., "estimatedAmount":...}, ...]}
        rows = (data.get("results") or data.get("data")) if isinstance(data, dict) else None
        if rows:
            for brand_entry in rows:
                brand_id = brand_entry.get("id")
                for vk, vinfo in BRICK_VENDORS.items():
                    if brand_id in vinfo["lit_ids"]:
                        revenue = (
                            brand_entry.get("estimatedAmount")
                            or brand_entry.get("revenue")
                            or brand_entry.get("totalSales")
                            or 0
                        )
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
    product_data, inventory_mix, store_inventory = fetch_inventory_data()
    lit_alerts_data, market_trend = fetch_lit_alerts_data()

    # ── VALIDATION GUARDS (hard fail before writing HTML) ──
    errors = []

    # Guard 1: every Dutchie store must have in-stock SKUs
    for sk in ["dracut", "pepperell", "groton"]:
        s = store_inventory.get(sk, {})
        if s.get("total", 0) == 0:
            errors.append(f"Dutchie: store={sk} returned 0 SKUs")

    # Guard 2: every brick-tab vendor should have at least 1 SKU across all stores
    for vk, vinfo in BRICK_VENDORS.items():
        if product_data["vendors"].get(vk, {}).get("totalSkus", 0) == 0:
            errors.append(f"Dutchie: brick-vendor {vk} ({vinfo['name']}) has 0 SKUs across all stores")

    # Guard 3: Lit Alerts market trend must have vendor data
    if not market_trend:
        errors.append("Lit Alerts: market_trend is None (fetch returned nothing)")
    else:
        if not market_trend.get("vendors"):
            errors.append("Lit Alerts: MARKET_TREND_DATA.vendors is EMPTY — no brand matches across all months")
        else:
            missing_vendors = [vk for vk in BRICK_VENDORS if vk not in market_trend["vendors"]]
            if missing_vendors:
                errors.append(f"Lit Alerts: MARKET_TREND missing vendors: {missing_vendors}")

    if errors:
        print("\n❌ VALIDATION FAILED — refusing to write HTML:")
        for e in errors:
            print(f"   • {e}")
        raise RuntimeError(f"Brick House refresh failed validation ({len(errors)} error(s)). HTML not updated. See log above.")

    print("\n✓ All validation guards passed")

    # Update HTML constants
    print("\nUpdating HTML file...")

    # PRODUCT_DATA — tab-vendor per-category detail
    html = replace_js_const(html, "PRODUCT_DATA", json.dumps(product_data, indent=2, ensure_ascii=True))
    print("  Updated PRODUCT_DATA")

    # INVENTORY_MIX — aggregate (brickVendors, coreVendors, otherVendors, byCategory)
    html = replace_js_const(html, "INVENTORY_MIX", json.dumps(inventory_mix, indent=2, ensure_ascii=True))
    print("  Updated INVENTORY_MIX")

    # STORE_INVENTORY — per-store breakdown (drives the per-store drill-in cards)
    html = replace_js_const(html, "STORE_INVENTORY", json.dumps(store_inventory, indent=2, ensure_ascii=True))
    print("  Updated STORE_INVENTORY")

    # MARKET_TREND_DATA (if Lit Alerts succeeded)
    if market_trend:
        html = replace_js_const(html, "MARKET_TREND_DATA", json.dumps(market_trend, indent=2, ensure_ascii=True))
        print("  Updated MARKET_TREND_DATA")
    else:
        print("  Skipped MARKET_TREND_DATA (Lit Alerts unavailable)")

    # Write
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDone! Updated {HTML_FILE}")
    print(f"  Product data: {sum(v['totalSkus'] for v in product_data['vendors'].values())} total SKUs (tab vendors)")
    print(f"  Inventory agg: {inventory_mix['totalActive']} active ({inventory_mix['totalBrick']} brick / {inventory_mix['totalCore']} core / {inventory_mix['totalOther']} other)")
    for sk in ["dracut", "pepperell", "groton"]:
        s = store_inventory[sk]
        print(f"  {sk}: {s['total']} total ({s['brick']}/{s['core']}/{s['other']})")


if __name__ == "__main__":
    main()
