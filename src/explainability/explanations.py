"""Evidence-linked explanation cards (Finding / Evidence / Driver / Impact
/ Recommendation) and the automated executive summary.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import CURRENCY_SYMBOL


@dataclass
class ExplanationCard:
    finding: str
    evidence: str
    driver: str
    impact: str
    recommendation: str


def _fmt_kes(value: float) -> str:
    return f"{CURRENCY_SYMBOL} {value:,.0f}"


def build_explanation_cards(kpis: dict, drivers: list) -> list:
    cards = []
    core = kpis["core"]
    breakeven = kpis["breakeven"]
    comparable = kpis["comparable_yoy"]

    if core["operating_profit"] < 0:
        gap = breakeven["avg_monthly_opex"] - breakeven["avg_monthly_gross_profit"]
        cards.append(ExplanationCard(
            finding="Operating profitability is negative.",
            evidence=f"Operating margin \u2248 {core['operating_margin_pct']:.1f}%.",
            driver="Gross profit is insufficient to cover the operating expense base.",
            impact=(
                f"Average monthly gross profit is approximately {_fmt_kes(breakeven['avg_monthly_gross_profit'])} "
                f"while average monthly operating expenses are approximately {_fmt_kes(breakeven['avg_monthly_opex'])} "
                f"\u2014 a gap of approximately {_fmt_kes(gap)} per month."
            ),
            recommendation=(
                "Management should address both sides of the equation: improve gross "
                "margin/revenue contribution and review the largest controllable "
                "operating-cost categories."
            ),
        ))

    for d in drivers:
        if not d.triggered:
            continue
        if d.code == "A":
            cards.append(ExplanationCard(
                finding="Gross margin has weakened.",
                evidence=f"Gross margin \u2248 {d.evidence.get('gross_margin_pct', 0):.1f}%"
                + (f", a change of {d.evidence.get('margin_change_pp'):.1f}pp over the comparable period." if d.evidence.get("margin_change_pp") is not None else "."),
                driver="Margin Pressure (Driver A)",
                impact="Each shilling of sales now converts into less gross profit than before.",
                recommendation=d.narrative,
            ))
        elif d.code == "B":
            top = d.evidence.get("top_expense_categories", [])
            top_names = ", ".join(f"{r['expense_category']} ({r['share_pct']:.0f}%)" for r in top[:3])
            cards.append(ExplanationCard(
                finding="Operating expenses consume a high share of revenue.",
                evidence=f"Operating expense ratio \u2248 {d.evidence.get('opex_ratio_pct', 0):.1f}%.",
                driver="Excessive Operating-Cost Burden (Driver B)",
                impact=f"Largest categories: {top_names}." if top_names else "See expense breakdown.",
                recommendation=d.narrative,
            ))
        elif d.code == "C":
            cards.append(ExplanationCard(
                finding="Revenue has declined against the preceding period.",
                evidence=f"Recent 3-month revenue change \u2248 {d.evidence.get('recent_change_pct', 0):.1f}%.",
                driver="Revenue Deterioration (Driver C)",
                impact="Lower sales volume directly reduces gross profit available to cover fixed costs.",
                recommendation=d.narrative,
            ))
        elif d.code == "D":
            cards.append(ExplanationCard(
                finding="Operating losses are persistent, not a single bad month.",
                evidence=f"Longest consecutive loss-making streak: {d.evidence.get('longest_consecutive_loss_streak')} months.",
                driver="Persistent Losses (Driver D)",
                impact="A structural, not seasonal, imbalance between revenue, margin and cost appears present.",
                recommendation=d.narrative,
            ))
        elif d.code == "E":
            cards.append(ExplanationCard(
                finding="A meaningful share of credit sales remains uncollected.",
                evidence=f"Collection coverage \u2248 {d.evidence.get('collection_coverage_pct', 0):.1f}%; estimated uncollected exposure \u2248 {_fmt_kes(d.evidence.get('estimated_uncollected_exposure', 0))}.",
                driver="Weak Collection (Driver E)",
                impact="Cash available to the business is lower than reported sales would suggest.",
                recommendation=d.narrative,
            ))
        elif d.code == "F":
            cards.append(ExplanationCard(
                finding="Discounting is materially affecting realized prices.",
                evidence=f"Weighted discount rate \u2248 {d.evidence.get('discount_rate_pct', 0):.1f}%.",
                driver="Discount Pressure (Driver F)",
                impact="Discounts reduce realized revenue and, in turn, gross margin.",
                recommendation=d.narrative,
            ))
        elif d.code == "G":
            products = d.evidence.get("negative_stock_products", [])
            cards.append(ExplanationCard(
                finding="Reconstructed inventory balances are invalid.",
                evidence=f"{len(products)} product line(s) show negative reconstructed stock.",
                driver="Inventory Data Integrity (Driver G)",
                impact="Inventory-based KPIs (turnover, stockout risk) cannot be trusted until resolved.",
                recommendation=d.narrative,
            ))
    return cards


def build_executive_summary(kpis: dict, health_score: float, rag_status: str, dq_report, drivers: list) -> str:
    core = kpis["core"]
    comparable = kpis["comparable_yoy"]
    breakeven = kpis["breakeven"]
    top_expenses = kpis["expense_breakdown"].head(2)

    triggered = [d for d in drivers if d.triggered]
    top_driver_names = ", ".join(d.name for d in triggered[:5]) if triggered else "no major risk drivers were triggered"

    lines = []
    if rag_status == "RED":
        lines.append("Business performance requires immediate management attention.")
    elif rag_status == "AMBER":
        lines.append("Business performance shows areas that require closer management attention.")
    else:
        lines.append("Business performance is currently within an acceptable range, with some areas worth monitoring.")

    lines.append(
        f"The business generated approximately {_fmt_kes(core['adjusted_revenue'])} in adjusted revenue "
        f"and produced {'an operating loss' if core['operating_profit'] < 0 else 'an operating profit'} of "
        f"approximately {_fmt_kes(abs(core['operating_profit']))}."
    )

    if comparable.get("sufficient_data"):
        lines.append(
            f"Comparable {comparable['prior_year']}\u2013{comparable['latest_year']} revenue for the same "
            f"months changed by approximately {comparable['revenue_change_pct']:.1f}%, while gross margin "
            f"moved by approximately {comparable['margin_change_pp']:.1f} percentage points."
        )

    if not top_expenses.empty:
        names = " and ".join(top_expenses["expense_category"].tolist())
        lines.append(f"The largest operating expense categories are {names}.")

    lines.append(f"Key drivers identified: {top_driver_names}.")

    if dq_report.status != "GREEN":
        lines.append(
            f"Data reliability is currently {dq_report.status} ({dq_report.overall_score:.0f}/100); "
            "some results (see Data Quality page) should be treated as provisional."
        )

    if breakeven.get("breakeven_revenue") == breakeven.get("breakeven_revenue"):  # not NaN
        gap_pct = breakeven.get("revenue_gap_pct")
        if gap_pct is not None and gap_pct == gap_pct and gap_pct > 0:
            lines.append(
                f"At the current margin and cost structure, the business would need roughly "
                f"{gap_pct:.0f}% more monthly revenue to reach operating break-even \u2014 "
                "revenue growth alone is unlikely to be sufficient without also addressing margin or cost structure."
            )

    return " ".join(lines)
