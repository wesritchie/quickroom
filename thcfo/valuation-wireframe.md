# Valuation Page — Wireframe

`dashboard/valuation.html` — the strategic page. First page to build.

## Page philosophy

**Revenue multiples are the headline; EBITDA is fluent secondary; comps drive the multiples; buyer type drives the synergies; cap-lift drives the upside.**

Wes's external-facing valuation argument is anchored on revenue, not EBITDA, because (a) 471(c) inventory capitalization distorts gross margin and EBITDA in ways a buyer's CPA doesn't always understand, (b) MSO buyers above the small-business threshold can't continue 471(c), so the EBITDA *they* would inherit is structurally lower than the EBITDA Tree House actually generates, and (c) revenue is dialect-free across buyer types. The page leads accordingly.

## Layout

Header pattern matches QuickRoom dashboards: project sidebar on the left, status pill at top, page title, persistent toggles for cap-lift scenario and buyer-type lens, then content sections in a single scrollable column.

## Internal sections (sidebar nav)

### 1. Headline Range
Big card. Live revenue-multiple range as the primary number. Format:
> **$10.2M – $14.3M** (most-likely range)
> **$8.8M – $17.6M** (full bracket)
> Based on TTM revenue of $8.81M × 1.0–2.0x revenue multiple

Below the headline: micro-toggles for the two persistent lenses (cap-lift scenario, buyer type) — same toggles in the page header but available inline so user can iterate without scrolling.

Sub-line: "Adjusted EBITDA-implied range: $5.9M – $11.7M" (smaller, footnoted, secondary). Note that EBITDA frame is shown but never headlines.

### 2. Methodologies (4-up grid)

**Methodology 1: Revenue Multiple (Primary)**
- TTM revenue input
- Multiple range: 1.0x / 1.25x / 1.5x / 2.0x (with cited comp range)
- Output: $X.XM – $Y.YM
- Source citations: list of recent MA cannabis transactions used to anchor multiple

**Methodology 2: EBITDA Multiple (Secondary)**
A 3 × 3 matrix:
- Rows: Conservative / Mid / Strategic Adjusted EBITDA
- Columns: 3.0x / 3.5x / 4.0x EBITDA multiple
- Cells show implied valuation
- Active cell (based on persistent EBITDA-lens toggle) highlighted

**Methodology 3: Asset Floor**
- Inventory at 80–90% of book
- Cash at face
- AR at 80–90% of book
- Tangible FF&E / leasehold improvements at discount
- License values (separate line — these are real, transferable intangibles)
- Output: floor range

**Methodology 4: Forward / Pro-Forma**
- Projected TTM revenue at Groton maturity ($10.74M per onboarding doc)
- Forward EBITDA scenarios
- Multiples applied to forward inputs
- Useful for "what we'll be worth in 12 months" view

### 3. Comps Tracker
Two sub-sections side by side:

**Public MSO Trading Multiples (live where possible)**
- Cresco Labs, Verano, Trulieve, Curaleaf, Green Thumb, etc.
- Current revenue multiple, EBITDA multiple, market cap
- Trend over last 12 months
- Source: ma-cannabis-market skill (Lit Alerts) + public market data

**MA Private Transaction Database (curated)**
- Recent MA cannabis transactions (Bloom Brothers / BB MA, others)
- Revenue / EBITDA / multiple paid (where disclosed)
- Buyer type
- Date
- Notes
- Source: ma-cannabis-intel skill + Wes's intelligence

Below the two: weighted-blend logic — the headline range is computed as a weighted average of public + private comps, with weights configurable.

### 4. Buyer-Type Lens
Toggle with four options. Each option modifies multiple range, applicable EBITDA lens, and synergy assumptions:

