/* ============================================================================
   THCFO — Comps Data
   ============================================================================
   This file holds the public MSO trading multiples and MA private transaction
   comps used by the Valuation page. Edit the values below and reload the page
   to refresh — no need to touch the HTML.

   REFRESH CADENCE:
   - Public MSOs: quarterly, after each earnings cycle (mid-Feb / May / Aug / Nov)
     Sources: SEC EDGAR (10-K/10-Q), New Cannabis Ventures, MacroTrends,
     Yahoo Finance, MJBizDaily
   - MA Private: monthly scan + ad hoc when deals are reported
     Sources: CCC public meeting agendas, MJBizDaily, broker conversations,
     public MSO 8-K filings, Viridian Capital reports

   CONFIDENCE LEVELS:
   - "high"   = publicly disclosed price/multiple (SEC filing, press release)
   - "medium" = industry intelligence (broker, peer operator, trade press)
   - "low"    = rumor or triangulated estimate
   ============================================================================ */

window.COMPS_DATA = {

  meta: {
    last_updated: "2026-04-26",
    next_refresh_due: "2026-07-26",
    refresh_owner: "Wes / next CFO session",
    primary_sources: [
      "SEC EDGAR (10-K, 10-Q, 8-K filings)",
      "MJBizDaily",
      "New Cannabis Ventures",
      "MacroTrends",
      "MA Cannabis Control Commission public records",
      "Viridian Capital Advisors reports"
    ]
  },

  // --------------------------------------------------------------------------
  // PUBLIC MSO TRADING MULTIPLES
  // Tier-1 US multi-state operators. Use TTM revenue and current market cap.
  // P/S = Market Cap / TTM Revenue. EV/EBITDA from public-coverage analyst
  // estimates (refresh from latest available source).
  // --------------------------------------------------------------------------
  public_msos: [
    {
      name: "Curaleaf",
      ticker: "CURLF",
      ttm_revenue_b: 1.27,
      market_cap_b: 1.62,
      ps_multiple: 1.3,
      ev_ebitda_multiple: 7.8,
      data_as_of: "Feb 2026",
      notes: "FY2025 reported. Premium to peer median per analyst coverage."
    },
    {
      name: "Green Thumb",
      ticker: "GTBIF",
      ttm_revenue_b: 1.20,
      market_cap_b: 2.0,
      ps_multiple: 1.7,
      ev_ebitda_multiple: 6.0,
      data_as_of: "Mar 2026",
      notes: "FY2025 reported. Normalized EBITDA $348M."
    },
    {
      name: "Trulieve",
      ticker: "TCNNF",
      ttm_revenue_b: 1.10,
      market_cap_b: 0.9,
      ps_multiple: 0.8,
      ev_ebitda_multiple: 4.5,
      data_as_of: "Apr 2026",
      notes: "Approximate; refresh from Q1 2026 reporting."
    },
    {
      name: "Verano",
      ticker: "VRNOF",
      ttm_revenue_b: 0.85,
      market_cap_b: 0.6,
      ps_multiple: 0.7,
      ev_ebitda_multiple: 4.0,
      data_as_of: "Apr 2026",
      notes: "Approximate; refresh from Q1 2026 reporting."
    },
    {
      name: "Cresco Labs",
      ticker: "CRLBF",
      ttm_revenue_b: 0.66,
      market_cap_b: 0.32,
      ps_multiple: 0.5,
      ev_ebitda_multiple: 4.0,
      data_as_of: "Mar 2026",
      notes: "Trading at $0.90/share. Lowest multiple among Tier-1 MSOs."
    }
  ],

  // --------------------------------------------------------------------------
  // MA PRIVATE TRANSACTIONS
  // Recent disclosed or triangulated MA cannabis acquisitions. Use revenue
  // multiples where computable; EBITDA multiples where the buyer disclosed.
  // For each entry, mark confidence and cite source.
  // --------------------------------------------------------------------------
  ma_private: [
    {
      target: "Bloom Brothers MA",
      buyer: "Undisclosed major operator",
      date: "2025",
      revenue_multiple: 1.5,
      ebitda_multiple: 3.5,
      buyer_type: "MSO",
      confidence: "medium",
      source: "Industry intel via Nathan Girard intro to Jade Green",
      notes: "Seller held paper post-close. Multiple is approximate."
    },
    {
      target: "(Add transaction)",
      buyer: "—",
      date: "—",
      revenue_multiple: null,
      ebitda_multiple: null,
      buyer_type: "—",
      confidence: "placeholder",
      source: "Add via CCC public records / MJBizDaily / broker intel",
      notes: ""
    },
    {
      target: "(Add transaction)",
      buyer: "—",
      date: "—",
      revenue_multiple: null,
      ebitda_multiple: null,
      buyer_type: "—",
      confidence: "placeholder",
      source: "Add via CCC public records / MJBizDaily / broker intel",
      notes: ""
    }
  ],

  // --------------------------------------------------------------------------
  // BLENDED MULTIPLE LOGIC
  // Headline range computation can blend public + private comps. Adjust the
  // weighting and the multiple ranges per buyer type here.
  // --------------------------------------------------------------------------
  blend: {
    public_weight: 0.4,
    private_weight: 0.6,
    notes: "Private transactions are weighted higher because they reflect actual willing-buyer / willing-seller pricing in MA, not public-market sentiment volatility."
  }

};
