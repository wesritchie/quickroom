/* ============================================================================
   THCFO — Quarterly Data
   ============================================================================
   SCOPE · RETAIL ONLY
   ───────────────────
   This file holds Dutchie-sourced retail performance data, aggregated to
   quarters per store and at the retail-portfolio level (sum of all three
   stores). It contains NO farm/wholesale/MACC revenue.

   Every comparison on the Quarterly Review page is apples-to-apples retail:
   store-vs-store, retail-portfolio-vs-retail-portfolio, retail-quarter-vs-
   prior-retail-quarter. Consolidated P&L (which includes farm) lives on
   Profitability and Verticalization, NOT here.

   DATA STRUCTURE
   ──────────────
   Each (entity, quarter) entry is a 10-element array, fixed positions:
     [0] netSales       (rounded to dollar)
     [1] grossSales     (rounded to dollar)
     [2] discount       (rounded to dollar)
     [3] cost           (rounded to dollar — product COGS only, no opex)
     [4] transactions   (integer)
     [5] items          (integer)
     [6] avgBasket      (2dp · netSales / transactions)
     [7] discountPct    (4dp · discount / grossSales)
     [8] grossMarginPct (4dp · (netSales-cost)/netSales — RETAIL product GM)
     [9] itemsPerTxn    (2dp)

   "Gross Margin" here is RETAIL PRODUCT margin from Dutchie cost field —
   excludes occupancy, payroll, and other opex. NOT the same as P&L gross
   margin or NOI margin. Use this for store-vs-store unit-economics
   comparison; use Profitability page for company-level P&L analysis.

   PORTFOLIO = sum of dracut + pepperell + groton.
   GROTON Q1-Q4 2024 = zeros (store opened Feb 2025).

   REFRESH WORKFLOW
   ────────────────
   When a new quarter completes:
     1. Wes prompts "pull Q[N] [YYYY] Dutchie quarterly"
     2. Claude pulls month-by-month closing-reports per store
     3. Aggregates to quarter, appends to byQuarter[entity][quarter]
     4. Updates meta.last_updated and meta.most_recent_quarter

   RECONCILIATION NOTES
   ────────────────────
   • Dracut FY 2025 retail: $5,012,294 (Dutchie) — matches operations-data.js
   • Pepperell FY 2025 retail: $2,489,112 (Dutchie) — matches operations-data.js
   • Groton FY 2025 retail: $544,015 (Dutchie) vs $426,192 stored in
     operations-data.js — $117,823 discrepancy. Dutchie API is authoritative.
     operations-data.js was a stale value and should be updated.
   ============================================================================ */

