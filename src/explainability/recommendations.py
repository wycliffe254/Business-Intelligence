"""Recommendation engine: converts triggered drivers + KPI evidence into
prioritized, evidence-linked management recommendations (never generic
advice). Priority order follows Expected Output Spec Sec. 34.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import CURRENCY_SYMBOL


@dataclass
class Recommendation:
    priority: int
    category: str
    title: str
    observed_issue: str
    evidence: str
    management_action: str


def _fmt_kes(value: float) -> str:
    return f"{CURRENCY_SYMBOL} {value:,.0f}"


def build_recommendations(kpis: dict, drivers: list) -> list:
    driver_map = {d.code: d for d in drivers}
    core = kpis["core"]
    comparable = kpis["comparable_yoy"]
    product_cat = kpis["product_category"]
    recs = []

    # Priority 1 — Restore Operating Profitability (only if op. loss)
    if core["operating_profit"] < 0:
        recs.append(Recommendation(
            priority=1, category="Profitability",
            title="Restore Operating Profitability",
            observed_issue="The business is operating at a loss.",
            evidence=f"Operating margin \u2248 {core['operating_margin_pct']:.1f}%; operating loss \u2248 {_fmt_kes(abs(core['operating_profit']))}.",
            management_action=(
                "Investigate the combined effect of gross margin deterioration and "
                "operating expenses; both sides of the equation need attention "
                "simultaneously rather than in isolation."
            ),
        ))

    # Priority 2 — Protect and Recover Revenue
    if driver_map.get("C") and driver_map["C"].triggered:
        decline = comparable.get("revenue_change_pct", 0.0) if comparable.get("sufficient_data") else 0.0
        recs.append(Recommendation(
            priority=2, category="Revenue",
            title="Protect and Recover Revenue",
            observed_issue="Revenue has declined against the preceding/comparable period.",
            evidence=f"Comparable-period revenue change \u2248 {decline:.1f}%.",
            management_action=(
                "Identify the specific product, customer, branch and channel sources "
                "of the revenue decline rather than treating it as a single "
                "company-wide problem."
            ),
        ))

    # Priority 3 — Improve Margin
    if driver_map.get("A") and driver_map["A"].triggered:
        low_margin_high_rev = product_cat[
            (product_cat["revenue_share_pct"] >= product_cat["revenue_share_pct"].median())
            & (product_cat["gross_margin_pct"] < product_cat["gross_margin_pct"].median())
        ].sort_values("revenue_share_pct", ascending=False)
        names = ", ".join(low_margin_high_rev["product_category"].head(2).tolist())
        recs.append(Recommendation(
            priority=3, category="Margin",
            title="Improve Margin",
            observed_issue="Gross margin is weak or deteriorating.",
            evidence=f"Gross margin \u2248 {core['gross_margin_pct']:.1f}%." + (f" Categories with meaningful sales but relatively low margin: {names}." if names else ""),
            management_action=(
                "Review pricing, supplier costs, discounts and product-level "
                "contribution, prioritizing categories with meaningful sales "
                "contribution but relatively low margin."
            ),
        ))

    # Priority 4 — Control Operating Costs
    if driver_map.get("B") and driver_map["B"].triggered:
        top = kpis["expense_breakdown"].head(3)
        names = ", ".join(top["expense_category"].tolist())
        recs.append(Recommendation(
            priority=4, category="Operating Cost",
            title="Control Operating Costs",
            observed_issue="Operating expenses consume a high proportion of revenue.",
            evidence=f"Operating expense ratio \u2248 {core['opex_ratio_pct']:.1f}%. Largest categories: {names}.",
            management_action=(
                f"Review the structure of {names}, which together account for a "
                "large proportion of operating expenditure. Assess whether each "
                "cost is fixed, variable, necessary, or capable of being reduced "
                "without damaging revenue generation."
            ),
        ))

    # Discount recommendation (tie to Driver F, unranked priority slot near cost/margin)
    if driver_map.get("F") and driver_map["F"].triggered:
        recs.append(Recommendation(
            priority=4, category="Discounting",
            title="Introduce Discount Controls",
            observed_issue="Discounting is materially affecting realized selling prices.",
            evidence=f"Weighted discount rate \u2248 {core['discount_rate_pct']:.1f}%.",
            management_action=(
                "Introduce discount controls or approval thresholds for discounts "
                "above the normal range and monitor whether discounted "
                "transactions generate sufficient incremental sales."
            ),
        ))

    # Priority 5 — Improve Credit Collection
    if driver_map.get("E") and driver_map["E"].triggered:
        collections = kpis["collections"]
        recs.append(Recommendation(
            priority=5, category="Credit / Collections",
            title="Improve Credit Collection",
            observed_issue="A portion of credit-like sales remains uncollected.",
            evidence=f"Collection coverage \u2248 {collections['collection_coverage_pct']:.1f}%; estimated uncollected exposure \u2248 {_fmt_kes(collections['estimated_uncollected_exposure'])}.",
            management_action=(
                "Review credit customers contributing to the estimated outstanding "
                "exposure and strengthen collection follow-up and credit terms "
                "where appropriate."
            ),
        ))

    # Priority 6 — Reconcile Inventory Data
    if driver_map.get("G") and driver_map["G"].triggered:
        recs.append(Recommendation(
            priority=6, category="Inventory / Data Integrity",
            title="Reconcile Inventory Data",
            observed_issue="Reconstructed inventory balances are negative.",
            evidence=f"{len(driver_map['G'].evidence.get('negative_stock_products', []))} product line(s) affected.",
            management_action=(
                "Do not use the current inventory data for procurement "
                "optimization. First reconcile opening stock, purchases, sales "
                "and stock adjustments."
            ),
        ))

    return sorted(recs, key=lambda r: r.priority)
