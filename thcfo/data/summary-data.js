/* ============================================================================
   THCFO — Summary Data (Cross-Page Single Source of Truth)
   ============================================================================
   This file holds company-level facts used across multiple dashboard pages.
   It is the authoritative source for: TTM revenue, EBITDA lenses, term debt,
   valuation parameters, and other cross-page numbers that previously lived
   hardcoded in HTML and drifted out of sync.

   ARCHITECTURAL PRINCIPLE:
   Every page that displays a value also defined here should READ from this
   file rather than hardcoding the value. When this file is updated, every
   page that reads from it reflects the new reality on next load.

   COMPANION DATA FILES:
   - ap-aging-data.js    · AP balances, risk-lens categorization, trajectory
   - operations-data.js  · Per-store Dutchie POS metrics, Rainbow Review snap
   - comps-data.js       · Public MSO + MA private valuation comps

   PAGES THAT DEPEND ON THIS FILE:
   - index.html (Overview)              · all hero KPIs and module cards
   - valuation.html                     · TTM revenue, fwd revenue, EBITDA lenses
   - profitability.html                 · revenue, EBITDA, NOI
   - cashflow.html                      · NOI → operating cash bridge
   - debt.html                          · term debt schedule summary
   - operations.html                    · revenue context

   REFRESH WORKFLOW:
   1. New monthly close from QuickBooks → update fy2025 figures + ebitda
   2. New debt facility added/retired   → update termDebt
   3. Cap-lift legislation amended      → update valuation.capLift
   4. Update meta.last_updated and add a changelog note
   ============================================================================ */

