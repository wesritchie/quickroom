# THCFO Dashboard Sitemap (v2 — locked Apr 26, 2026)

Seven pages, each a self-contained HTML file with internal sidebar nav for sections. Sister design system to Wes' QuickRoom dashboards.

## Cross-page persistent state

| Toggle | Default | Affects |
|---|---|---|
| **Cap-lift scenario** | Phase 1 (5 stores, Jun 2026 – Jun 2027) | Valuation, Verticalization, Operations, Debt |
| **Buyer-type lens** | MA at-cap acquirer (cap-lift driven) | Valuation, Profitability |
| **EBITDA lens** | Strategic / Pro-Forma | Valuation, Profitability |
| **Period selector** | Latest closed month | Most pages |

## Pages

### 1. Overview (`index.html`)
North-star landing — 6–8 highest-level KPIs, one-line health indicator per domain, links to all six dashboards.

### 2. Valuation (`valuation.html`) ← **first build target**
Strategic page. Sections:
- Headline range (live revenue × multiple, with cap-lift and buyer-type controls)
- Methodologies (4: revenue, EBITDA matrix, asset, projected)
- Comps tracker (public MSO trading + MA private transactions)
- Buyer-type lens (single-state / MA at-cap / MSO / ESOP)
- Cap-lift scenarios (3 today / 5 from Jun 2026 / 6 from Jun 2027 / sister-entity speculative)
- Strategic synergy add-back layer (collapsible, role-by-role)
- Methodology footnotes

### 3. Profitability (`profitability.html`)
P&L stack with EBITDA bridge. Sections:
- Revenue (consolidated + by store + farm wholesale broken out)
- Gross margin (book vs. economic — 471(c) reconciliation)
- Store contribution margin (Dracut / Pep / Groton + Corporate)
- Operating income → EBIT → EBITDA
- EBITDA bridge (Book → Conservative-Adjusted → Strategic-Adjusted)
- Owner-comp dual lens
- Add-backs detail (line-itemed, footnoted)
- **Capital allocation / ROIC by store** *(added)*
- Variance vs. prior period
- Educational layer

### 4. Verticalization (`verticalization.html`) *(new — added Apr 26)*
Farm economics, integration value, make-vs-buy. Sections:
- Headline economics (in-house production, % of retail revenue, margin uplift $, standalone farm contribution margin)
- Make-vs-buy analysis ($/lb in-house vs. wholesale comparable, "if we bought instead" pro-forma)
- Capacity & utilization (current vs. designed, indoor / outdoor / greenhouse, Sept 2026 manufacturing license expansion)
- Wholesale revenue (farm to other dispensaries, customer concentration, margin)
- Standalone farm valuation (assets + cultivation license + brand + revenue × cultivator multiple)
- Strategic narrative (margin protection, supply security, brand differentiation, optionality)

### 5. Cash Flow & Liquidity (`cashflow.html`)
Sections:
- Current cash position
- Days cash on hand / runway
- Monthly cash flow statement (Operating / Investing / Financing)
- Weekly cashflow tracker (forward through end 2027)
- Cash conversion: book NI vs. cash from operations
- **Working capital cycle (DIO / DPO / CCC)** *(added — elevated to prominent metric set)*
- **Budget vs. actuals — forward operating view** *(added)*
- Educational layer

### 6. Debt & Capital Structure (`debt.html`)
Sections:
- Debt schedule (live, consolidated all sources)
- Total debt over time (deleveraging narrative)
- DSCR and interest coverage
- Maturity wall (next 12 / 24 / 36 months)
- By debt type (institutional / friendly notes / tax-payment-plan)
- Personal guarantee inventory
- Cap table summary
- Educational layer

### 7. Operations (`operations.html`)
Sections:
- Same-store sales (Dracut / Pep / Groton)
- Traffic / basket / mix (from Dutchie POS)
- Customer geography snapshot (link to full Geo Totem)
- Vertical integration mix (links to Verticalization page)
- **MA peer benchmarking (revenue per store, gross margin, growth — Lit Alerts)** *(added)*
- 471(c) explainer + book-to-tax bridge
- Buyer-type tax implication notes

## Build order

1. **Valuation** — first build (this session)
2. **Profitability** — second; produces EBITDA inputs back to Valuation
3. **Verticalization** — third; standalone farm valuation feeds back to Valuation asset-floor
4. **Cash Flow & Liquidity**
5. **Debt & Capital Structure**
6. **Operations**
7. **Overview** — last; summarizes everything above
