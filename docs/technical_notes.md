# Technical Notes

## 1. Architecture

```
RAW CSV (upload)
   -> src/data/loader.py         (schema check, raw DataFrame — never mutated)
   -> src/data/cleaning.py       (type coercion, date parsing, flags; builds
                                   the "analytical" DataFrame = raw + flags)
   -> src/data/validation.py     (aggregates flags -> Data Quality Report + score)
   -> src/analytics/kpis.py      (orchestrates profitability/liquidity/growth/
                                   efficiency/inventory -> one KPI dict)
   -> src/health/scoring.py      (0-100 Financial Health Score, 5 weighted
                                   components, fully itemized)
   -> src/health/rag.py          (GREEN/AMBER/RED + 5 critical-risk overrides)
   -> src/explainability/drivers.py        (7 rule-based driver checks, A-G)
   -> src/explainability/explanations.py   (Finding/Evidence/Driver/Impact/
                                              Recommendation cards + executive summary)
   -> src/explainability/recommendations.py (prioritized, evidence-linked actions)
   -> src/reporting/report.py    (HTML executive report)
   -> app.py + pages/*.py        (Streamlit presentation layer only — no
                                   business logic lives in the UI layer)
```

Every stage above is plain Python/pandas and independently testable
(see `tests/`) without starting Streamlit.

## 2. Raw vs. Analytical Data

`src/data/cleaning.py::clean_dataset()` never deletes rows. It returns
the original DataFrame with additional flag/derived columns
(`is_duplicate_txn_id`, `is_valid_date`, `is_invalid_sale_quantity`,
`has_financial_inconsistency`, `include_in_kpis`, `exclude_reason`,
...). All KPI computations filter on `include_in_kpis`; the reason a
row was excluded is always visible in `exclude_reason` and surfaced on
the Data Quality page.

## 3. Date Parsing

The dataset mixes `YYYY-MM-DD`, `DD-MM-YYYY`, and slash-separated dates
where day/month order is not consistent (e.g. `19/12/2025` can only be
`DD/MM`, while `08/19/2026` can only be `MM/DD`). `src/utils/dates.py`
resolves each row independently:
1. If one component is `>12`, it must be the day; the other is the month.
2. If both components are `<=12`, the format is genuinely ambiguous.
   **Assumption**: default to day-first (Kenyan/international
   convention), and flag the row `is_ambiguous_date` for the Data
   Quality Report.

## 4. KPI Formulas (as implemented, `src/analytics/`)

| KPI | Formula | Source module |
|---|---|---|
| Adjusted Net Revenue | `sum(net_sales_kes, SALE) - sum(net_sales_kes, REFUND)` | profitability.py |
| Gross Profit | `Adjusted Revenue - sum(cogs_kes, SALE)` | profitability.py |
| Gross Margin % | `Gross Profit / Adjusted Revenue * 100` | profitability.py |
| Operating Expenses | `sum(expense_amount_kes, EXPENSE)` | profitability.py |
| Operating Profit | `Gross Profit - Operating Expenses` | profitability.py |
| Operating Margin % | `Operating Profit / Adjusted Revenue * 100` | profitability.py |
| Operating Expense Ratio | `Operating Expenses / Adjusted Revenue * 100` | profitability.py |
| Discount Rate % | `sum(gross_sales - net_sales, SALE) / sum(gross_sales, SALE) * 100` | profitability.py |
| Refund Rate % | `sum(net_sales_kes, REFUND) / sum(gross_sales_kes, SALE) * 100` | profitability.py |
| Avg Transaction Value | `Adjusted Revenue / count(valid SALE txns)` | profitability.py |
| Break-even Revenue | `Avg Monthly Operating Expenses / Gross Margin (fraction)` | profitability.py |
| Collection Coverage % | `(amount_received_at_sale for credit-like sales + sum(cash_in_kes, CUSTOMER_PAYMENT)) / credit-like sales value * 100` | liquidity.py |
| Revenue Growth (recent) | latest 3 complete months vs preceding 3 complete months | growth.py |
| Revenue Growth (comparable) | same Jan–Aug window, latest year vs. prior year present in data | growth.py |
| Profitable Months % | `count(months with operating_profit > 0) / total months` | growth.py |

