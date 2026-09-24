import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.loader import load_default_sample
from src.data.cleaning import clean_dataset, reconstruct_inventory
from src.data.validation import build_data_quality_report
from src.analytics.kpis import compute_all_kpis
from src.health.scoring import compute_health_score
from src.health.rag import classify as classify_rag
from src.health.thresholds import interpolate_score, band_score


def test_interpolate_score_clamps_at_edges():
    table = [(0, 0), (10, 5), (20, 10)]
    assert interpolate_score(-5, table) == 0
    assert interpolate_score(25, table) == 10
    assert interpolate_score(5, table) == 2.5


def test_band_score_picks_correct_band():
    table = [(95, 10), (90, 9), (80, 7.5), (0, 2)]
    assert band_score(97, table) == 10
    assert band_score(85, table) == 7.5
    assert band_score(10, table) == 2


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


def test_health_score_within_0_100():
    kpis, dq = _pipeline()
    health = compute_health_score(kpis, dq.overall_score, dq.inventory_integrity_ok)
    assert 0 <= health.total_score <= 100


def test_health_score_components_sum_to_total():
    kpis, dq = _pipeline()
    health = compute_health_score(kpis, dq.overall_score, dq.inventory_integrity_ok)
    # total_score is rounded to 1dp while component points are not, so
    # allow rounding tolerance rather than requiring exact equality.
    assert abs(sum(c.points for c in health.components) - health.total_score) < 0.5


def test_rag_status_is_red_for_sample_dataset():
    kpis, dq = _pipeline()
    health = compute_health_score(kpis, dq.overall_score, dq.inventory_integrity_ok)
    rag = classify_rag(kpis, health.total_score, dq)
    # Expected Output Spec Sec. 27: final status should be RED
    assert rag.status == "RED"
    assert len(rag.triggered_overrides) > 0
