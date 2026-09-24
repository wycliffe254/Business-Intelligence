"""Overall RAG classification, including the five critical-risk override
rules (Expected Output Spec Sec. 25-26) that force RED regardless of the
numeric score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import settings


@dataclass
class RagResult:
    status: str
    score_based_status: str
    triggered_overrides: list = field(default_factory=list)


def _score_band(score: float) -> str:
    if score >= settings.RAG_GREEN_MIN:
        return "GREEN"
    if score >= settings.RAG_AMBER_MIN:
        return "AMBER"
    return "RED"


def classify(kpis: dict, health_score: float, dq_report) -> RagResult:
    score_status = _score_band(health_score)
    triggered = []

    core = kpis["core"]
    comparable = kpis["comparable_yoy"]
    collections = kpis["collections"]
    stability = kpis["profitability_stability"]

    cfg = settings.CRITICAL_OVERRIDES

    # Rule 1 — Persistent Operating Loss
    r1 = cfg["persistent_operating_loss"]
    if (
        core["operating_margin_pct"] < r1["operating_margin_threshold"]
        and stability["longest_consecutive_loss_streak"] >= r1["min_consecutive_months"]
    ):
        triggered.append({
            "rule": "Persistent Operating Loss",
            "explanation": (
                f"Operating margin ({core['operating_margin_pct']:.1f}%) is below "
                f"{r1['operating_margin_threshold']:.0f}% and losses have persisted for "
                f"{stability['longest_consecutive_loss_streak']} consecutive months "
                f"(threshold: {r1['min_consecutive_months']})."
            ),
        })

    # Rule 2 — Severe Revenue Deterioration
    r2 = cfg["severe_revenue_deterioration"]
    if comparable.get("sufficient_data"):
        rev_decline = comparable["revenue_change_pct"]
        margin_deteriorated = comparable["margin_change_pp"] < 0
        if rev_decline <= r2["revenue_decline_threshold"] and (
            margin_deteriorated or not r2["requires_margin_deterioration"]
        ):
            triggered.append({
                "rule": "Severe Revenue Deterioration",
                "explanation": (
                    f"Comparable-period revenue fell {rev_decline:.1f}% (threshold "
                    f"{r2['revenue_decline_threshold']:.0f}%) alongside a "
                    f"{comparable['margin_change_pp']:.1f} percentage-point gross-margin decline."
                ),
            })

    # Rule 3 — Severe Collection Failure
    r3 = cfg["severe_collection_failure"]
    if collections["collection_coverage_pct"] < r3["collection_coverage_threshold"]:
        triggered.append({
            "rule": "Severe Collection Failure",
            "explanation": (
                f"Collection coverage ({collections['collection_coverage_pct']:.1f}%) is below "
                f"{r3['collection_coverage_threshold']:.0f}%."
            ),
        })

    # Rule 4 — Severe Margin Deterioration
    r4 = cfg["severe_margin_deterioration"]
    if comparable.get("sufficient_data") and comparable["margin_change_pp"] <= -r4["gross_margin_decline_pp_threshold"]:
        triggered.append({
            "rule": "Severe Margin Deterioration",
            "explanation": (
                f"Gross margin declined by {abs(comparable['margin_change_pp']):.1f} percentage "
                f"points over the comparable period (threshold "
                f"{r4['gross_margin_decline_pp_threshold']:.0f}pp)."
            ),
        })

    # Rule 5 — Critical Data Integrity Failure
    if dq_report.status == "RED" and dq_report.overall_score < 40:
        triggered.append({
            "rule": "Critical Data Integrity Failure",
            "explanation": (
                "Core financial values cannot be reliably determined from the "
                f"current data (Data Quality Score {dq_report.overall_score:.0f}/100). "
                "This is a data-quality warning, not evidence that the business "
                "itself is financially unhealthy."
            ),
        })

    final_status = "RED" if triggered else score_status
    return RagResult(status=final_status, score_based_status=score_status, triggered_overrides=triggered)
