"""Collection coverage / credit exposure analytics.

The dataset has no invoice-aging structure, so this module explicitly
avoids computing a true DSO. It computes a portfolio-level "collection
coverage" estimate as specified in Expected Output Spec Sec. 14/21.
"""

from __future__ import annotations

import pandas as pd


def collection_analysis(df: pd.DataFrame) -> dict:
    sale = df[df["transaction_type"] == "SALE"]
    is_credit_like = sale["is_credit_like_sale"]
    credit_sales = sale[is_credit_like]

    credit_sales_value = float(credit_sales["net_sales_kes"].sum())
    received_at_sale = float(credit_sales["amount_received_kes"].sum())

    customer_payments = df[df["transaction_type"] == "CUSTOMER_PAYMENT"]
    total_collections = float(customer_payments["cash_in_kes"].sum())

    total_collected = received_at_sale + total_collections
    coverage_pct = (total_collected / credit_sales_value * 100) if credit_sales_value else 100.0
    estimated_uncollected = max(credit_sales_value - total_collected, 0.0)

    revenue = float(sale["net_sales_kes"].sum())
    opex = float(df[df["transaction_type"] == "EXPENSE"]["expense_amount_kes"].sum())
    revenue_to_opex_ratio = (revenue / opex) if opex else float("inf")

    return {
        "credit_sales_value": credit_sales_value,
        "received_at_sale": received_at_sale,
        "total_customer_payments": total_collections,
        "collection_coverage_pct": coverage_pct,
        "estimated_uncollected_exposure": estimated_uncollected,
        "revenue_to_opex_ratio": revenue_to_opex_ratio,
        "note": (
            "Collection coverage is a portfolio-level estimate: the dataset "
            "does not contain invoice-level aging or matching between sales "
            "and payments, so figures are not a substitute for a true "
            "Days Sales Outstanding (DSO) calculation."
        ),
    }
