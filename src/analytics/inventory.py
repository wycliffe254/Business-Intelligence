"""Inventory analytics.

Per Expected Output Spec Sec. 4 / 24: conventional inventory turnover
must NOT be computed when reconstructed stock is negative for any
product. This module always returns whether the inventory is usable for
scoring, and only computes turnover when it is.
"""

from __future__ import annotations

import pandas as pd


def inventory_status(inventory_summary: pd.DataFrame) -> dict:
    negative_products = inventory_summary.loc[
        inventory_summary["has_negative_stock"], "product_name"
    ].tolist()
    usable = len(negative_products) == 0
    return {
        "usable_for_scoring": usable,
        "negative_stock_products": negative_products,
        "message": (
            "Inventory analysis unavailable for financial scoring. Reason: "
            "Inventory records cannot currently support a reliable "
            "stock-on-hand calculation."
            if not usable
            else "Inventory reconstruction is internally consistent for all products."
        ),
    }


def inventory_turnover(df: pd.DataFrame, inventory_summary: pd.DataFrame, core: dict) -> dict | None:
    """Only computed when inventory_status()['usable_for_scoring'] is True.
    Inventory Turnover = COGS / Average Inventory Value (Spec Sec. 24).

    Average Inventory Value is approximated as the mean of total
    business-wide inventory value (at cost) at the start and end of the
    period, reconstructed from `inventory_value_change_kes`. This is a
    two-point average, not a full time-weighted average — a documented
    simplification for an academic prototype.
    """
    status = inventory_status(inventory_summary)
    if not status["usable_for_scoring"]:
        return None

    if "opening_value" not in inventory_summary.columns or "ending_value" not in inventory_summary.columns:
        return None

    opening_total_value = float(inventory_summary["opening_value"].sum())
    ending_total_value = float(inventory_summary["ending_value"].sum())
    avg_inventory_value = (opening_total_value + ending_total_value) / 2

    if avg_inventory_value <= 0:
        return None
    return {
        "turnover_ratio": core["cogs"] / avg_inventory_value,
        "opening_inventory_value": opening_total_value,
        "ending_inventory_value": ending_total_value,
        "average_inventory_value": avg_inventory_value,
    }
