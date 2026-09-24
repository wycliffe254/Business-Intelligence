"""Top-level KPI orchestration: runs every analytics sub-module against
the analytical (validated) dataset and returns one consolidated result
dict used throughout the app.
"""

from __future__ import annotations

import pandas as pd

from src.analytics import efficiency, growth, inventory, liquidity, profitability
from src.data.cleaning import reconstruct_inventory


def compute_all_kpis(analytical_df: pd.DataFrame) -> dict:
    included = analytical_df[analytical_df["include_in_kpis"]].copy()

    core = profitability.compute_core_profitability(included)
    expense_breakdown = profitability.expense_breakdown(included)
    breakeven = profitability.break_even_analysis(included, core)
    collections = liquidity.collection_analysis(included)

    monthly = growth.monthly_series(included)
    recent = growth.recent_trend(monthly)
    comparable = growth.comparable_period_yoy(monthly)
    stability = growth.profitability_stability(monthly)

    product_cat = efficiency.product_category_performance(included)
    product = efficiency.product_performance(included)
    branch = efficiency.branch_performance(included)
    channel = efficiency.channel_performance(included)
    customer_type = efficiency.customer_type_performance(included)

    inv_summary = reconstruct_inventory(analytical_df)
    inv_status = inventory.inventory_status(inv_summary)
    inv_turnover = inventory.inventory_turnover(included, inv_summary, core)

    return {
        "core": core,
        "expense_breakdown": expense_breakdown,
        "breakeven": breakeven,
        "collections": collections,
        "monthly": monthly,
        "recent_trend": recent,
        "comparable_yoy": comparable,
        "profitability_stability": stability,
        "product_category": product_cat,
        "product": product,
        "branch": branch,
        "channel": channel,
        "customer_type": customer_type,
        "inventory_summary": inv_summary,
        "inventory_status": inv_status,
        "inventory_turnover": inv_turnover,
    }
