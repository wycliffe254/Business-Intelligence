"""
Data cleaning / preparation layer.

Principle (per project brief): "Keep two datasets/concepts: RAW DATA and
VALIDATED / ANALYTICAL DATA. Do not destroy the raw upload. Track
transformations. Where a record is excluded from a KPI, explain why."

This module NEVER deletes rows from the raw DataFrame. It returns an
"analytical" DataFrame that is the raw data plus derived/flag columns,
and a boolean `include_in_kpis` column that downstream analytics use to
filter. Every exclusion reason is recorded in `exclusion_reasons`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import NUMERIC_COLUMNS, VALID_TRANSACTION_TYPES
from src.utils.dates import parse_date_series

FINANCIAL_TOLERANCE_KES = 1.0  # ASSUMPTION: rounding tolerance for consistency checks


def _to_numeric(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Coerce a string series to numeric; return (numeric, was_invalid)."""
    numeric = pd.to_numeric(series, errors="coerce")
    was_present = series.notna() & (series.astype(str).str.strip() != "")
    was_invalid = was_present & numeric.isna()
    return numeric, was_invalid


def clean_dataset(raw_df: pd.DataFrame) -> dict:
    """Build the analytical dataset from the raw upload.

    Returns a dict with:
      - analytical_df: pd.DataFrame (raw + derived/flag columns)
      - flags: dict of column-name -> boolean Series (for the Data
        Quality Report)
      - exclusion_summary: dict reason -> count
    """
    df = raw_df.copy()
    df["_row_id"] = np.arange(len(df))

    # ---- 1. Date parsing -------------------------------------------------
    date_info = parse_date_series(df["transaction_date"])
    df["parsed_date"] = date_info["parsed_date"]
    df["is_valid_date"] = date_info["is_valid_date"]
    df["is_ambiguous_date"] = date_info["is_ambiguous_date"]

    # ---- 2. Numeric coercion ----------------------------------------------
    invalid_numeric_any = pd.Series(False, index=df.index)
    for col in NUMERIC_COLUMNS:
        numeric, invalid = _to_numeric(df[col])
        df[col] = numeric
        invalid_numeric_any = invalid_numeric_any | invalid
    df["has_invalid_numeric_field"] = invalid_numeric_any

    # inventory_qty_change is numeric-like but many rows are legitimately
    # blank (non stock-affecting transaction types) -> coerce separately,
    # blanks become 0 change (not an error).
    inv_qty_numeric, inv_qty_invalid = _to_numeric(df["inventory_qty_change"])
    df["inventory_qty_change_numeric"] = inv_qty_numeric.fillna(0.0)
    df["has_invalid_inventory_qty"] = inv_qty_invalid

    # ---- 3. Duplicate transaction IDs -------------------------------------
    df["is_duplicate_txn_id"] = df.duplicated(subset=["transaction_id"], keep="first")

    # ---- 4. Transaction type validity --------------------------------------
    df["is_valid_transaction_type"] = df["transaction_type"].isin(VALID_TRANSACTION_TYPES)

    # ---- 5. Category normalization (case/whitespace only; does not
    #         silently merge genuinely different categories) ---------------
    def _norm(series: pd.Series) -> pd.Series:
        return series.astype(str).str.strip()

    for col in ["branch", "customer_type", "sales_channel", "product_category",
                "expense_category", "payment_method"]:
        raw_col = df[col]
        norm_col = raw_col.where(raw_col.isna(), _norm(raw_col))
        df[f"{col}_norm"] = norm_col

    # flag rows where trimming actually changed the text (i.e. had stray
    # whitespace / case-only variants) as "inconsistent category" evidence
    def _changed(col: str) -> pd.Series:
        raw_col = df[col].astype(str)
        norm_col = df[f"{col}_norm"].astype(str)
        return (raw_col != norm_col) & df[col].notna()

    df["has_inconsistent_category_text"] = (
        _changed("branch") | _changed("customer_type") | _changed("sales_channel")
        | _changed("product_category")
    )

    # ---- 6. Payment-method inference for SALE rows -------------------------
    # Spec Sec. 3 / 14: payment_method is blank for sale records, so infer
    # credit-like sales instead of trusting payment_method.
    is_sale = df["transaction_type"] == "SALE"
    df["is_credit_like_sale"] = is_sale & (
        df["amount_received_kes"].fillna(0) < df["net_sales_kes"].fillna(0)
    )
    df["payment_method_missing_for_sale"] = is_sale & (
        df["payment_method"].isna() | (df["payment_method"].astype(str).str.strip() == "")
    )

    # inconsistent payment labels among the NON-sale rows that do have a
    # payment_method value (e.g. case variants like "M-PESA" vs "Mpesa")
    payment_label_map = {"mpesa": "M-PESA", "m-pesa": "M-PESA"}
    pm_lower = df["payment_method_norm"].astype(str).str.lower()
    df["payment_label_variant"] = pm_lower.isin(payment_label_map.keys()) & (
        df["payment_method_norm"].astype(str) != "M-PESA"
    )

    # ---- 7. Invalid sales quantities ---------------------------------------
    df["is_invalid_sale_quantity"] = is_sale & (
        (df["quantity"].fillna(0) <= 0) & (df["net_sales_kes"].fillna(0) > 0)
    )

    # ---- 8. Financial-relationship consistency -----------------------------
    # NOTE: discount_pct is stored as a fraction in this dataset (e.g. 0.02
    # means 2%), not as a 0-100 percentage value — confirmed against the
    # raw data (gross_sales_kes * (1 - discount_pct) reproduces
    # net_sales_kes for valid rows). An earlier version of this check
    # incorrectly divided by 100 a second time, which flagged the large
    # majority of legitimately-discounted sales as inconsistent.
    expected_net = df["gross_sales_kes"].fillna(0) * (1 - df["discount_pct"].fillna(0))
    net_mismatch = is_sale & (
        (expected_net - df["net_sales_kes"].fillna(0)).abs() > FINANCIAL_TOLERANCE_KES
    )
    expected_gp = df["net_sales_kes"].fillna(0) - df["cogs_kes"].fillna(0)
    gp_mismatch = is_sale & (
        (expected_gp - df["gross_profit_kes"].fillna(0)).abs() > FINANCIAL_TOLERANCE_KES
    )
    df["has_financial_inconsistency"] = net_mismatch | gp_mismatch

    # ---- 9. Missing critical fields ----------------------------------------
    # ASSUMPTION: "critical" fields are those without which a row cannot be
    # placed in time or attributed to a transaction type.
    df["missing_critical_field"] = (
        ~df["is_valid_date"] | df["transaction_id"].isna()
        | df["transaction_type"].isna()
    )

    # ---- 10. Inclusion in KPI calculations ---------------------------------
    df["exclude_reason"] = ""
    df.loc[df["is_duplicate_txn_id"], "exclude_reason"] += "duplicate_transaction_id;"
    df.loc[~df["is_valid_date"], "exclude_reason"] += "invalid_date;"
    df.loc[df["missing_critical_field"], "exclude_reason"] += "missing_critical_field;"
    df.loc[df["is_invalid_sale_quantity"], "exclude_reason"] += "invalid_sale_quantity;"

    df["include_in_kpis"] = df["exclude_reason"] == ""

    exclusion_summary = {
        "duplicate_transaction_id": int(df["is_duplicate_txn_id"].sum()),
        "invalid_date": int((~df["is_valid_date"]).sum()),
        "missing_critical_field": int(df["missing_critical_field"].sum()),
        "invalid_sale_quantity": int(df["is_invalid_sale_quantity"].sum()),
        "total_excluded_rows": int((~df["include_in_kpis"]).sum()),
        "total_rows": int(len(df)),
    }

    flags = {
        "is_duplicate_txn_id": df["is_duplicate_txn_id"],
        "is_valid_date": df["is_valid_date"],
        "is_ambiguous_date": df["is_ambiguous_date"],
        "has_invalid_numeric_field": df["has_invalid_numeric_field"],
        "has_invalid_inventory_qty": df["has_invalid_inventory_qty"],
        "is_invalid_sale_quantity": df["is_invalid_sale_quantity"],
        "has_inconsistent_category_text": df["has_inconsistent_category_text"],
        "payment_label_variant": df["payment_label_variant"],
        "payment_method_missing_for_sale": df["payment_method_missing_for_sale"],
        "has_financial_inconsistency": df["has_financial_inconsistency"],
        "missing_critical_field": df["missing_critical_field"],
    }

    return {
        "analytical_df": df,
        "flags": flags,
        "exclusion_summary": exclusion_summary,
    }


def reconstruct_inventory(analytical_df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct a running stock-on-hand position per product from
    inventory_qty_change, ordered by date. Rows without a valid date or
    product_name are excluded from the reconstruction (and reported).

    Returns a per-product summary with columns:
      product_name, ending_stock, min_running_stock, has_negative_stock
    """
    df = analytical_df[
        analytical_df["is_valid_date"] & analytical_df["product_name"].notna()
        & (analytical_df["product_name"].astype(str).str.strip() != "")
        & (~analytical_df["is_duplicate_txn_id"])
    ].copy()

    df = df.sort_values(["product_name", "parsed_date", "_row_id"])
    df["running_stock"] = df.groupby("product_name")["inventory_qty_change_numeric"].cumsum()
    df["running_value"] = df.groupby("product_name")["inventory_value_change_kes"].cumsum()

    summary = (
        df.groupby("product_name")
        .agg(
            ending_stock=("running_stock", "last"),
            min_running_stock=("running_stock", "min"),
            opening_value=("running_value", "first"),
            ending_value=("running_value", "last"),
        )
        .reset_index()
    )
    summary["has_negative_stock"] = summary["min_running_stock"] < 0
    return summary
