/* ============================================================================
   THCFO — Operations Data
   ============================================================================
   Sourced directly from the Dutchie POS API closing-report endpoint
   (/reporting/closing-report). FY 2025 figures verified against P&L revenue
   subtotals at consolidated level. To refresh, re-pull from Dutchie API
   month-by-month and update the byMonth arrays + recalculate aggregates.

   Note on customer count: Dutchie's customerCount is "unique customers within
   that period." When summing monthly customerCounts to a full year, repeat
   customers are double-counted. transactionCount is additive across periods
   and is the more reliable annual metric. For the dashboard, we present
   "Transactions per day" as the primary traffic indicator (each retail
   transaction ≈ 1 customer visit). Basket = Net Sales ÷ Transactions.

   Also includes a snapshot of the Rainbow Review's key Tree House Position
   metrics — peer comps that change daily and live on rainbow-review.html.
   ============================================================================ */

window.OPERATIONS_DATA = {

  meta: {
    last_updated: "2026-04-26",
    period: "FY 2025",
    primary_source: "Dutchie POS API · /reporting/closing-report",
    secondary_source: "Rainbow Review (rainbow-review.html) for MA peer comps",
    refresh_instructions: "Re-pull monthly closing-report data from Dutchie API; aggregate; update byStore values."
  },

  // -------------------------------------------------------------------------
  // FY 2025 STORE PERFORMANCE — verified via Dutchie API
  // -------------------------------------------------------------------------
  fy2025: {
    byStore: {
      dracut: {
        netSales: 5012295,
        grossSales: 5564000,           // approx grossSales unverified — placeholder
        transactionCount: 90226,
        sumMonthlyCustomers: 52971,    // sum-of-monthly-unique — for ratio/share only
        newCustomerSum: 11925,
        itemCount: 295728,
        daysOpen: 365,
        transactionsPerDay: 247,        // 90226 / 365
        avgBasket: 55.55                // netSales / transactions
      },
      pepperell: {
        netSales: 2489113,
        transactionCount: 51194,
        sumMonthlyCustomers: 25278,
        itemCount: 157000,
        daysOpen: 365,
        transactionsPerDay: 140,        // 51194 / 365
        avgBasket: 48.62                // netSales / transactions
      },
      groton: {
        netSales: 426192,
        transactionCount: 10492,
        sumMonthlyCustomers: 5799,
        newCustomerSum: 2298,
        itemCount: 30016,
        daysOpen: 334,                  // opened ~Feb 1, 2025 (partial year)
        transactionsPerDay: 31,         // 10492 / 334
        avgBasket: 40.62                // netSales / transactions
      }
    },
    portfolio: {
      netSales: 7927600,
      transactionCount: 151912,
      avgBasket: 52.18,                 // 7927600 / 151912
      avgTransactionsPerDay: 416        // 151912 / 365
    }
  },

  // -------------------------------------------------------------------------
  // RAINBOW REVIEW — daily peer comps
  // Updated when the Rainbow Review snapshot changes. The Rainbow Review
  // dashboard itself is the live source of truth — these values are a recent
  // snapshot used for the THCFO landing summary.
  // -------------------------------------------------------------------------
  rainbow_review: {
    snapshot_date: "2026-04-25",
    snapshot_label: "Yesterday (4/25)",

    market_overview: {
      total_market_revenue: 4100000,    // $4.1M yesterday
      active_retailers: 380,
      avg_revenue_per_store: 10800      // $10.8K per store yesterday
    },

    tree_house_rankings: {
      dracut:    { rank: 62,  movement: "+4",  movement_dir: "up",   total_stores: 380 },
      pepperell: { rank: 188, movement: "-4",  movement_dir: "down", total_stores: 380 },
      groton:    { rank: 325, movement: "+10", movement_dir: "up",   total_stores: 380 }
    },

    market_category_top: [
      { category: "Flower",     market_revenue: 1700000, market_pct: 42.0 },
      { category: "Vaporizers", market_revenue: 862100,  market_pct: 21.1 }
      // additional categories visible on Rainbow Review
    ],

    rainbow_review_url: "https://wesritchie.github.io/quickroom/rainbow-review.html"
  }

};
