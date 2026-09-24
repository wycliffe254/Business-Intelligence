"""Rule-based driver detection. Each driver fires strictly from the
thresholds in config/settings.py (verbatim from Expected Output Spec
Sec. 29) and carries the evidence used to trigger it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import settings


@dataclass
class Driver:
    code: str
    name: str
    triggered: bool
    evidence: dict = field(default_factory=dict)
    narrative: str = ""


def detect_drivers(kpis: dict, dq_report) -> list:
    drivers = []
    core = kpis["core"]
    comparable = kpis["comparable_yoy"]
    recent = kpis["recent_trend"]
    stability = kpis["profitability_stability"]
    collections = kpis["collections"]
    inv_status = kpis["inventory_status"]
    t = settings.DRIVER_THRESHOLDS

    # Driver A — Margin Pressure
    margin_low = core["gross_margin_pct"] < t["margin_pressure"]["gross_margin_below_pct"]
    margin_falling = (
        comparable.get("sufficient_data")
        and comparable["margin_change_pp"] <= -t["margin_pressure"]["gross_margin_decline_pp"]
    )
    drivers.append(Driver(
        code="A", name="Margin Pressure",
        triggered=bool(margin_low or margin_falling),
        evidence={
            "gross_margin_pct": core["gross_margin_pct"],
            "margin_change_pp": comparable.get("margin_change_pp"),
        },
        narrative=(
            "Gross margin has weakened, indicating that the business is retaining "
            "less gross profit from each shilling of sales. Investigate supplier "
            "costs, selling prices, discounting, and product-level margins."
        ),
    ))

    # Driver B — Excessive Operating-Cost Burden
    opex_high = core["opex_ratio_pct"] > t["operating_cost_pressure"]["opex_to_revenue_above_pct"]
    top_expenses = kpis["expense_breakdown"].head(3)
    drivers.append(Driver(
        code="B", name="Excessive Operating-Cost Burden",
        triggered=bool(opex_high),
        evidence={
            "opex_ratio_pct": core["opex_ratio_pct"],
            "top_expense_categories": top_expenses.to_dict("records") if not top_expenses.empty else [],
        },
        narrative=(
            "Operating expenses consume a high proportion of revenue. The largest "
            "expense categories should be prioritized for management review."
        ),
    ))

    # Driver C — Revenue Deterioration
    recent_decline = (
        recent.get("sufficient_data")
        and recent["change_pct"] <= -t["revenue_deterioration"]["recent_decline_above_pct"]
    )
    drivers.append(Driver(
        code="C", name="Revenue Deterioration",
        triggered=bool(recent_decline),
        evidence={"recent_change_pct": recent.get("change_pct")},
        narrative=(
            "Revenue has declined compared with the preceding period. Investigate "
            "changes by branch, customer type, product category and sales channel "
            "rather than treating the decline as a single company-wide problem."
        ),
    ))

    # Driver D — Persistent Losses
    persistent = stability["longest_consecutive_loss_streak"] >= t["persistent_losses"]["min_consecutive_loss_months"]
    drivers.append(Driver(
        code="D", name="Persistent Losses",
        triggered=bool(persistent),
        evidence={"longest_consecutive_loss_streak": stability["longest_consecutive_loss_streak"]},
        narrative=(
            "Operating losses are persistent rather than isolated. The business "
            "requires investigation of the structural relationship between gross "
            "margin, revenue volume and operating expenses."
        ),
    ))

    # Driver E — Weak Collection
    weak_collection = collections["collection_coverage_pct"] < t["weak_collection"]["collection_coverage_below_pct"]
    drivers.append(Driver(
        code="E", name="Weak Collection",
        triggered=bool(weak_collection),
        evidence={
            "collection_coverage_pct": collections["collection_coverage_pct"],
            "estimated_uncollected_exposure": collections["estimated_uncollected_exposure"],
        },
        narrative=(
            "A portion of credit sales remains uncollected. Management should "
            "review customer-level outstanding balances and credit terms. Because "
            "this dataset lacks proper invoice-aging fields, this is a "
            "portfolio-level collection signal, not confirmed aging."
        ),
    ))

    # Driver F — Discount Pressure
    discount_high = core["discount_rate_pct"] > t["discount_pressure"]["weighted_discount_rate_above_pct"]
    drivers.append(Driver(
        code="F", name="Discount Pressure",
        triggered=bool(discount_high),
        evidence={"discount_rate_pct": core["discount_rate_pct"]},
        narrative=(
            "Discounting is beginning to affect realized selling prices. Review "
            "discounts by product, customer type and salesperson to determine "
            "whether discounts are generating enough additional volume to justify "
            "the margin reduction."
        ),
    ))

    # Driver G — Inventory Data Integrity
    inv_failed = not inv_status["usable_for_scoring"]
    drivers.append(Driver(
        code="G", name="Inventory Data Integrity",
        triggered=bool(inv_failed),
        evidence={"negative_stock_products": inv_status["negative_stock_products"]},
        narrative=(
            "Inventory records are internally inconsistent. Stock-on-hand should "
            "be reconciled before inventory turnover, stockout or replenishment "
            "recommendations are used for decision-making."
        ),
    ))

    return drivers
