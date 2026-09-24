"""Segment-level analytics: product/category, branch, customer type,
sales channel breakdowns.
"""

from __future__ import annotations

import pandas as pd


def _segment_performance(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    sale = df[df["transaction_type"] == "SALE"].copy()
    refund = df[df["transaction_type"] == "REFUND"].copy()

    sale_grp = sale.groupby(group_col).agg(
        revenue=("net_sales_kes", "sum"),
        gross_sales=("gross_sales_kes", "sum"),
        units_sold=("quantity", "sum"),
        cogs=("cogs_kes", "sum"),
        transactions=("transaction_id", "nunique"),
    )
    refund_grp = refund.groupby(group_col)["net_sales_kes"].sum()
    disc_grp = (sale.groupby(group_col).apply(
        lambda g: (g["gross_sales_kes"] - g["net_sales_kes"]).sum(), include_groups=False
    ))

    result = sale_grp.copy()
    result["refunds"] = refund_grp.reindex(result.index, fill_value=0.0)
    result["adjusted_revenue"] = result["revenue"] - result["refunds"]
    result["gross_profit"] = result["adjusted_revenue"] - result["cogs"]
    result["gross_margin_pct"] = result.apply(
        lambda r: (r["gross_profit"] / r["adjusted_revenue"] * 100) if r["adjusted_revenue"] else 0.0, axis=1
    )
    total_revenue = result["adjusted_revenue"].sum()
    result["revenue_share_pct"] = (
        result["adjusted_revenue"] / total_revenue * 100 if total_revenue else 0.0
    )
    result["discount_value"] = disc_grp.reindex(result.index, fill_value=0.0)
    result["discount_rate_pct"] = result.apply(
        lambda r: (r["discount_value"] / r["gross_sales"] * 100) if r["gross_sales"] else 0.0, axis=1
    )
    result["refund_rate_pct"] = result.apply(
        lambda r: (r["refunds"] / r["gross_sales"] * 100) if r["gross_sales"] else 0.0, axis=1
    )
    result["avg_transaction_value"] = result.apply(
        lambda r: (r["adjusted_revenue"] / r["transactions"]) if r["transactions"] else 0.0, axis=1
    )
    return result.reset_index().sort_values("adjusted_revenue", ascending=False)


def product_category_performance(df: pd.DataFrame) -> pd.DataFrame:
    perf = _segment_performance(df, "product_category_norm").rename(
        columns={"product_category_norm": "product_category"}
    )

    median_rev_share = perf["revenue_share_pct"].median()
    median_margin = perf["gross_margin_pct"].median()

    def _quadrant(row):
        rev_high = row["revenue_share_pct"] >= median_rev_share
        margin_high = row["gross_margin_pct"] >= median_margin
        if rev_high and margin_high:
            return "High revenue / High margin"
        if rev_high and not margin_high:
            return "High revenue / Low margin"
        if not rev_high and margin_high:
            return "Low revenue / High margin"
        return "Low revenue / Low margin"

    perf["quadrant"] = perf.apply(_quadrant, axis=1)
    return perf


def product_performance(df: pd.DataFrame) -> pd.DataFrame:
    return _segment_performance(df, "product_name")


def branch_performance(df: pd.DataFrame) -> pd.DataFrame:
    return _segment_performance(df, "branch_norm").rename(columns={"branch_norm": "branch"})


def channel_performance(df: pd.DataFrame) -> pd.DataFrame:
    return _segment_performance(df, "sales_channel_norm").rename(columns={"sales_channel_norm": "sales_channel"})


def customer_type_performance(df: pd.DataFrame) -> pd.DataFrame:
    return _segment_performance(df, "customer_type_norm").rename(columns={"customer_type_norm": "customer_type"})
