"""
Data Quality Report generation.

Consumes the flags produced by src/data/cleaning.py and turns them into
a structured, explainable Data Quality Report: per-check counts, a
composite 0-100 Data Quality Score, a GREEN/AMBER/RED status, and the
affected-record tables the UI needs to show (never just a clean number).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from config.settings import DQ_DIMENSION_WEIGHTS, DQ_STATUS_BANDS


@dataclass
class DataQualityReport:
    row_count: int
    column_count: int
    duplicate_count: int
    missing_value_summary: dict
    invalid_date_count: int
    ambiguous_date_count: int
    invalid_quantity_count: int
    inconsistent_category_count: int
    inconsistent_payment_label_count: int
    payment_method_missing_for_sale_count: int
    financial_inconsistency_count: int
    inventory_integrity_ok: bool
    inventory_negative_products: list
    dimension_scores: dict = field(default_factory=dict)
    overall_score: float = 0.0
    status: str = "RED"
    limitations: list = field(default_factory=list)


def _dimension_score(bad_count: int, total: int) -> float:
    """0-100 score for a single dimension: 100 = no issues, scaled down
    by the proportion of affected rows. ASSUMPTION: linear penalty,
    floor at 0.
    """
    if total == 0:
        return 100.0
    bad_ratio = min(bad_count / total, 1.0)
    return max(0.0, 100.0 * (1 - bad_ratio))


def build_data_quality_report(
    analytical_df: pd.DataFrame,
    flags: dict,
    exclusion_summary: dict,
    inventory_summary: pd.DataFrame,
) -> DataQualityReport:
    total = len(analytical_df)

    missing_summary = {
        col: int(analytical_df[col].isna().sum())
        for col in ["branch", "customer_type", "sales_channel", "payment_method",
                    "supplier_name", "customer_id"]
    }

    duplicate_count = int(flags["is_duplicate_txn_id"].sum())
    invalid_date_count = int((~flags["is_valid_date"]).sum())
    ambiguous_date_count = int(flags["is_ambiguous_date"].sum())
    invalid_qty_count = int(flags["is_invalid_sale_quantity"].sum())
    inconsistent_cat_count = int(flags["has_inconsistent_category_text"].sum())
    payment_variant_count = int(flags["payment_label_variant"].sum())
    payment_missing_sale_count = int(flags["payment_method_missing_for_sale"].sum())
    financial_inconsistency_count = int(flags["has_financial_inconsistency"].sum())

    negative_products = inventory_summary.loc[
        inventory_summary["has_negative_stock"], "product_name"
    ].tolist()
    inventory_ok = len(negative_products) == 0

    dim_scores = {
        "duplicates": _dimension_score(duplicate_count, total),
        "missing_values": _dimension_score(sum(missing_summary.values()), total * len(missing_summary)),
        "invalid_dates": _dimension_score(invalid_date_count, total),
        "invalid_quantities": _dimension_score(invalid_qty_count, total),
        "inconsistent_categories": _dimension_score(inconsistent_cat_count, total),
        "inconsistent_payment_labels": _dimension_score(payment_variant_count, total),
        "financial_consistency": _dimension_score(financial_inconsistency_count, total),
    }

    overall_score = sum(
        dim_scores[dim] * (DQ_DIMENSION_WEIGHTS[dim] / 100.0) for dim in dim_scores
    )
    # Inventory integrity failure is treated as a hard cap rather than a
    # weighted-average dimension, because it blocks an entire analytical
    # capability (Spec Sec. 4: "Inventory integrity: RED").
    if not inventory_ok:
        overall_score = min(overall_score, DQ_STATUS_BANDS["AMBER"] - 1)

    if overall_score >= DQ_STATUS_BANDS["GREEN"]:
        status = "GREEN"
    elif overall_score >= DQ_STATUS_BANDS["AMBER"]:
        status = "AMBER"
    else:
        status = "RED"

    limitations = []
    if payment_missing_sale_count > 0:
        limitations.append(
            "payment_method is not recorded for sale transactions; credit-like "
            "sales are instead inferred from amount_received_kes < net_sales_kes. "
            "This is an estimate, not a confirmed payment classification."
        )
    if not inventory_ok:
        limitations.append(
            "Reconstructed inventory balances are negative for one or more "
            "products; inventory turnover and stock-based KPIs are withheld "
            "until stock records are reconciled."
        )
    if duplicate_count > 0:
        limitations.append(
            f"{duplicate_count} duplicate transaction_id records were detected "
            "and excluded from KPI calculations (first occurrence kept)."
        )
    if invalid_date_count > 0:
        limitations.append(
            f"{invalid_date_count} records have unparseable transaction dates "
            "and are excluded from all time-based analysis."
        )
    if ambiguous_date_count > 0:
        limitations.append(
            f"{ambiguous_date_count} records had a date format where day/month "
            "order was ambiguous; day-first (DD/MM/YYYY) was assumed."
        )

    return DataQualityReport(
        row_count=total,
        column_count=analytical_df.shape[1],
        duplicate_count=duplicate_count,
        missing_value_summary=missing_summary,
        invalid_date_count=invalid_date_count,
        ambiguous_date_count=ambiguous_date_count,
        invalid_quantity_count=invalid_qty_count,
        inconsistent_category_count=inconsistent_cat_count,
        inconsistent_payment_label_count=payment_variant_count,
        payment_method_missing_for_sale_count=payment_missing_sale_count,
        financial_inconsistency_count=financial_inconsistency_count,
        inventory_integrity_ok=inventory_ok,
        inventory_negative_products=negative_products,
        dimension_scores=dim_scores,
        overall_score=round(overall_score, 1),
        status=status,
        limitations=limitations,
    )