**Credit-like sale** (Spec Sec. 3/14): a SALE row where
`amount_received_kes < net_sales_kes`, because `payment_method` is
blank on all sale records in this dataset and cannot be used directly.

### Validation against the Expected Output Specification

Running the pipeline on the supplied 2,287-row dataset produces:

| Metric | Spec expectation | This implementation |
|---|---|---|
| Adjusted revenue | ≈ KES 7.70M | KES 7,704,313 |
| Gross profit / margin | ≈ KES 1.64M / 21.3% | KES 1,637,512 / 21.25% |
| Operating profit / margin | ≈ -KES 1.59M / -20.6% | -KES 1,590,121 / -20.64% |
| Operating expense ratio | ≈ 41.9% | 41.89% |
| Comparable Jan–Aug revenue decline | ≈ 21.9% | 21.92% |
| Gross margin deterioration | ≈ 4.9pp | 4.94pp |
| Collection coverage | ≈ 88.5% | 88.47% |
| Refund rate | ≈ 0.26% | 0.25% |
| Profitable months | ≈ 20% | 20.0% (4 of 20 months) |
| Avg monthly revenue / gross profit / opex | ≈ 385,216 / 81,876 / 161,382 | 385,216 / 81,876 / 161,382 |
| Break-even revenue | ≈ KES 759,283 (+97%) | KES 759,299 (+97.1%) |

All core KPIs reproduce the spec's validation figures to within rounding.

## 5. Financial Health Score

Five weighted dimensions (Spec Sec. 19-24): Profitability (35),
Liquidity & Collections (20), Cost & Operating Efficiency (20), Growth
& Stability (15), Working Capital / Data Reliability (10).

Only **Collection Coverage** has an explicit points table in the spec;
every other sub-score uses a documented, isolated, piecewise-linear
interpolation curve defined in `config/settings.py` (search for
`ASSUMPTION:`). `src/health/thresholds.py` provides two reusable
primitives: `interpolate_score()` (continuous linear ramp) and
`band_score()` (discrete step table, used for Collection Coverage).

**On the sample dataset this implementation scores 49.2/100** before
overrides. The Expected Output Specification states the dataset
"should produce a score in approximately the low-60s before
critical-risk overrides, **depending on the precise interpolation
method used**" (Spec Sec. 27) — the spec explicitly does not fix these
curves. We investigated the gap: every underlying KPI matches the
spec's validation figures almost exactly (see table above), so the
~12-point difference is attributable entirely to the assumed
interpolation curves for Operating Margin, Cost Efficiency and Data
Reliability sub-scores, which are stricter than whatever curve the
spec's authors used. Because the **final RAG status is forced to RED
by critical-risk overrides regardless of the numeric score** (which is
the behavior the spec actually validates against — Sec. 27), this
discrepancy does not affect the system's classification correctness.
Anyone recalibrating the score for closer numeric alignment should
start with `OPERATING_MARGIN_SCORE_POINTS`, `OPEX_RATIO_SCORE_POINTS`
and `DATA_RELIABILITY_SCORE_POINTS` in `config/settings.py`.

## 6. RAG Classification & Critical Overrides

Base bands: `>=70` GREEN, `50-69` AMBER, `<50` RED (Spec Sec. 25).

Five critical-risk overrides (Spec Sec. 26) force RED regardless of
score, implemented in `src/health/rag.py`:
1. Persistent Operating Loss — operating margin < -10% for >=3 consecutive months.
2. Severe Revenue Deterioration — comparable-period revenue decline <= -20% with margin also deteriorating.
3. Severe Collection Failure — collection coverage < 60%.
4. Severe Margin Deterioration — gross margin decline >= 5pp over the comparable period.
5. Critical Data Integrity Failure — Data Quality status RED and score < 40.

