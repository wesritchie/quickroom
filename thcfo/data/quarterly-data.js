/* ============================================================================
   THCFO — Quarterly Data
   ============================================================================
   ARCHITECTURE NOTE
   -----------------
   This file holds ONLY data that cannot be derived from summary-data.js.

   Company-wide quarterly P&L (Revenue / COGS / GP / NOI / margins) is
   computed dynamically by quarterly.html from window.SUMMARY_DATA.monthly.
   That keeps the monthly time series the single source of truth — when a
   new monthly close lands, the quarterly view rolls forward automatically
   with no edit to this file.

   What lives here:
     • Per-store quarterly Dutchie data (not in P&L, requires API pull)
     • Discount analysis by quarter (Dutchie API · awaiting pull)
     • Sales mix by quarter (Dutchie API · awaiting pull)
     • Notes about consolidation history affecting comparability

   REFRESH WORKFLOW
   ----------------
   When Wes prompts "pull Q[N] [YYYY] Dutchie quarterly", Claude pulls per-
   store closing reports for the three months in that quarter, sums to a
   quarterly total per store, and appends to storeQuarterly[storeName].
   Discount and mix sections same pattern.
   ============================================================================ */

window.QUARTERLY_DATA = {

  meta: {
    last_updated: "2026-04-27",
    most_recent_complete_quarter: "Q4 2025",
    consolidation_note: "FY 2024 = NECC standalone P&L (pre-MACC consolidation). FY 2025 onward = consolidated NECC + MACC. YoY comparisons across this boundary include scope expansion, not just same-store change.",
    farm_revenue_note: "Dutchie does not capture wholesale farm revenue (MACC sales to other dispensaries). Company-wide quarterly P&L does include farm revenue (it's in QuickBooks consolidated). Per-store sections cover retail Dutchie-tracked sales only."
  },

  // -------------------------------------------------------------------------
  // PER-STORE QUARTERLY · Dutchie POS
  // FY 2025 annual totals are known and locked from the verified FY 2025 pull
  // (see operations-data.js). Per-quarter breakouts require a fresh closing-
  // report pull at the quarterly granularity.
  // -------------------------------------------------------------------------
  storeQuarterly: {
    status: "pending",
    blocker: "Dutchie API pull · Q-level closing reports per store",
    instruction: "Prompt Claude: 'pull quarterly Dutchie data through Q1 2026'",

    // Annual totals (known) — used as a sanity check when quarterly data lands
    fy2025_annual_locked: {
      dracut:    { netSales: 5012295, transactionCount: 90226, avgBasket: 55.55 },
      pepperell: { netSales: 2489113, transactionCount: 51194, avgBasket: 48.62 },
      groton:    { netSales: 426192,  transactionCount: 10492, avgBasket: 40.62 }
    },

    // Per-quarter detail — populated when Dutchie pull runs
    // Shape: { dracut: { "Q1 2024": {netSales, transactionCount, avgBasket, discountPct}, ... }, ... }
    quarters: {
      dracut:    {},
      pepperell: {},
      groton:    {}
    }
  },

  // -------------------------------------------------------------------------
  // DISCOUNT ANALYSIS
  // -------------------------------------------------------------------------
  discounts: {
    status: "pending",
    blocker: "Dutchie API pull · discount fields from closing-report endpoint",
    rationale: "Quarterly discount % trend (gross sales → net sales bridge) and discount $ by quarter helps see whether margin compression is COGS-driven or promotional.",
    fields_to_pull: ["grossSales", "netSales", "discountAmount", "discountPct"],

    // Populated per quarter when pull runs
    quarters: {}
  },

  // -------------------------------------------------------------------------
  // SALES MIX BY QUARTER
  // -------------------------------------------------------------------------
  mix: {
    status: "pending",
    blocker: "Dutchie API pull · category/strain breakouts from closing-report endpoint",
    rationale: "Quarter-over-quarter mix shifts (flower → vape, sativa → indica, in-house vs. external brands) reveal customer behavior trends and inform purchasing decisions.",
    categories_to_track: ["Flower", "Vaporizers", "Pre-Rolls", "Edibles", "Concentrates", "Topicals", "Other"],

    quarters: {}
  },

  // -------------------------------------------------------------------------
  // FARM (WHOLESALE) QUARTERLY
  // Manually uploaded each monthly close from internal records. Not in Dutchie.
  // -------------------------------------------------------------------------
  farm: {
    status: "pending",
    blocker: "Manual upload · accumulates with each monthly close",
    rationale: "MACC wholesale revenue to other MA dispensaries plus exchange/trade transactions. Verticalization page covers the annual view; quarterly granularity is a TBD enhancement.",

    quarters: {}
  }

};
