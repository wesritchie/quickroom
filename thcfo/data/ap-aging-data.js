/* ============================================================================
   THCFO — AP Aging Data
   ============================================================================
   This file holds AP aging values used by the Debt & Capital page. Edit values
   below and reload the page to refresh — no HTML changes required.

   TWO LENSES are stored here:
   1. Standard 30/60/90 aging — sourced from QuickBooks A/P Aging Summary Report
      at close. Refresh after each monthly close.
   2. Internal risk-lens categorization (Brick / Core / Payment Plan / Hold) —
      sourced from the operational tracker (Sandbox NECC AP + Budget Google
      Sheet). Refresh weekly when the tracker is updated.

   REFRESH WORKFLOW:
   - When a new closed-month QB A/P Aging Summary Report arrives, update
     standard_aging.as_of, .total, and .buckets, and append a new entry to
     trajectory[].
   - When a new operational tracker export arrives, update risk_categorization
     (.as_of, .total, and the four .categories balances + vendor_counts).
   - Set null on any field where current data is not available; the dashboard
     will render a "pending refresh" indicator rather than fabricate a number.

   NULL = "we don't know yet · don't display a number." This is by design.
   ============================================================================ */

window.AP_AGING_DATA = {

  meta: {
    last_updated: "2026-04-26",
    last_close_period: "2026-01-31",
    feb_mar_close_status: "pending",
    operational_tracker_week_ending: "2026-04-24",
    operational_tracker_source: "Sandbox NECC AP + Budget · Google Sheets",
    refresh_owner: "Update on monthly close + weekly operational tracker refresh"
  },

  // -------------------------------------------------------------------------
  // STANDARD 30/60/90 AGING — last fully reconciled close
  // Source: QuickBooks A/P Aging Summary Report at close
  // -------------------------------------------------------------------------
  standard_aging: {
    as_of: "2026-01-31",
    total: 1788121,
    buckets: {
      current:  398376,
      d1_30:    242445,
      d31_60:   222889,
      d61_90:   156143,
      d91_plus: 768268
    }
  },

  // -------------------------------------------------------------------------
  // INTERNAL RISK-LENS CATEGORIZATION
  // Source: operational tracker (Sandbox NECC AP + Budget)
  // Set values to null when data is not currently available — dashboard will
  // render "pending refresh" indicator instead of fabricating numbers.
  // -------------------------------------------------------------------------
  risk_categorization: {
    as_of: "2026-04-24",
    total: 953545,
    last_tracker_export: "2026-04-26",
    notes: "Values from operational tracker (Sandbox NECC AP + Budget) week ending 2026-04-24. Brick + Core + Payment Plan combined = Controlled Debt $781,016. Hold = Uncontrolled Debt $172,529.",

    categories: {
      brick: {
        label: "Brick Vendors",
        risk_level: "wont_be_problem",
        risk_label: "Won't be a problem",
        balance: 200557,
        vendor_count: 8,
        description: "Core product vendors with agreed weekly payment cadence and product flow. Active commercial terms."
      },
      core: {
        label: "Core Vendors",
        risk_level: "wont_be_problem",
        risk_label: "Won't be a problem",
        balance: 380141,
        vendor_count: 18,
        description: "Recurring service and product vendors operating under standard terms. Active relationships."
      },
      payment_plan: {
        label: "Payment Plan Vendors",
        risk_level: "being_managed",
        risk_label: "Being managed",
        balance: 200319,
        vendor_count: 13,
        description: "Past-due balances under formal or informal repayment plans. Vendor has agreed to a structured paydown schedule."
      },
      hold: {
        label: "Hold Vendors",
        risk_level: "could_be_problem",
        risk_label: "Could become a problem",
        balance: 172529,
        vendor_count: 16,
        description: "Past-due balances without an active payment plan. Often disputed, paused, or under negotiation. Highest attention category."
      }
    }
  },

  // -------------------------------------------------------------------------
  // HISTORICAL TRAJECTORY
  // Append a new entry for each new reliable data point.
  // -------------------------------------------------------------------------
  trajectory: [
    { as_of: "2024-12-31", source: "BS year-end",        total_ap: 1695977 },
    { as_of: "2025-12-31", source: "BS year-end",        total_ap: 1703556 },
    { as_of: "2026-01-31", source: "QB A/P Aging Report", total_ap: 1788121 },
    { as_of: "2026-04-24", source: "Operational tracker (week ending)", total_ap: 953545 }
    // append next: { as_of: "2026-02-28", source: "QB A/P Aging Report", total_ap: ... }
  ]

};