On the sample dataset, overrides 1 and 2 both trigger.

## 7. Data Quality Score

`src/data/validation.py` computes a 0-100 composite from seven weighted
dimensions (duplicates, missing values, invalid dates, invalid
quantities, inconsistent categories, inconsistent payment labels,
financial consistency). Bands: `>=85` GREEN, `>=65` AMBER, else RED.
Inventory integrity failure caps the composite at AMBER-1 regardless of
the weighted average, because it blocks an entire analytical capability
(Spec Sec. 4).

**Design principle**: Data Reliability and Financial Health are always
displayed as two separate concepts. A RED data-reliability status is a
statement about the trustworthiness of the input, not a statement about
whether the business is failing, and vice versa.

## 8. Explainability Engine

`src/explainability/drivers.py` implements exactly the 7 rule-based
drivers specified (Sec. 29): Margin Pressure (A), Excessive
Operating-Cost Burden (B), Revenue Deterioration (C), Persistent Losses
(D), Weak Collection (E), Discount Pressure (F), Inventory Data
Integrity (G). Every driver's `evidence` dict is populated directly
from computed KPIs — nothing is templated without a supporting number.

`src/explainability/explanations.py` turns triggered drivers (plus the
"operating loss" special case) into Finding/Evidence/Driver/Impact/
Recommendation cards, and builds the automated executive summary in
SME-owner-friendly language.

`src/explainability/recommendations.py` maps triggered drivers to
management recommendations with an explicit priority order (Sec. 34):
1. Restore Operating Profitability, 2. Protect and Recover Revenue,
3. Improve Margin, 4. Control Operating Costs / Discount Controls,
5. Improve Credit Collection, 6. Reconcile Inventory Data. A category is
only produced when its underlying driver actually triggered — the
system never emits a recommendation without supporting evidence.

## 9. Inventory Handling

`src/data/cleaning.py::reconstruct_inventory()` builds a running stock
position per product from `inventory_qty_change`, ordered by date,
excluding duplicate/undated rows. If any product's running stock goes
negative, `src/analytics/inventory.py` reports the inventory as
**unusable for financial scoring** and withholds inventory turnover
entirely (Spec Sec. 4/24) rather than producing a number from invalid
data. On the sample dataset several product lines fail this check.

## 10. Known Limitations

- Collection coverage is a portfolio-level estimate; the dataset has no
  invoice-level aging or matching, so it is not a substitute for DSO.
- Inventory turnover cannot be computed on the sample dataset by design.
- The Financial Health sub-score interpolation curves are documented
  assumptions (see Section 5) and can be recalibrated in
  `config/settings.py` without touching any other module.
- Ambiguous two-digit/two-digit dates default to day-first; this is
  logged per-row (`is_ambiguous_date`) but cannot be resolved with
  certainty from the data alone.

## 11. Changelog

- **Financial-consistency check fixed.** `discount_pct` is stored as a
  fraction (e.g. `0.02` = 2%), not a 0–100 percentage. The original
  check divided by 100 a second time, which flagged ~58% of the
  bundled sample's legitimately-discounted sales as inconsistent.
  Fixed in `src/data/cleaning.py`; the flag count drops to 0 on rows
  that are actually consistent, confirmed against both bundled test
  datasets.
- **Inventory Turnover formula fixed.** The original formula divided
  COGS (a KES value) by the mean of raw ending-stock *unit counts*
  across products, producing a nonsensical ratio. `reconstruct_inventory()`
  now also tracks running inventory *value* (via
  `inventory_value_change_kes`), and `inventory_turnover()` uses
  `COGS / Average Inventory Value`, averaged between opening and
  ending total inventory value. This path was previously untested
  because the original bundled sample fails inventory integrity; the
  second bundled test dataset (see README Section 12) exercises it.
