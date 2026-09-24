import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.loader import load_default_sample
from src.data.cleaning import clean_dataset, reconstruct_inventory
from src.data.validation import build_data_quality_report
from src.analytics.kpis import compute_all_kpis
from src.explainability.drivers import detect_drivers
from src.explainability.explanations import build_explanation_cards, build_executive_summary
from src.explainability.recommendations import build_recommendations
from src.health.scoring import compute_health_score
from src.health.rag import classify as classify_rag


def _pipeline():
    load_result = load_default_sample()
    clean_result = clean_dataset(load_result.raw_df)
    analytical_df = clean_result["analytical_df"]
    inv_summary = reconstruct_inventory(analytical_df)
    dq_report = build_data_quality_report(
        analytical_df, clean_result["flags"], clean_result["exclusion_summary"], inv_summary
    )
    kpis = compute_all_kpis(analytical_df)
    return kpis, dq_report


def test_margin_pressure_driver_triggers():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    driver_a = next(d for d in drivers if d.code == "A")
    # Gross margin ~21% is close to but not always <20%; margin decline
    # of ~5pp should still trigger this driver via the decline condition.
    assert driver_a.triggered


def test_operating_cost_pressure_driver_triggers():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    driver_b = next(d for d in drivers if d.code == "B")
    # opex ratio ~42% > 35% threshold
    assert driver_b.triggered


def test_inventory_integrity_driver_triggers():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    driver_g = next(d for d in drivers if d.code == "G")
    assert driver_g.triggered


def test_all_seven_drivers_present():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    codes = {d.code for d in drivers}
    assert codes == {"A", "B", "C", "D", "E", "F", "G"}


def test_explanation_cards_generated_for_triggered_drivers():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    cards = build_explanation_cards(kpis, drivers)
    assert len(cards) > 0
    for c in cards:
        assert c.finding and c.evidence and c.driver and c.impact and c.recommendation


def test_recommendations_are_evidence_linked_and_prioritized():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    recs = build_recommendations(kpis, drivers)
    assert len(recs) > 0
    priorities = [r.priority for r in recs]
    assert priorities == sorted(priorities)
    for r in recs:
        assert "Improve your business finances" not in r.management_action
        assert r.evidence  # every recommendation must cite evidence


def test_executive_summary_mentions_revenue_and_status():
    kpis, dq = _pipeline()
    drivers = detect_drivers(kpis, dq)
    health = compute_health_score(kpis, dq.overall_score, dq.inventory_integrity_ok)
    rag = classify_rag(kpis, health.total_score, dq)
    summary = build_executive_summary(kpis, health.total_score, rag.status, dq, drivers)
    assert "revenue" in summary.lower() or "KES" in summary
    assert len(summary) > 50