| Buyer Type | Multiple Range | EBITDA Lens | Synergy Assumption |
|---|---|---|---|
| **Single-state operator (≤3 stores)** | 1.0–1.5x rev / 3.0–3.5x EBITDA | Conservative | Minimal — they're scaling up |
| **MA operator at cap (cap-lift acquirer)** | 1.5–2.0x rev / 3.5–4.5x EBITDA | Strategic | Moderate — they have some overlap |
| **MSO (out-of-state, MA entry)** | 0.8–1.2x rev / 3.0–3.5x EBITDA | Conservative — 280E penalty | Low (different ops) but pays for license + footprint |
| **ESOP buyer** | 1.5–2.0x rev / N/A — uses different framework | N/A | Different value driver entirely (governance / employee continuity) |
| **Sub-20% strategic partner** | Implied valuation × ownership %, with control discount | Strategic | Partial / negotiated |

For each option, a one-paragraph explainer describes why these multiples and assumptions apply.

### 5. Cap-Lift Scenarios
Toggle with four options:

| Scenario | Description | Multiple Adjustment |
|---|---|---|
| **Pre-cap-lift (today)** | 3 stores, 1 farm, Tree House at the cap | Baseline |
| **Phase 1: 5 stores (Jun 2026 – Jun 2027)** | Cap-lift live, non-SE businesses limited to 5 | +10–20% premium for headroom |
| **Phase 2: 6 stores (Jun 2027+)** | Full cap, Tree House can hold 6 | +15–25% premium |
| **Sister-entity / unlimited (speculative)** | Sub-20% / no-control structuring (counsel review pending) | Premium TBD |

Each scenario has:
- Implied multiple range
- Number of stores at maturity
- Strategic narrative blurb

### 6. Strategic Synergy Add-Back Layer (collapsible / advanced)
Editable role-by-role table:

| Role | Current Comp | Replacement Cost | Synergy % | Add-Back $ |
|---|---|---|---|---|
| Wes (Co-CEO/CFO/GC/CRO) | $175,000 | $250,000 | 100% (full absorption) | $175,000 |
| Ture (Co-CEO/marketing) | $175,000 | $175,000 | 100% (full absorption) | $175,000 |
| Matt (HR/licensing) | $150,000 | $135,000 | 50% (partial absorption) | $75,000 |
| James (COO) | $120,000 | $175,000 | 100% (full absorption) | $120,000 |
| Jess (CPO/buyer) | $120,000 | $125,000 | 25% (partial — buying knowledge specific) | $30,000 |
| **Total** | $740,000 | $860,000 | — | **$575,000** |

Synergy % is the user-editable input. The example numbers above are illustrative — the actual numbers get set during the EBITDA module build with Wes.

Below the table: "Conservative lens shows replacement-cost normalization (typically modest add-back). Strategic lens shows full or partial role absorption (typically larger). Default external-facing presentation: Strategic."

### 7. Methodology Footnotes (collapsible)
Every number on the page has a footnote linking to source:
- Revenue from QB closed P&L (date)
- EBITDA from EBITDA build worksheet (date, version)
- Multiples from comps tracker (last refresh date)
- Cap-lift assumptions from Chapter 65 of Acts of 2026 (with Wes's read on §16(b)(ii))
- Buyer-type assumptions documented inline
- Synergy assumptions editable, defaults documented

## Inputs needed before HTML build

| Input | Source | Status |
|---|---|---|
| TTM revenue ($8.81M for 2025) | QB 2025 P&L | ✅ have |
| Adjusted EBITDA — Conservative | TBD — needs EBITDA build session | ⏳ pending |
| Adjusted EBITDA — Mid | TBD | ⏳ pending |
| Adjusted EBITDA — Strategic | $1.97M (Wes's calc) → up to $3M+ (gut) | partial |
| Public MSO multiples | live via skill / web research | ⏳ build into module |
| MA private transaction comps | ma-cannabis-intel skill + Wes input | ⏳ build into module |
| Asset floor inputs | Year-end BS | ✅ have (need to refresh post-close) |
| Forward revenue projection | Onboarding doc ($10.74M) | ✅ have |

## Decisions deferred to build session

- Charting library (Chart.js, recharts, or vanilla SVG) — leaning vanilla SVG for self-contained portability
- Whether comps tracker is live (calls skill) or static (curated CSV refreshed periodically)
- Default synergy % values for each role (will set during EBITDA build with Wes)
- Whether the "sister entity" scenario stays in the cap-lift toggle or gets footnoted out of view pending counsel