window.SUMMARY_DATA = {

  meta: {
    last_updated: "2026-04-26",
    fy_period: "FY 2025",
    next_close_pending: "Feb / March 2026 monthly close"
  },

  // -------------------------------------------------------------------------
  // CORE COMPANY FINANCIALS · FY 2025
  // From QuickBooks closed P&L. Update after each monthly close.
  // -------------------------------------------------------------------------
  fy2025: {
    totalRevenue: 8810261,
    revenueGrowthYoY: 0.030,            // +3.0% vs. FY24
    grossProfitBook: 1041925,
    grossMarginBook: 0.118,             // 11.8%
    grossMarginEconomic: 0.597,         // ~59.7% — 471(c)-adjusted
    netOperatingIncome: 1022662,
    netIncome: 1022662,
    operatingMargin: 0.116
  },

  fy2024: {
    totalRevenue: 8556306,              // NECC standalone
    netOperatingIncome: 376295,
    netIncome: 376295
  },

  // -------------------------------------------------------------------------
  // MONTHLY TIME SERIES
  // Append a new entry to monthly[YYYY] when each month closes (~20th of
  // following month). Preserves history; enables MoM and YoY trend analysis.
  //
  // 2024 entries reflect NECC standalone P&L (pre-MACC consolidation; MACC
  // operated on separate books with arms-length transfer pricing through
  // mid-2024). 2025 entries reflect fully-consolidated NECC + MACC.
  // 2026 entries will be appended as monthly closes complete; Feb/March 2026
  // are pending at time of this dashboard build.
  // -------------------------------------------------------------------------
  monthly: {
    "2024": [
      { month: "2024-01", revenue: 637540,  cogs: 645004,  grossProfit:  -7463, noi:  -9367, source: "NECC standalone P&L by month" },
      { month: "2024-02", revenue: 636506,  cogs: 614615,  grossProfit:  21891, noi:  20664, source: "NECC standalone P&L by month" },
      { month: "2024-03", revenue: 709125,  cogs: 668170,  grossProfit:  40955, noi:  40900, source: "NECC standalone P&L by month" },
      { month: "2024-04", revenue: 711797,  cogs: 647268,  grossProfit:  64529, noi:  64386, source: "NECC standalone P&L by month" },
      { month: "2024-05", revenue: 761967,  cogs: 747895,  grossProfit:  14072, noi:  14072, source: "NECC standalone P&L by month" },
      { month: "2024-06", revenue: 729143,  cogs: 705866,  grossProfit:  23277, noi:  23277, source: "NECC standalone P&L by month" },
      { month: "2024-07", revenue: 809648,  cogs: 676438,  grossProfit: 133210, noi: 133210, source: "NECC standalone P&L by month" },
      { month: "2024-08", revenue: 779849,  cogs: 642079,  grossProfit: 137770, noi: 137770, source: "NECC standalone P&L by month" },
      { month: "2024-09", revenue: 651844,  cogs: 685247,  grossProfit: -33403, noi: -34603, source: "NECC standalone P&L by month" },
      { month: "2024-10", revenue: 720786,  cogs: 666052,  grossProfit:  54734, noi:  53250, source: "NECC standalone P&L by month" },
      { month: "2024-11", revenue: 683496,  cogs: 734872,  grossProfit: -51376, noi: -51660, source: "NECC standalone P&L by month" },
      { month: "2024-12", revenue: 724604,  cogs: 729730,  grossProfit:  -5126, noi: -15603, source: "NECC standalone P&L by month" }
    ],
    "2025": [
      { month: "2025-01", revenue: 659005,  cogs: 611927,  grossProfit:  47078, noi:  45878, source: "QB P&L by month · consolidated" },
      { month: "2025-02", revenue: 662332,  cogs: 672438,  grossProfit: -10106, noi: -11306, source: "QB P&L by month · consolidated" },
      { month: "2025-03", revenue: 692386,  cogs: 661663,  grossProfit:  30723, noi:  29463, source: "QB P&L by month · consolidated" },
      { month: "2025-04", revenue: 746941,  cogs: 781953,  grossProfit: -35012, noi: -35012, source: "QB P&L by month · consolidated" },
      { month: "2025-05", revenue: 790926,  cogs: 696338,  grossProfit:  94588, noi:  93388, source: "QB P&L by month · consolidated" },
      { month: "2025-06", revenue: 752087,  cogs: 626754,  grossProfit: 125333, noi: 124133, source: "QB P&L by month · consolidated" },
      { month: "2025-07", revenue: 805644,  cogs: 606982,  grossProfit: 198662, noi: 198662, source: "QB P&L by month · consolidated" },
      { month: "2025-08", revenue: 722377,  cogs: 627943,  grossProfit:  94434, noi:  93234, source: "QB P&L by month · consolidated" },
      { month: "2025-09", revenue: 769434,  cogs: 589756,  grossProfit: 179678, noi: 178478, source: "QB P&L by month · consolidated" },
      { month: "2025-10", revenue: 775799,  cogs: 655754,  grossProfit: 120045, noi: 118845, source: "QB P&L by month · consolidated" },
      { month: "2025-11", revenue: 685159,  cogs: 599939,  grossProfit:  85219, noi:  82204, source: "QB P&L by month · consolidated" },
      { month: "2025-12", revenue: 748173,  cogs: 636890,  grossProfit: 111283, noi: 104696, source: "QB P&L by month · consolidated" }
    ],
    "2026": [
      // Append next entry when Feb 2026 closes:
      // { month: "2026-02", revenue: ..., cogs: ..., grossProfit: ..., noi: ..., source: "QB P&L by month · consolidated" }
    ]
  },

  // -------------------------------------------------------------------------
  // CASH FLOW · FY 2025
  // From statement of cash flows.
  // -------------------------------------------------------------------------
  cashFlow: {
    netCashFromOps: 551202,
    netCashFromInvesting: -44578,
    netCashFromFinancing: -513976,
    netChangeInCash: -7351,
    cashConversionRatio: 0.539,         // 54% of book NI converted to cash
    inventoryBuildAbsorption: 555886,   // cannabis inventory growth — drove the gap
    dscr: 4.15,                         // on Strategic EBITDA
    interestCoverage: 4.33,
    workingCapitalCycle: {
      dioBook: 69, dpoBook: 80, dso: 7, cccBook: -4,
      dioEconomic: 151, dpoEconomic: 175, cccEconomic: -17
    }
  },

  // -------------------------------------------------------------------------
  // EBITDA · Three Lenses (from Profitability page methodology)
  // -------------------------------------------------------------------------
  ebitda: {
    operating: 1309022,                 // Book EBITDA pre-adjustments
    conservative: 1300000,
    mid: 1650000,
    strategic: 1968186,                 // Internal calculation, strategic-buyer view
    strategicMargin: 0.223,             // 22.3% of revenue
    yoyMarginExpansion: 1.72            // +172% NOI YoY
  },

  // -------------------------------------------------------------------------
  // TERM DEBT · current schedule
  // From signed debt schedule. Update when facilities are added/retired.
  // (Future: migrate to debt-schedule-data.js with per-facility detail)
  // -------------------------------------------------------------------------
  termDebt: {
    totalOutstanding: 693000,
    annualService: 474528,
    monthlyService: 39544,
    facilityCount: 5,
    rateRangeText: "0% – 15%",
    weightedAvgRate: 0.1020,
    annualInterestExpense: 70670,
    netDeleveragingFY25: 524000,
    institutionalRetiredFY25: 876386,
    friendlyAddedFY25: 381000,
    refinancingRiskMonths: 36           // no refi events in next 36 months
  },

  // -------------------------------------------------------------------------
  // VERTICALIZATION SUMMARY
  // From verticalization page. Future: migrate to verticalization-data.js
  // -------------------------------------------------------------------------
  verticalization: {
    farmDerivedRevenueTotal: 1894835,
    farmDerivedRevenuePctOfTotal: 0.215,    // 21.5% of consolidated
    inHouseRetailMix: 0.145,                 // 14.5% of retail product sales
    integrationEconomicValue: 931000,        // annual margin uplift + wholesale + exchange
    standaloneFarmValueLow: 2500000,
    standaloneFarmValueHigh: 3500000,
    manufacturingLicenseExpected: "September 2026"
  },

  // -------------------------------------------------------------------------
  // VALUATION · range computation parameters
  // Used to compute the headline range across all supported scenarios on the
  // Valuation page.
  // -------------------------------------------------------------------------
  valuation: {
    ttmRevenue: 8810261,
    fwdRevenue: 10740000,                // Groton-mature run-rate
    // Multiple ranges across buyer types
    revenueMultiples: {
      msoLow:        0.8,
      msoHigh:       1.2,
      singleStateLow:  1.0,
      singleStateHigh: 1.5,
      maAcquirerLow:   1.5,
      maAcquirerHigh:  2.0,
      esopLow:         1.5,
      esopHigh:        2.0
    },
    // Cap-lift scenario premiums (multiplier on revenue range)
    capLiftPremiums: {
      preLow: 1.00,    preHigh: 1.00,
      phase1Low: 1.10, phase1High: 1.20,
      phase2Low: 1.15, phase2High: 1.25,
      sisterLow: 1.20, sisterHigh: 1.30   // speculative, pending counsel
    },
    // Computed: lowest possible × highest possible
    // Floor: ttmRevenue × msoLow × preLow      = $8.81M × 0.8 × 1.00 = $7,048,209
    // Ceil:  ttmRevenue × maAcquirerHigh × sisterHigh = $8.81M × 2.0 × 1.30 = $22,906,679
    // Default lens (for module headline): MA Acquirer × Phase 1
    defaultLens: { revLow: 1.5, revHigh: 2.0, capLow: 1.10, capHigh: 1.20 }
  },

  // -------------------------------------------------------------------------
  // CAP-LIFT LEGISLATION · Chapter 65 of Acts of 2026
  // Static narrative facts (rare changes).
  // -------------------------------------------------------------------------
  capLift: {
    actName: "Chapter 65 of Acts of 2026",
    capCurrent: 3,                       // pre-cap-lift
    capPhase1: 5,                        // Jun 2026 – Jun 2027 for non-social-equity
    capPhase2: 6,                        // Jun 2027+
    phase1EffectiveDate: "Late June 2026",
    phase2EffectiveDate: "Late June 2027"
  }

};
