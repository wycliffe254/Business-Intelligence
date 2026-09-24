"""Revenue, COGS, gross profit/margin, operating expenses/profit/margin."""

from __future__ import annotations

import pandas as pd


def compute_core_profitability(df: pd.DataFrame) -> dict:
    """df must already be filtered to include_in_kpis rows."""
    sale = df[df["transaction_type"] == "SALE"]
    refund = df[df["transaction_type"] == "REFUND"]
    expense = df[df["transaction_type"] == "EXPENSE"]

    gross_sales = float(sale["gross_sales_kes"].sum())
    sales_net_revenue = float(sale["net_sales_kes"].sum())
    refunds_value = float(refund["net_sales_kes"].sum())
    adjusted_revenue = sales_net_revenue - refunds_value

    cogs = float(sale["cogs_kes"].sum())
    gross_profit = adjusted_revenue - cogs
    gross_margin_pct = (gross_profit / adjusted_revenue * 100) if adjusted_revenue else 0.0

    operating_expenses = float(expense["expense_amount_kes"].sum())
    operating_profit = gross_profit - operating_expenses
    operating_margin_pct = (operating_profit / adjusted_revenue * 100) if adjusted_revenue else 0.0
    opex_ratio_pct = (operating_expenses / adjusted_revenue * 100) if adjusted_revenue else 0.0

    discount_value = float((sale["gross_sales_kes"] - sale["net_sales_kes"]).sum())
    discount_rate_pct = (discount_value / gross_sales * 100) if gross_sales else 0.0

    refund_rate_pct = (refunds_value / gross_sales * 100) if gross_sales else 0.0

    valid_sales_txns = int((sale["quantity"] > 0).sum())
    avg_transaction_value = (adjusted_revenue / valid_sales_txns) if valid_sales_txns else 0.0

    return {
        "gross_sales": gross_sales,
        "sales_net_revenue": sales_net_revenue,
        "refunds_value": refunds_value,
        "adjusted_revenue": adjusted_revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "operating_expenses": operating_expenses,
        "operating_profit": operating_profit,
        "operating_margin_pct": operating_margin_pct,
        "opex_ratio_pct": opex_ratio_pct,
        "discount_value": discount_value,
        "discount_rate_pct": discount_rate_pct,
        "refund_rate_pct": refund_rate_pct,
        "valid_sales_transactions": valid_sales_txns,
        "average_transaction_value": avg_transaction_value,
    }


def expense_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    expense = df[df["transaction_type"] == "EXPENSE"]
    breakdown = (
        expense.groupby("expense_category_norm")["expense_amount_kes"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"expense_category_norm": "expense_category", "expense_amount_kes": "amount_kes"})
    )
    total = breakdown["amount_kes"].sum()
    breakdown["share_pct"] = (breakdown["amount_kes"] / total * 100) if total else 0.0
    return breakdown


def break_even_analysis(df: pd.DataFrame, core: dict) -> dict:
    """Approximate monthly break-even revenue.

    Break-even Revenue = Average Monthly Operating Expenses / Gross Margin
    (Spec Sec. 31). Explicitly labelled an approximate analytical estimate.
    """
    sale = df[df["transaction_type"] == "SALE"].copy()
    sale["month"] = sale["parsed_date"].dt.to_period("M")
    n_months = df.loc[df["parsed_date"].notna(), "parsed_date"].dt.to_period("M").nunique()
    n_months = max(n_months, 1)

    avg_monthly_revenue = core["adjusted_revenue"] / n_months
    avg_monthly_gross_profit = core["gross_profit"] / n_months
    avg_monthly_opex = core["operating_expenses"] / n_months

    gross_margin_fraction = core["gross_margin_pct"] / 100.0
    if gross_margin_fraction > 0:
        breakeven_revenue = avg_monthly_opex / gross_margin_fraction
    else:
        breakeven_revenue = float("nan")

    revenue_gap_pct = (
        (breakeven_revenue - avg_monthly_revenue) / avg_monthly_revenue * 100
        if avg_monthly_revenue and breakeven_revenue == breakeven_revenue
        else float("nan")
    )

    return {
        "n_months": n_months,
        "avg_monthly_revenue": avg_monthly_revenue,
        "avg_monthly_gross_profit": avg_monthly_gross_profit,
        "avg_monthly_opex": avg_monthly_opex,
        "breakeven_revenue": breakeven_revenue,
        "revenue_gap_pct": revenue_gap_pct,
    }
