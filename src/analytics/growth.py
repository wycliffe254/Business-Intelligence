"""Time-series / growth analytics: monthly series, recent trend, comparable
year-on-year period, profitable-months ratio.
"""

from __future__ import annotations

import pandas as pd

from config.settings import RECENT_TREND_MONTHS


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """Build a monthly financial series: revenue, gross profit, opex,
    operating profit, for every month present in the valid data.
    """
    valid = df[df["parsed_date"].notna()].copy()
    valid["month"] = valid["parsed_date"].dt.to_period("M")

    sale = valid[valid["transaction_type"] == "SALE"]
    refund = valid[valid["transaction_type"] == "REFUND"]
    expense = valid[valid["transaction_type"] == "EXPENSE"]

    rev = sale.groupby("month")["net_sales_kes"].sum()
    ref = refund.groupby("month")["net_sales_kes"].sum()
    cogs = sale.groupby("month")["cogs_kes"].sum()
    opex = expense.groupby("month")["expense_amount_kes"].sum()

    all_months = pd.period_range(
        start=valid["month"].min(), end=valid["month"].max(), freq="M"
    )
    result = pd.DataFrame(index=all_months)
    result["revenue"] = rev.reindex(all_months, fill_value=0.0) - ref.reindex(all_months, fill_value=0.0)
    result["cogs"] = cogs.reindex(all_months, fill_value=0.0)
    result["gross_profit"] = result["revenue"] - result["cogs"]
    result["operating_expenses"] = opex.reindex(all_months, fill_value=0.0)
    result["operating_profit"] = result["gross_profit"] - result["operating_expenses"]
    result["gross_margin_pct"] = result.apply(
        lambda r: (r["gross_profit"] / r["revenue"] * 100) if r["revenue"] else 0.0, axis=1
    )
    result = result.reset_index().rename(columns={"index": "month"})
    result["month_str"] = result["month"].astype(str)
    return result


def recent_trend(monthly: pd.DataFrame, n: int = RECENT_TREND_MONTHS) -> dict:
    if len(monthly) < 2 * n:
        return {
            "sufficient_data": False,
            "message": "Insufficient historical data for this analysis.",
        }
    recent = monthly.tail(n)["revenue"].sum()
    preceding = monthly.tail(2 * n).head(n)["revenue"].sum()
    change_pct = ((recent - preceding) / preceding * 100) if preceding else 0.0
    return {
        "sufficient_data": True,
        "recent_period_revenue": float(recent),
        "preceding_period_revenue": float(preceding),
        "change_pct": float(change_pct),
        "n_months": n,
    }


def comparable_period_yoy(monthly: pd.DataFrame, start_month: str = "01", end_month: str = "08") -> dict:
    """Compare the same Jan-Aug (or configured) window across the two most
    recent years present in the data, avoiding an 8-month vs 12-month
    mismatch.
    """
    monthly = monthly.copy()
    monthly["year"] = monthly["month"].apply(lambda p: p.year)
    monthly["mo"] = monthly["month"].apply(lambda p: p.month)

    years = sorted(monthly["year"].unique())
    if len(years) < 2:
        return {"sufficient_data": False, "message": "Insufficient historical data for this analysis."}

    latest_year = years[-1]
    prior_year = years[-2]
    start_m, end_m = int(start_month), int(end_month)

    latest_window = monthly[(monthly["year"] == latest_year) & (monthly["mo"] >= start_m) & (monthly["mo"] <= end_m)]
    prior_window = monthly[(monthly["year"] == prior_year) & (monthly["mo"] >= start_m) & (monthly["mo"] <= end_m)]

    if latest_window.empty or prior_window.empty:
        return {"sufficient_data": False, "message": "Insufficient historical data for this analysis."}

    latest_rev = latest_window["revenue"].sum()
    prior_rev = prior_window["revenue"].sum()
    latest_gp = latest_window["gross_profit"].sum()
    prior_gp = prior_window["gross_profit"].sum()
    latest_margin = (latest_gp / latest_rev * 100) if latest_rev else 0.0
    prior_margin = (prior_gp / prior_rev * 100) if prior_rev else 0.0
    latest_opex = latest_window["operating_expenses"].sum()
    prior_opex = prior_window["operating_expenses"].sum()
    latest_opex_ratio = (latest_opex / latest_rev * 100) if latest_rev else 0.0
    prior_opex_ratio = (prior_opex / prior_rev * 100) if prior_rev else 0.0

    revenue_change_pct = ((latest_rev - prior_rev) / prior_rev * 100) if prior_rev else 0.0
    margin_change_pp = latest_margin - prior_margin

    return {
        "sufficient_data": True,
        "prior_year": int(prior_year),
        "latest_year": int(latest_year),
        "prior_period_revenue": float(prior_rev),
        "latest_period_revenue": float(latest_rev),
        "revenue_change_pct": float(revenue_change_pct),
        "prior_gross_margin_pct": float(prior_margin),
        "latest_gross_margin_pct": float(latest_margin),
        "margin_change_pp": float(margin_change_pp),
        "prior_opex_ratio_pct": float(prior_opex_ratio),
        "latest_opex_ratio_pct": float(latest_opex_ratio),
    }


def profitability_stability(monthly: pd.DataFrame) -> dict:
    total_months = len(monthly)
    profitable_months = int((monthly["operating_profit"] > 0).sum())
    pct_profitable = (profitable_months / total_months * 100) if total_months else 0.0

    # longest consecutive loss-making streak (for persistent-loss driver)
    loss_flags = (monthly["operating_profit"] <= 0).tolist()
    longest_streak, current_streak = 0, 0
    for flag in loss_flags:
        if flag:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    return {
        "total_months": total_months,
        "profitable_months": profitable_months,
        "pct_profitable_months": pct_profitable,
        "longest_consecutive_loss_streak": longest_streak,
    }
