/* ============================================================================
   THCFO — Docs Data (Provenance + Refresh Checklist)
   ============================================================================
   Two parallel lists displayed on the Overview page:

     LEFT  · currentSources       — the documents this dashboard is built from.
                                    Source-of-truth manifest. If a number on the
                                    dashboard isn't traceable to a doc here,
                                    something is wrong.

     RIGHT · pendingNextRefresh   — the documents required to bring the
                                    dashboard forward to the next monthly cut.
                                    Doubles as a self-imposed to-do list.

   STATUS TAXONOMY · pendingNextRefresh
     "awaiting-close"   — Books are not yet closed. Blocked on bookkeeping.
     "awaiting-upload"  — Doc exists somewhere, just needs to be fed to Claude.
     "auto-refresh"     — Live API pull. Claude can fetch on request.

   When a pending doc lands:
     1. Move the entry from pendingNextRefresh → currentSources
     2. Update its `period` to the new period covered
     3. Update meta.last_updated
   ============================================================================ */

window.DOCS_DATA = {

  meta: {
    last_updated: "2026-04-29",
    refresh_target: "May 2026 — Feb + March 2026 monthly close cut"
  },

  // -------------------------------------------------------------------------
  // LEFT COLUMN · What the dashboard is built from
  // -------------------------------------------------------------------------
  currentSources: [
    {
      name: "FY 2025 P&L by Month",
      source: "QuickBooks · consolidated NECC + MACC",
      period: "Jan – Dec 2025",
      lens: "Monthly trend, gross margin, NOI"
    },
    {
      name: "FY 2024 P&L by Month",
      source: "NECC standalone P&L",
      period: "Jan – Dec 2024",
      lens: "YoY comparison baseline"
    },
    {
      name: "Balance Sheet",
      source: "QuickBooks",
      period: "As of Dec 31, 2025",
      lens: "Equity, AP, term debt, working capital"
    },
    {
      name: "Statement of Cash Flows",
      source: "QuickBooks",
      period: "FY 2025",
      lens: "Cash bridge, DSCR, working capital cycle"
    },
    {
      name: "Debt Schedule",
      source: "Internal facility tracker",
      period: "Current (signed)",
      lens: "Outstanding, rates, service, amortization"
    },
    {
      name: "QB A/P Aging Summary",
      source: "QuickBooks · A/P Aging Summary Report",
      period: "As of Apr 29, 2026",
      lens: "Standard 30/60/90/91+ buckets · vendor-level · operating-vs-carried framing (<60d / >60d)"
    },
    {
      name: "AP Risk Lens",
      source: "Operational tracker · Sandbox NECC AP + Budget · Google Sheets",
      period: "Week ending Apr 24, 2026",
      lens: "Brick / Core / Payment Plan / Hold categorization"
    },
    {
      name: "Federal Tax Returns",
      source: "Tax counsel work product",
      period: "FY 2024 filed",
      lens: "§471(c) framework basis"
    },
    {
      name: "Dutchie POS Closing Reports",
      source: "Dutchie API · per-store · monthly + quarterly",
      period: "Jan 2024 – Mar 2026 (27 months · 9 quarters)",
      lens: "Revenue, transactions, basket, discounts, category mix"
    },
    {
      name: "Veriscan ID-Scan Data",
      source: "Veriscan API · all 3 locations",
      period: "FY 2025",
      lens: "Customer demographics, geography"
    },
    {
      name: "MA Market Snapshot",
      source: "Lit Alerts · Rainbow Review",
      period: "Trailing peer ranking",
      lens: "Competitive context"
    }
  ],

  // -------------------------------------------------------------------------
  // RIGHT COLUMN · What's required for the next refresh
  // -------------------------------------------------------------------------
  pendingNextRefresh: [
    {
      name: "Feb 2026 Monthly Close",
      source: "QuickBooks · P&L + balance sheet snapshot",
      period: "Feb 2026",
      status: "awaiting-close",
      blocker: "Bookkeeping"
    },
    {
      name: "March 2026 Monthly Close",
      source: "QuickBooks · P&L + balance sheet snapshot",
      period: "March 2026",
      status: "awaiting-close",
      blocker: "Bookkeeping"
    },
    {
      name: "April 2026 Monthly Close",
      source: "QuickBooks · when ready",
      period: "April 2026",
      status: "awaiting-close",
      blocker: "Bookkeeping"
    },
    {
      name: "Updated AP Aging",
      source: "Operational tracker · current week",
      period: "Week ending closer to refresh date",
      status: "awaiting-upload",
      blocker: "Wes"
    },
    {
      name: "Updated Debt Schedule",
      source: "If any facilities added or retired",
      period: "Current",
      status: "awaiting-upload",
      blocker: "Wes — only if changed"
    },
    {
      name: "Depreciation Schedule",
      source: "Tax / accounting work product",
      period: "FY 2025 finalized",
      status: "awaiting-upload",
      blocker: "Bookkeeping — refines EBITDA bridge"
    },
    {
      name: "2026 Operating Budget",
      source: "Internal forecast",
      period: "FY 2026",
      status: "awaiting-upload",
      blocker: "Wes — powers Budget vs Actuals"
    },
    {
      name: "Q2 2026 Dutchie Pull",
      source: "Dutchie API · all 3 stores · once Q2 2026 completes",
      period: "Q2 2026 (Apr–Jun)",
      status: "auto-refresh",
      blocker: "Auto — Claude can pull on request after Jun 2026"
    },
    {
      name: "Q1 2026 Veriscan Refresh",
      source: "Veriscan API · all 3 stores",
      period: "Q1 2026",
      status: "auto-refresh",
      blocker: "Auto — Claude can pull on request"
    },
    {
      name: "Refreshed MA Market Snapshot",
      source: "Lit Alerts · Rainbow Review",
      period: "Trailing peer ranking",
      status: "auto-refresh",
      blocker: "Auto — Claude can pull on request"
    }
  ]

};
