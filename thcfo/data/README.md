# THCFO Data Files · Refresh Architecture

The dashboard's principle: **data values live in editable `.js` files in this folder. HTML pages read from those files and render dynamically. Refreshing data never requires editing HTML.**

This protects against the dashboard going stale. New report arrives → update one data file → every page that uses that data reflects the new reality on next page load.

## Current data files

| File | Pages that use it | Refresh cadence | Source |
|---|---|---|---|
| **`summary-data.js`** | Overview · Valuation · Profitability · Cash Flow · Debt · Operations | Monthly (after close) + ad hoc | QuickBooks closed P&L, balance sheet, debt schedule, statutory updates |
| `comps-data.js` | Valuation | Quarterly post-earnings · ad hoc on MA private deals | SEC EDGAR · MJBizDaily · CCC public records · broker conversations |
| `ap-aging-data.js` | Debt & Capital · Overview | Monthly close (standard 30/60/90) + Weekly (risk-lens categorization) | QuickBooks A/P Aging Summary Report · Sandbox NECC AP + Budget operational tracker |
| `operations-data.js` | Operations · Overview | Monthly (Dutchie POS pull) + Daily (Rainbow Review snapshot) | Dutchie POS API closing-report endpoint · Rainbow Review dashboard |

## The Overview page is now fully data-driven

`index.html` loads four data files and renders the entire page (hero KPIs, module cards, footer) from them. **No values are hardcoded in the Overview's HTML.** This means:

- When `summary-data.js` updates FY 2025 revenue, the Overview's Revenue KPI updates automatically.
- When `ap-aging-data.js` updates the AP categorization (Brick / Core / Payment Plan / Hold balances), the Overview's Operational Debt and Unmanaged Vendor Debt KPIs and Debt module card recompute automatically.
- When `operations-data.js` updates Dutchie POS aggregates, the Overview's Operations module card and the "best store rank" KPI update automatically.
- The Implied Valuation Range on the Overview is computed from `summary-data.js` valuation parameters using the same formula the Valuation page uses, so the two views can never drift.

## `summary-data.js` — single source of truth for cross-page facts

This is the most important data file. It holds company-level facts that appear on multiple pages — TTM revenue, EBITDA lenses, term debt summary, cash-flow metrics, valuation parameters, cap-lift legislative context. **Every page that displays any of these values should read from `summary-data.js` rather than hardcoding.**

The Overview is fully migrated to this pattern. Detail pages (Valuation, Profitability, Cash Flow, Debt, Operations) currently still hardcode many of these values inline. The next mechanical pass is to migrate each detail page to read from `summary-data.js` for cross-page facts. The pattern:

1. Add `<script src="data/summary-data.js"></script>` to the page head.
2. Replace hardcoded values with `<span id="...">—</span>` placeholders.
3. Add a small render function that populates from `window.SUMMARY_DATA`.

## Convention

- **File header** documents what's inside, where it comes from, refresh cadence, dependencies, and any nulls/placeholders.
- **`null` is a legitimate value.** It means "we don't know yet · don't display a fabricated number." The dashboard renders a "pending refresh" indicator rather than a fake value.
- **Each top-level `meta` block** carries `last_updated` and source attribution so the dashboard can display data freshness at the bottom of the relevant section.
- **Historical entries are append-only.** Trajectory arrays grow over time; old entries should never be edited unless an actual data correction is happening.
- **Computed values are derived at render time** rather than stored. For example: Operational Debt = Term Debt + Brick + Core + Payment Plan AP. Storing a separate `operationalDebt` field would create drift; computing at render time guarantees the Overview always reflects the latest underlying values.

## Refresh workflow

1. New source document arrives (QB report, operational tracker export, Dutchie pull, broker comp update, etc.).
2. Open the relevant `.js` file in this folder.
3. Update the relevant fields. For values that don't have a current data point, leave as `null`.
4. Update `meta.last_updated`.
5. For time-series files, append a new entry to the historical `trajectory` array.
6. Save and reload the dashboard page — every consumer reflects the new value.

## Files planned for future externalization

The dashboard's first build inlined some values directly in HTML on detail pages — those should be migrated to data files over time. The mechanical pattern in the Overview's `index.html` (load data files in head; render with a render function) is the template for each:

| Future data file | Pages it would feed | Notes |
|---|---|---|
| `pl-data.js` | Profitability · Verticalization · Cash Flow | Monthly P&L line items, per-store revenue, gross margin, EBITDA inputs detail |
| `cashflow-data.js` | Cash Flow & Liquidity | Statement of cash flows line items, working capital metrics, weekly forward projections |
| `debt-schedule-data.js` | Debt & Capital | Term debt facility-by-facility, deleveraging history, blended rate inputs |
| `valuation-data.js` | Valuation | (replaces hardcoded TTM revenue, lens values; merge with `summary-data.js`'s valuation block) |

Each migration is mechanical: extract values from HTML into a data file, replace HTML with empty render targets, add a render function. The pattern in `index.html` (Overview) is the working template.

## When the dashboard is hosted (GitHub Pages or similar)

The same pattern works hosted: data files are part of the repo, edits are committed alongside HTML changes, page loads pull data from the same origin. Future enhancement: data files could be regenerated by an automated job (e.g., scheduled fetch from QuickBooks API or Dutchie POS API) without manual intervention. The Overview's render function automatically reflects whatever values are in the data files at page load.
