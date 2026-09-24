# Explainable BI & Financial Health Decision Support System for Kenyan SMEs

An academic Data Science prototype that turns raw, imperfect SME
transaction data into an **explainable** financial health assessment —
not just a dashboard. Every score, driver and recommendation is
traceable back to a specific formula, source column and set of
exclusions.

## 1. Purpose & Problem

Many Kenyan SMEs operate without structured financial reporting, so
owners often cannot answer: *What is happening? How healthy is the
business? Why? What should management do about it?* This system
answers all four questions from transaction-level data, while being
transparent about how reliable that data actually is.

## 2. Intended Users

SME owners/managers (primary), and academic reviewers assessing the
explainability and financial-analytics methodology (secondary).

## 3. System Architecture

```
Upload CSV -> Data Quality Assessment -> Cleaning/Validation ->
KPI Calculation -> Financial Health Score -> RAG Classification ->
Driver Identification -> Explainable Insights -> Recommendations ->
Executive Report
```

See `docs/technical_notes.md` for the full module-by-module breakdown,
every formula, and the scoring methodology.

```
app.py                 Streamlit entry point (upload + overview)
pages/                 One Streamlit page per functional area
config/settings.py     Every threshold/weight; all assumptions isolated & documented
src/data/               loader.py, cleaning.py, validation.py
src/analytics/          profitability, liquidity, growth, efficiency, inventory, kpis
src/health/              scoring.py, thresholds.py, rag.py
src/explainability/      drivers.py, explanations.py, recommendations.py
src/reporting/report.py Executive HTML report
tests/                  Unit tests for cleaning, KPIs, scoring, explainability
docs/technical_notes.md Full technical documentation
```

## 4. Dataset Structure

~2,287 transaction rows, 32 columns, transaction_type in
`{SALE, PURCHASE, EXPENSE, CUSTOMER_PAYMENT, SUPPLIER_PAYMENT, REFUND,
STOCK_ADJUSTMENT}`. The dataset intentionally contains duplicate
transaction IDs, mixed date formats, missing values, and an
inconsistent inventory trail — see Section 5.

## 5. Data-Quality Handling

The app keeps **raw data and analytical (validated) data as two
separate concepts**. Nothing is silently deleted: every excluded row
carries an `exclude_reason`, visible on the Data Quality page, and the
cleaned dataset is downloadable. Data Reliability and Financial Health
are always shown as two distinct indicators — a messy dataset does not
automatically imply an unhealthy business, and a healthy-looking score
is never presented as more reliable than the underlying data supports.

## 6. KPI Formulas & Financial Health Methodology

Fully documented in `docs/technical_notes.md`, including a table
comparing this implementation's output against the Expected Output
Specification's validation figures (all core KPIs match to within
rounding). The Financial Health Score is a transparent 0–100 composite
across 5 weighted dimensions (Profitability 35 / Liquidity &
Collections 20 / Cost & Operating Efficiency 20 / Growth & Stability
15 / Working Capital & Data Reliability 10), with every sub-score and
its supporting evidence visible on the Financial Health page.

## 7. Explainability & Recommendation Methodology

Seven rule-based drivers (Margin Pressure, Operating-Cost Burden,
Revenue Deterioration, Persistent Losses, Weak Collection, Discount
Pressure, Inventory Data Integrity) are checked against fixed
thresholds. Every triggered driver produces a Finding → Evidence →
Driver → Impact → Recommendation card and, where applicable, a
prioritized management recommendation. Nothing is generated without a
supporting calculated number — there is no generic advice and no LLM
in the loop (see "No Fake AI" note below).

## 8. Installation