window.QUARTERLY_DATA = {

  meta: {
    last_updated: "2026-04-28",
    most_recent_quarter: "Q1 2026",
    source: "Dutchie POS API · /reporting/closing-report · monthly pulls aggregated to quarters",
    scope: "Retail only · 3 stores (Dracut, Pepperell, Groton). Excludes MACC farm/wholesale revenue.",
    quartersOrdered: [
      "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024",
      "Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025",
      "Q1 2026"
    ],
    fields: ["netSales","grossSales","discount","cost","transactions","items","avgBasket","discountPct","grossMarginPct","itemsPerTxn"],
    consolidation_note: "Dutchie data is per-store retail. Even FY 2024 Dutchie data is retail (Dracut + Pepperell, since Groton wasn't open). NECC FY 2024 P&L matches retail Dutchie within ~0.5%; NECC FY 2025 consolidated includes ~$765K of MACC farm/wholesale revenue layered on top of retail.",
    groton_open_date: "Approx Feb 2025 — Q1-Q4 2024 entries are zeros.",
    reconciliation_notes: [
      "Dracut FY 2025: $5,012,294 (Dutchie) ≈ $5,012,295 (operations-data.js) — match",
      "Pepperell FY 2025: $2,489,112 (Dutchie) ≈ $2,489,113 (operations-data.js) — match",
      "Groton FY 2025: $544,015 (Dutchie fresh pull) vs $426,192 (operations-data.js) — Dutchie authoritative; operations-data.js stale by $117,823"
    ]
  },

  // -------------------------------------------------------------------------
  // BY-QUARTER, BY-ENTITY · 10-position arrays (see header for field map)
  // -------------------------------------------------------------------------
  byQuarter: {

    portfolio: {
      "Q1 2024": [1975098, 2129134, 149724,  916292, 35416, 108613, 55.77, 0.0703, 0.5361, 3.07],
      "Q2 2024": [2193010, 2377477, 179051, 1029868, 40115, 129390, 54.67, 0.0753, 0.5304, 3.23],
      "Q3 2024": [2228646, 2409396, 174556, 1012500, 41541, 128626, 53.65, 0.0724, 0.5457, 3.10],
      "Q4 2024": [2116357, 2323078, 199518,  958464, 37818, 118142, 55.96, 0.0859, 0.5471, 3.12],
      "Q1 2025": [1866191, 2069658, 197525,  816056, 34125, 103731, 54.69, 0.0954, 0.5627, 3.04],
      "Q2 2025": [2013530, 2268835, 249519,  872612, 38512, 122091, 52.28, 0.1100, 0.5666, 3.17],
      "Q3 2025": [2071046, 2312152, 235422,  932592, 40148, 132960, 51.59, 0.1018, 0.5497, 3.31],
      "Q4 2025": [2094654, 2322295, 221634,  974390, 39976, 130190, 52.40, 0.0954, 0.5348, 3.26],
      "Q1 2026": [1866481, 2071255, 198546,  865699, 35427, 108247, 52.69, 0.0959, 0.5362, 3.06]
    },

    dracut: {
      "Q1 2024": [1335709, 1429875,  91645, 620240, 22144, 71389, 60.32, 0.0641, 0.5356, 3.22],
      "Q2 2024": [1438455, 1557413, 115767, 675993, 24487, 83621, 58.74, 0.0743, 0.5301, 3.41],
      "Q3 2024": [1459687, 1572210, 109024, 662865, 25282, 83110, 57.74, 0.0693, 0.5459, 3.29],
      "Q4 2024": [1396008, 1519957, 119793, 626681, 23213, 77014, 60.14, 0.0788, 0.5511, 3.32],
      "Q1 2025": [1180336, 1291270, 107959, 510020, 20042, 64207, 58.89, 0.0836, 0.5679, 3.20],
      "Q2 2025": [1250595, 1387783, 134092, 538326, 22041, 72334, 56.74, 0.0966, 0.5695, 3.28],
      "Q3 2025": [1290073, 1432953, 139627, 584917, 23020, 79470, 56.04, 0.0974, 0.5466, 3.45],
      "Q4 2025": [1291291, 1416942, 122375, 593809, 23123, 78582, 55.84, 0.0864, 0.5401, 3.40],
      "Q1 2026": [1143999, 1258461, 110941, 526439, 20069, 63333, 57.00, 0.0882, 0.5398, 3.16]
    },

    pepperell: {
      "Q1 2024": [639389, 699259, 58079, 296052, 13272, 37224, 48.18, 0.0831, 0.5370, 2.80],
      "Q2 2024": [754556, 820064, 63284, 353874, 15628, 45769, 48.28, 0.0772, 0.5310, 2.93],
      "Q3 2024": [768959, 837186, 65532, 349635, 16259, 45516, 47.29, 0.0783, 0.5453, 2.80],
      "Q4 2024": [720349, 803120, 79725, 331783, 14605, 41128, 49.32, 0.0993, 0.5394, 2.82],
      "Q1 2025": [631011, 715987, 82166, 278424, 12829, 36291, 49.19, 0.1148, 0.5588, 2.83],
      "Q2 2025": [612640, 703699, 88654, 261672, 12876, 39559, 47.58, 0.1260, 0.5729, 3.07],
      "Q3 2025": [618691, 694798, 74301, 275946, 12938, 41228, 47.82, 0.1069, 0.5540, 3.19],
      "Q4 2025": [626770, 700757, 71871, 294897, 12551, 38969, 49.94, 0.1026, 0.5295, 3.10],
      "Q1 2026": [551986, 618880, 64850, 256054, 11258, 34086, 49.03, 0.1048, 0.5361, 3.03]
    },

    groton: {
      "Q1 2024": [     0,      0,     0,     0,    0,     0,    0,     0,     0,    0],
      "Q2 2024": [     0,      0,     0,     0,    0,     0,    0,     0,     0,    0],
      "Q3 2024": [     0,      0,     0,     0,    0,     0,    0,     0,     0,    0],
      "Q4 2024": [     0,      0,     0,     0,    0,     0,    0,     0,     0,    0],
      "Q1 2025": [ 54844,  62401,  7400, 27612, 1254,  3233, 43.74, 0.1186, 0.4965, 2.58],
      "Q2 2025": [150295, 177353, 26773, 72614, 3595, 10198, 41.81, 0.1510, 0.5169, 2.84],
      "Q3 2025": [162283, 184401, 21494, 71728, 4190, 12262, 38.73, 0.1166, 0.5580, 2.93],
      "Q4 2025": [176593, 204596, 27389, 85684, 4302, 12639, 41.05, 0.1339, 0.5148, 2.94],
      "Q1 2026": [170496, 193914, 22755, 83206, 4100, 10828, 41.58, 0.1173, 0.5120, 2.64]
    }
  },

  // -------------------------------------------------------------------------
  // PORTFOLIO CATEGORY MIX BY QUARTER · net sales $ per category
  // (Per-store category mix not currently tracked; can be added if needed)
  // -------------------------------------------------------------------------
  portfolioCategoryMix: {
    "Q1 2024": {"Accessories":20192,"Beverage":39235,"CBD":8054,"Concentrate":40026,"Edible":226700,"Flower":654724,"Pre Roll":377525,"Tincture":14229,"Topicals":882,"Vape Cartridge":591867},
    "Q2 2024": {"Accessories":19307,"Beverage":66606,"CBD":10939,"Concentrate":41355,"Edible":241481,"Flower":744064,"Pre Roll":451425,"Tincture":5865,"Topicals":400,"Vape Cartridge":609511},
    "Q3 2024": {"Accessories":22698,"Beverage":80021,"CBD":11117,"Concentrate":48367,"Edible":251039,"Flower":722693,"Pre Roll":430201,"Tincture":3083,"Vape Cartridge":657063,"Topicals":1496},
    "Q4 2024": {"Accessories":27332,"Beverage":79474,"CBD":10485,"Concentrate":39899,"Edible":270485,"Flower":629989,"Pre Roll":386350,"Tincture":789,"Topicals":1747,"Vape Cartridge":669369},
    "Q1 2025": {"Accessories":19920,"Beverage":90377,"CBD":6100,"Concentrate":46485,"Edible":231324,"Flower":594309,"Pre Roll":311494,"Topicals":2018,"Vape Cartridge":563419,"Tincture":98},
    "Q2 2025": {"Accessories":25172,"Beverage":84821,"CBD":6103,"Concentrate":37717,"Edible":219968,"Flower":661121,"Pre Roll":400119,"Topicals":3090,"Vape Cartridge":572913},
    "Q3 2025": {"Accessories":25182,"Beverage":88138,"CBD":4141,"Concentrate":32115,"Edible":247312,"Flower":636011,"Pre Roll":423353,"Topicals":4134,"Vape Cartridge":607369,"Tincture":1925},
    "Q4 2025": {"Accessories":28455,"Beverage":92265,"CBD":7672,"Concentrate":31004,"Edible":233765,"Flower":624669,"Pre Roll":396270,"Tincture":5599,"Topicals":2178,"Vape Cartridge":672130},
    "Q1 2026": {"Accessories":18396,"Beverage":88581,"CBD":4411,"Concentrate":30298,"Edible":228499,"Flower":552195,"Pre Roll":307148,"Tincture":5461,"Topicals":1974,"Vape Cartridge":628900}
  }

};
