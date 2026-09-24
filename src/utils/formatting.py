"""Shared display-formatting helpers used across Streamlit pages."""

from __future__ import annotations

from config.settings import CURRENCY_SYMBOL


def kes(value: float, millions: bool = False) -> str:
    if value is None or value != value:
        return "N/A"
    if millions:
        return f"{CURRENCY_SYMBOL} {value / 1_000_000:,.2f}M"
    return f"{CURRENCY_SYMBOL} {value:,.0f}"


def pct(value: float, decimals: int = 1) -> str:
    if value is None or value != value:
        return "N/A"
    return f"{value:.{decimals}f}%"


def rag_color(status: str) -> str:
    return {"GREEN": "#1a7f37", "AMBER": "#b08800", "RED": "#c92a2a"}.get(status, "#666666")


def rag_badge_md(status: str, label: str | None = None) -> str:
    color = rag_color(status)
    text = label or status
    return f'<span style="background-color:{color};color:white;padding:2px 10px;border-radius:10px;font-weight:600;font-size:0.85em;">{text}</span>'


def kpi_rag(value: float, green_min: float | None = None, amber_min: float | None = None, inverse: bool = False) -> str:
    """Classify a single KPI value into GREEN/AMBER/RED given band edges.
    inverse=True means lower is better (e.g. opex ratio, discount rate).
    """
    if value is None or value != value:
        return "AMBER"
    if inverse:
        if green_min is not None and value <= green_min:
            return "GREEN"
        if amber_min is not None and value <= amber_min:
            return "AMBER"
        return "RED"
    else:
        if green_min is not None and value >= green_min:
            return "GREEN"
        if amber_min is not None and value >= amber_min:
            return "AMBER"
        return "RED"
