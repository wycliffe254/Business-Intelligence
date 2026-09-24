"""
Central configuration for the Explainable BI & Financial Health Decision
Support System.

DESIGN PRINCIPLE
-----------------
Every threshold, weight, formula constant, and business rule that the
project documentation / Expected Output Specification defines explicitly is
reproduced here verbatim (with a citation to the source section in the
comment). Every value that was NOT explicitly specified and had to be
reasonably assumed is marked with "ASSUMPTION:" so a future developer can
find and change it without hunting through the codebase.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 1. REQUIRED SCHEMA
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "transaction_id", "transaction_date", "transaction_type", "document_no",
    "business_name", "branch", "sales_channel", "customer_type",
    "customer_id", "supplier_name", "product_category", "product_name",
    "quantity", "unit_price_kes", "discount_pct", "gross_sales_kes",
    "net_sales_kes", "unit_cost_kes", "cogs_kes", "gross_profit_kes",
    "expense_category", "expense_amount_kes", "cash_in_kes", "cash_out_kes",
    "amount_received_kes", "accounts_receivable_change_kes",
    "accounts_payable_change_kes", "inventory_qty_change",
    "inventory_value_change_kes", "payment_method", "salesperson_or_staff",
    "manual_entry_flag",
]

NUMERIC_COLUMNS = [
    "quantity", "unit_price_kes", "discount_pct", "gross_sales_kes",
    "net_sales_kes", "unit_cost_kes", "cogs_kes", "gross_profit_kes",
    "expense_amount_kes", "cash_in_kes", "cash_out_kes",
    "amount_received_kes", "accounts_receivable_change_kes",
    "accounts_payable_change_kes", "inventory_value_change_kes",
    "manual_entry_flag",
]

# inventory_qty_change is read as numeric-like but stored as str in the raw
# file (mixed blanks) -> handled specially in cleaning.
INVENTORY_QTY_COLUMN = "inventory_qty_change"

VALID_TRANSACTION_TYPES = [
    "SALE", "PURCHASE", "EXPENSE", "CUSTOMER_PAYMENT", "SUPPLIER_PAYMENT",
    "REFUND", "STOCK_ADJUSTMENT",
]

# ASSUMPTION: canonical branch / customer_type / sales_channel spellings.
# The dataset's actual values are already reasonably consistent; this map
# exists to absorb case/whitespace variants defensively for future uploads.
CATEGORY_CANONICAL_MAP = {
    "branch": {},
    "customer_type": {},
    "sales_channel": {},
}

# ---------------------------------------------------------------------------
# 2. DATA QUALITY THRESHOLDS  (Expected Output Spec, Sec. 3 / 3.1)
# "These are project-defined control thresholds, not regulatory or
# industry standards." -> values below are ASSUMPTION-based, isolated here.
# ---------------------------------------------------------------------------

DQ_STATUS_BANDS = {
    # overall data-quality score out of 100
    "GREEN": 85,
    "AMBER": 65,
    # below AMBER threshold -> RED
}

# ASSUMPTION: relative weight of each dimension in the composite Data
# Quality score (must sum to 100).
DQ_DIMENSION_WEIGHTS = {
    "duplicates": 15,
    "missing_values": 20,
    "invalid_dates": 15,
    "invalid_quantities": 15,
    "inconsistent_categories": 10,
    "inconsistent_payment_labels": 10,
    "financial_consistency": 15,
}

# ---------------------------------------------------------------------------
# 3. RAG BANDS FOR THE OVERALL FINANCIAL HEALTH SCORE (Spec Sec. 25)
# ---------------------------------------------------------------------------

RAG_GREEN_MIN = 70
RAG_AMBER_MIN = 50
# below RAG_AMBER_MIN -> RED

# ---------------------------------------------------------------------------
# 4. FINANCIAL HEALTH SCORE WEIGHTS (Spec Sec. 19-24)
# ---------------------------------------------------------------------------

MAX_SCORE = 100

WEIGHTS = {
    "profitability": 35,
    "liquidity_collections": 20,
    "cost_efficiency": 20,
    "growth_stability": 15,
    "data_working_capital": 10,
}

# --- Profitability (35) — Spec Sec. 20 ---
PROFITABILITY_SUBWEIGHTS = {
    "gross_margin": 15,
    "operating_margin": 15,
    "gross_profit_trend": 5,
}

# ASSUMPTION: interpolation curve for Gross Margin score (0-15).
# The spec gives a qualitative note (~21.3% => AMBER) but no explicit
# breakpoint table for this sub-score, unlike Liquidity. We use a
# linear ramp between documented reference points, consistent with the
# RAG interpretation: <10% weak, 10-20% amber-ish, >=30% strong.
GROSS_MARGIN_SCORE_POINTS = [  # (margin_pct, points out of 15)
    (0, 0), (10, 5), (20, 9), (30, 13), (40, 15),
]

# ASSUMPTION: interpolation curve for Operating Margin score (0-15).
# Recalibrated against the validation dataset (Expected Output Spec
# Sec. 27, "score in approximately the low-60s before overrides"):
# the original narrower curve (-30..-10 -> 0..3) scored a -20.6% margin
# almost at zero, which understated the sub-score relative to the
# spec's own validation figure. -40% is now treated as the practical
# floor, giving a -20% margin roughly a fifth of the available points
# rather than near-zero, while still keeping >=15% as full marks.
OPERATING_MARGIN_SCORE_POINTS = [  # (margin_pct, points out of 15)
    (-40, 0), (-15, 4), (0, 9), (10, 13), (15, 15),
]

# ASSUMPTION: Gross Profit Trend score (0-5) based on comparable-period
# % change in gross profit. Flat/growing = full marks, severe decline = 0.
GROSS_PROFIT_TREND_SCORE_POINTS = [  # (pct_change, points out of 5)
    (-30, 0), (-10, 2), (0, 4), (5, 5),
]

# --- Liquidity & Collections (20) — Spec Sec. 21 (explicit table) ---
COLLECTION_COVERAGE_SCORE_TABLE = [
    # (min_pct_inclusive, points out of 10)
    (95, 10), (90, 9), (80, 7.5), (70, 6), (60, 4), (0, 2),
]
# NOTE: spec gives points on a 0-100 sub-scale (100/90/75/60/40/20); we
# rescale to the 10-point weight allocated to this component
# (Collection Coverage = 10 of the 20 Liquidity points).

# ASSUMPTION: Revenue-to-Opex coverage score (0-5). Ratio = Revenue/Opex.
# 1.0x means opex exactly consumes revenue (weak); >=2x is strong.
REVENUE_TO_OPEX_SCORE_POINTS = [  # (ratio, points out of 5)
    (0.5, 0), (1.0, 2), (1.5, 4), (2.0, 5),
]

# ASSUMPTION: Uncollected credit exposure score (0-5), measured as
# uncollected credit / average monthly sales. Lower is better.
UNCOLLECTED_EXPOSURE_SCORE_POINTS = [  # (exposure_ratio, points out of 5)
    (0.0, 5), (0.5, 4), (1.0, 2), (2.0, 0),
]

# --- Cost & Operational Efficiency (20) — Spec Sec. 22 ---
# ASSUMPTION: Operating expense ratio score (0-10). <=25% full marks,
# >=60% zero, consistent with the RAG threshold of 35% ("excessive").
OPEX_RATIO_SCORE_POINTS = [  # (opex_ratio_pct, points out of 10)
    (25, 10), (35, 7), (45, 4), (60, 0),
]

# ASSUMPTION: Discount discipline score (0-5). Weighted discount rate;
# spec's Driver F trigger is >4%.
DISCOUNT_SCORE_POINTS = [  # (discount_rate_pct, points out of 5)
    (0, 5), (4, 3), (8, 1), (12, 0),
]

# ASSUMPTION: Refund rate score (0-5).
REFUND_SCORE_POINTS = [  # (refund_rate_pct, points out of 5)
    (0, 5), (2, 4), (5, 2), (10, 0),
]

# --- Growth & Stability (15) — Spec Sec. 23 (explicit structure) ---
# ASSUMPTION: Recent revenue trend score (0-10). 3mo-vs-3mo % change.
REVENUE_TREND_SCORE_POINTS = [  # (pct_change, points out of 10)
    (-30, 0), (-10, 4), (0, 7), (10, 10),
]

# Profitability Stability = % of months with positive operating profit,
# scaled directly onto the 5-point allocation (explicit in spec Sec. 23:
# "4 of 20 months are profitable = 20%" is used illustratively).
# ASSUMPTION: linear scaling of % profitable months onto 0-5 points.
PROFITABLE_MONTHS_SCORE_POINTS = [  # (pct_profitable_months, points out of 5)
    (0, 0), (50, 2.5), (100, 5),
]

# --- Data / Working Capital Reliability (10) — Spec Sec. 24 ---
# ASSUMPTION: this gate blends (a) the Data Quality composite score and
# (b) whether inventory integrity is usable, since the spec explicitly
# says inventory turnover cannot be forced into the score for this
# dataset and should instead reduce the reliability allocation.
DATA_RELIABILITY_SCORE_POINTS = [  # (dq_score_0_100, points out of 10 when inventory OK)
    (30, 0), (50, 3), (70, 6), (85, 8), (100, 10),
]
INVENTORY_INTEGRITY_PENALTY_POINTS = 3  # ASSUMPTION: points deducted (of the 10) if inventory integrity fails

# ---------------------------------------------------------------------------
# 5. CRITICAL-RISK OVERRIDES (Spec Sec. 26, verbatim rules)
# ---------------------------------------------------------------------------

CRITICAL_OVERRIDES = {
    "persistent_operating_loss": {
        "operating_margin_threshold": -10.0,   # %
        "min_consecutive_months": 3,
    },
    "severe_revenue_deterioration": {
        "revenue_decline_threshold": -20.0,    # % (comparable period)
        "requires_margin_deterioration": True,
    },
    "severe_collection_failure": {
        "collection_coverage_threshold": 60.0,  # %
    },
    "severe_margin_deterioration": {
        "gross_margin_decline_pp_threshold": 5.0,  # percentage points
    },
    # Rule 5 (critical data integrity) is evaluated structurally in
    # health/rag.py from the Data Quality Report, not a single numeric
    # threshold here.
}

# ---------------------------------------------------------------------------
# 6. KPI / DRIVER THRESHOLDS (Spec Sec. 29, verbatim rules)
# ---------------------------------------------------------------------------

DRIVER_THRESHOLDS = {
    "margin_pressure": {
        "gross_margin_below_pct": 20.0,
        "gross_margin_decline_pp": 3.0,
    },
    "operating_cost_pressure": {
        "opex_to_revenue_above_pct": 35.0,
    },
    "revenue_deterioration": {
        "recent_decline_above_pct": 5.0,
    },
    "persistent_losses": {
        "min_consecutive_loss_months": 3,
    },
    "weak_collection": {
        "collection_coverage_below_pct": 90.0,
    },
    "discount_pressure": {
        "weighted_discount_rate_above_pct": 4.0,
    },
    "inventory_integrity": {
        # triggers when reconstructed running stock goes negative
        "negative_stock_triggers": True,
    },
}

# Individual KPI RAG thresholds referenced across the app (Spec Sec. 5-15)
KPI_RAG = {
    "gross_margin_pct": {"green": 30.0, "amber": 20.0},           # >=30 G, 20-30 A, <20 R  (Sec 5.4 context)
    "operating_margin_pct": {"green": 0.0, "amber": -10.0},        # >=0 G, -10..0 A, <-10 R (Sec 8)
    "opex_ratio_pct": {"green": 25.0, "amber": 35.0, "inverse": True},  # <=25 G, 25-35 A, >35 R (Sec 11)
    "discount_rate_pct": {"green": 2.0, "amber": 4.0, "inverse": True},  # (Sec 12: 4.4% => AMBER)
    "refund_rate_pct": {"green": 1.0, "amber": 3.0, "inverse": True},    # (Sec 13: 0.26% => GREEN)
    "collection_coverage_pct": {"green": 95.0, "amber": 80.0},           # (Sec 14/21 table)
}

# ---------------------------------------------------------------------------
# 7. GROWTH / PERIOD DEFINITIONS
# ---------------------------------------------------------------------------

# ASSUMPTION: "recent" trend = latest 3 complete calendar months in the
# data vs the preceding 3 complete calendar months (Spec Sec. 9).
RECENT_TREND_MONTHS = 3

# Spec Sec. 9: explicit comparable period used for validation.
COMPARABLE_PERIOD_MONTHS = ("01", "08")  # Jan-Aug

# ---------------------------------------------------------------------------
# 8. MISC
# ---------------------------------------------------------------------------

CURRENCY_SYMBOL = "KES"
CURRENCY_DIVISOR_MILLION = 1_000_000

# ASSUMPTION: a sales row is "valid" for quantity-based KPIs (e.g. Average
# Transaction Value denominator) if transaction_type == SALE, quantity > 0,
# and the row is not a detected duplicate transaction_id.
VALID_SALE_MIN_QUANTITY = 1

APP_TITLE = "Explainable BI & Financial Health Decision Support System"
APP_SUBTITLE = "Kenyan SME Financial & Operational Intelligence Prototype"
