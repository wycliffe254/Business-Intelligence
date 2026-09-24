"""Composite Financial Health Score (0-100), transparent component
breakdown, per Expected Output Spec Sec. 19-24.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import settings
from src.health.thresholds import band_score, interpolate_score


@dataclass
class ScoreComponent:
    name: str
    points: float
    max_points: float
    detail: dict = field(default_factory=dict)


@dataclass
class HealthScoreResult:
    total_score: float
    components: list  # list[ScoreComponent], one per top-level dimension
    subcomponents: dict  # dimension_name -> list[ScoreComponent]


def _profitability_score(kpis: dict) -> ScoreComponent:
    core = kpis["core"]
    comparable = kpis["comparable_yoy"]

    gm_points = interpolate_score(core["gross_margin_pct"], settings.GROSS_MARGIN_SCORE_POINTS)
    om_points = interpolate_score(core["operating_margin_pct"], settings.OPERATING_MARGIN_SCORE_POINTS)

    gp_trend_pct = comparable.get("revenue_change_pct", 0.0) if comparable.get("sufficient_data") else 0.0
    gp_trend_points = interpolate_score(gp_trend_pct, settings.GROSS_PROFIT_TREND_SCORE_POINTS)

    subs = [
        ScoreComponent("Gross Margin", gm_points, settings.PROFITABILITY_SUBWEIGHTS["gross_margin"],
                        {"gross_margin_pct": core["gross_margin_pct"]}),
        ScoreComponent("Operating Margin", om_points, settings.PROFITABILITY_SUBWEIGHTS["operating_margin"],
                        {"operating_margin_pct": core["operating_margin_pct"]}),
        ScoreComponent("Gross Profit Trend", gp_trend_points, settings.PROFITABILITY_SUBWEIGHTS["gross_profit_trend"],
                        {"comparable_revenue_change_pct": gp_trend_pct}),
    ]
    total = sum(s.points for s in subs)
    return ScoreComponent("Profitability", total, settings.WEIGHTS["profitability"], {"subcomponents": subs}), subs


def _liquidity_score(kpis: dict) -> ScoreComponent:
    collections = kpis["collections"]

    coverage_points = band_score(collections["collection_coverage_pct"], settings.COLLECTION_COVERAGE_SCORE_TABLE)

    ratio = collections["revenue_to_opex_ratio"]
    ratio_capped = ratio if ratio != float("inf") else 999
    opex_cov_points = interpolate_score(ratio_capped, settings.REVENUE_TO_OPEX_SCORE_POINTS)

    core = kpis["core"]
    avg_monthly_sales = core["adjusted_revenue"] / max(kpis["breakeven"]["n_months"], 1)
    exposure_ratio = (
        collections["estimated_uncollected_exposure"] / avg_monthly_sales if avg_monthly_sales else 0.0
    )
    exposure_points = interpolate_score(exposure_ratio, settings.UNCOLLECTED_EXPOSURE_SCORE_POINTS)

    subs = [
        ScoreComponent("Collection Coverage", coverage_points, 10, {"collection_coverage_pct": collections["collection_coverage_pct"]}),
        ScoreComponent("Revenue-to-Opex Coverage", opex_cov_points, 5, {"revenue_to_opex_ratio": ratio}),
        ScoreComponent("Uncollected Credit Exposure", exposure_points, 5, {"exposure_ratio_of_monthly_sales": exposure_ratio}),
    ]
    total = sum(s.points for s in subs)
    return ScoreComponent("Liquidity & Collections", total, settings.WEIGHTS["liquidity_collections"], {"subcomponents": subs}), subs


def _cost_efficiency_score(kpis: dict) -> ScoreComponent:
    core = kpis["core"]
    opex_points = interpolate_score(core["opex_ratio_pct"], settings.OPEX_RATIO_SCORE_POINTS)
    discount_points = interpolate_score(core["discount_rate_pct"], settings.DISCOUNT_SCORE_POINTS)
    refund_points = interpolate_score(core["refund_rate_pct"], settings.REFUND_SCORE_POINTS)

    subs = [
        ScoreComponent("Operating Expense Ratio", opex_points, 10, {"opex_ratio_pct": core["opex_ratio_pct"]}),
        ScoreComponent("Discount Discipline", discount_points, 5, {"discount_rate_pct": core["discount_rate_pct"]}),
        ScoreComponent("Refund Rate", refund_points, 5, {"refund_rate_pct": core["refund_rate_pct"]}),
    ]
    total = sum(s.points for s in subs)
    return ScoreComponent("Cost & Operating Efficiency", total, settings.WEIGHTS["cost_efficiency"], {"subcomponents": subs}), subs


def _growth_stability_score(kpis: dict) -> ScoreComponent:
    recent = kpis["recent_trend"]
    stability = kpis["profitability_stability"]

    trend_pct = recent.get("change_pct", 0.0) if recent.get("sufficient_data") else 0.0
    trend_points = interpolate_score(trend_pct, settings.REVENUE_TREND_SCORE_POINTS)

    pct_profitable = stability["pct_profitable_months"]
    stability_points = interpolate_score(pct_profitable, settings.PROFITABLE_MONTHS_SCORE_POINTS)

    subs = [
        ScoreComponent("Recent Revenue Trend", trend_points, 10, {"recent_3mo_change_pct": trend_pct}),
        ScoreComponent("Profitability Stability", stability_points, 5, {"pct_profitable_months": pct_profitable}),
    ]
    total = sum(s.points for s in subs)
    return ScoreComponent("Growth & Stability", total, settings.WEIGHTS["growth_stability"], {"subcomponents": subs}), subs


def _data_reliability_score(dq_score: float, inventory_ok: bool) -> ScoreComponent:
    points = interpolate_score(dq_score, settings.DATA_RELIABILITY_SCORE_POINTS)
    if not inventory_ok:
        points = max(0.0, points - settings.INVENTORY_INTEGRITY_PENALTY_POINTS)
    detail = {"data_quality_score": dq_score, "inventory_integrity_ok": inventory_ok}
    return ScoreComponent("Working Capital / Data Reliability", points, settings.WEIGHTS["data_working_capital"], detail), []


def compute_health_score(kpis: dict, dq_score: float, inventory_ok: bool) -> HealthScoreResult:
    profitability_comp, profitability_subs = _profitability_score(kpis)
    liquidity_comp, liquidity_subs = _liquidity_score(kpis)
    cost_comp, cost_subs = _cost_efficiency_score(kpis)
    growth_comp, growth_subs = _growth_stability_score(kpis)
    data_comp, data_subs = _data_reliability_score(dq_score, inventory_ok)

    components = [profitability_comp, liquidity_comp, cost_comp, growth_comp, data_comp]
    total = sum(c.points for c in components)

    subcomponents = {
        "Profitability": profitability_subs,
        "Liquidity & Collections": liquidity_subs,
        "Cost & Operating Efficiency": cost_subs,
        "Growth & Stability": growth_subs,
        "Working Capital / Data Reliability": data_subs,
    }

    return HealthScoreResult(total_score=round(total, 1), components=components, subcomponents=subcomponents)