```bash
cd business-intelligence-app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 9. Running

```bash
streamlit run app.py
```

Then either upload your own CSV (matching the required schema — see
`config/settings.py::REQUIRED_COLUMNS`) or check "Use bundled sample
dataset" in the sidebar to explore the supplied Kenyan SME dataset.
Navigate the analysis using the pages listed in the left sidebar.

## 10. Testing

```bash
pytest tests/ -v
```

Tests cover date parsing, duplicate/quality-flag detection, KPI
calculations (validated against the Expected Output Specification's
reference figures), the scoring engine, RAG classification with
critical overrides, and the explainability/recommendation engine.

## 11. Known Limitations

- Collection coverage is a **portfolio-level estimate** (no invoice
  aging in the source data) — not a true DSO calculation.
- Inventory turnover is withheld whenever reconstructed stock goes
  negative for any product (as on the original bundled sample); this
  is a deliberate data-integrity safeguard, not a bug. The second
  bundled test dataset (Section 12) has intact inventory, so it
  exercises the turnover calculation instead.
- The Financial Health Score's sub-component interpolation curves are
  documented assumptions (isolated in `config/settings.py`) where the
  Expected Output Specification does not fix an exact formula; see
  `docs/technical_notes.md` Section 5 for the validation discussion.
- No LLM/generative AI is used anywhere in the analytical pipeline —
  every explanation and recommendation is generated from rule-based
  logic against calculated evidence.

## 12. Test Datasets

Two CSVs matching the required schema are available for testing:

1. **Bundled sample** (`data/sample/kenyan_sme_bi_financial_operational_data_1800_records.csv`)
   — the original dataset supplied with the project brief. Deliberately
   messy: RED data reliability, RED financial health (critical
   overrides triggered), inventory integrity fails for several
   products. Good for exercising the "unhealthy business / unreliable
   data" path end-to-end.
2. **Synthetic second dataset** (`thika_road_hardware_agrovet_synthetic_dataset.csv`,
   provided alongside this app) — an independently generated
   18-month dataset for a fictional hardware & agrovet business.
   Moderately healthy (GREEN data reliability, GREEN financial health),
   with inventory integrity intact (so Inventory Turnover is actually
   computed), but still carries realistic, deliberate imperfections
   (duplicate transaction IDs, missing categorical fields, mixed date
   formats including a few ambiguous ones, a handful of invalid sale
   quantities and financial-inconsistency rows) so the Data Quality
   page has genuine findings to display. Useful for exercising the
   "healthy business" path and the inventory-turnover calculation,
   which the bundled sample cannot exercise.

Both datasets can be uploaded via the sidebar file uploader on the main
page.

## 13. Definition of Terms

Plain-language definitions of the terms used throughout the app, for
readers who are not accountants or data scientists.

**Gross Sales** — Total sale value before any discount is subtracted.

**Net Sales** — Sale value after discount (`Gross Sales − Discount`).
This is what the customer actually owes/pays for that sale.

**Refund** — Value of goods returned by a customer after a sale.

**Adjusted (Net) Revenue** — The business's real revenue for the
period, after removing refunds: `Net Sales − Refunds`. This is the
"Revenue" figure used everywhere else in the app.

**COGS (Cost of Goods Sold)** — What it cost the business to buy or
produce the goods that were sold (not the selling price — the cost).

**Gross Profit** — What is left of revenue after paying for the goods
themselves: `Adjusted Revenue − COGS`. This is profit before rent,
salaries, and other running costs.

**Gross Margin** — Gross Profit expressed as a percentage of revenue:
`Gross Profit ÷ Adjusted Revenue × 100`. Shows how much of every
shilling of sales is kept after covering the cost of the goods sold.

**Operating Expenses (Opex)** — Day-to-day running costs of the
business that are *not* the cost of goods — e.g. rent, staff salaries,
utilities, repairs, transport.

**Operating Profit** — What is left after both the cost of goods *and*
running costs are covered: `Gross Profit − Operating Expenses`. This is
the business's "real" bottom-line profit from normal operations. A
negative value is an **operating loss**.

**Operating Margin** — Operating Profit as a percentage of revenue:
`Operating Profit ÷ Adjusted Revenue × 100`.

**Operating Expense Ratio** — Operating Expenses as a percentage of
revenue: `Operating Expenses ÷ Adjusted Revenue × 100`. The higher this
is, the more of every sale is consumed by running costs before any
profit is left.

**Discount Rate** — The share of gross sales value given away as
discounts: `Total Discount ÷ Gross Sales × 100`.

**Refund Rate** — Refunds as a percentage of gross sales: how much of
what was sold ended up being returned.

**Average Transaction Value** — Average revenue per valid sale
transaction: `Adjusted Revenue ÷ Number of Valid Sale Transactions`.

**Credit-like Sale** — A sale where the customer paid less than the
full net sale amount at the time of the transaction (i.e. they still
owe the business money). The dataset does not record payment method
directly for sales, so this is *inferred* from the amounts, not
confirmed from a payment field.

**Collection Coverage** — An estimate of how much of the value of
credit-like sales has actually been collected in cash, as a percentage.
A lower number means more money owed to the business is still
outstanding. Because the data has no formal invoice/aging records, this
is a **portfolio-level estimate**, not a precise Days Sales Outstanding
(DSO) calculation.

**Estimated Uncollected Credit Exposure** — The estimated shilling
amount of credit-like sales that has not yet been collected.

**Break-even Revenue** — The approximate monthly revenue the business
would need, at its *current* gross margin and cost structure, to reach
KES 0 operating profit (no profit, no loss): `Average Monthly Operating
Expenses ÷ Gross Margin`. This is an analytical estimate, not a
forecast or guarantee.

**Reconstructed Inventory / Stock-on-Hand** — Because the dataset has
no single "current stock count" field, the app rebuilds an estimated
running stock balance for each product over time by adding up all
recorded stock movements (purchases in, sales out, returns in, stock
adjustments) in date order. If this running total ever goes negative
for a product, it means the recorded movements are inconsistent with
reality (e.g. a sale was recorded for stock that, according to the
records, was never received) — a sign the underlying data needs to be
corrected before it can be trusted for inventory decisions.

**Inventory Integrity** — Whether the reconstructed inventory for all
products stays at zero or above throughout the period. If it does not
(as in the supplied sample dataset), inventory turnover and other
stock-based KPIs are intentionally withheld rather than calculated from
data known to be inconsistent.

**Inventory Turnover** — (Only calculated when inventory integrity is
intact) `COGS ÷ Average Inventory`. Measures how many times stock is
sold and replaced over the period; a standard retail/stock-management
ratio.

**Data Quality Score / Data Reliability** — A 0–100 score (and
GREEN/AMBER/RED status) describing how trustworthy the *input data*
is — based on duplicates, missing values, invalid dates, invalid
quantities, inconsistent labels, and financial inconsistencies. This is
deliberately kept separate from the Financial Health Score: messy data
does not necessarily mean an unhealthy business, and vice versa.

**Financial Health Score** — A 0–100 composite score summarizing the
business's overall financial condition across five weighted areas:
Profitability, Liquidity & Collections, Cost & Operating Efficiency,
Growth & Stability, and Working Capital/Data Reliability. Every
component and sub-component can be expanded to see exactly how it was
calculated.

**RAG Status (Red / Amber / Green)** — A simple traffic-light summary
of financial health: **Green** = healthy/acceptable, **Amber** =
requires attention, **Red** = significant concern. A Red status can
also be triggered directly by a **critical-risk override** (e.g.
persistent losses, a severe revenue drop) even if the numeric score
alone would suggest Amber — the app always explains why when this
happens.

**Driver** — A specific, rule-based, evidence-backed reason
contributing to the current financial result (e.g. "Margin Pressure",
"Weak Collection"). Drivers only appear when their underlying
calculated evidence crosses a defined threshold — never generically.

## 14. Academic / Project Scope

This is a prototype academic Data Science / BI decision-support system.
It does not constitute accounting, tax, or financial advisory services,
does not guarantee future business performance, and is not a
replacement for professional financial review.
