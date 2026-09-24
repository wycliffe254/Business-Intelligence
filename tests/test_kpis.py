import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.loader import load_default_sample
from src.data.cleaning import clean_dataset
from src.analytics.kpis import compute_all_kpis


def _sample_kpis():
    load_result = load_default_sample()
    assert load_result.success
    clean_result = clean_dataset(load_result.raw_df)
    return compute_all_kpis(clean_result["analytical_df"])


def test_adjusted_revenue_in_expected_range():
    kpis = _sample_kpis()
    revenue_m = kpis["core"]["adjusted_revenue"] / 1_000_000
    # Expected Output Spec: approximately KES 7.70M
    assert 7.0 < revenue_m < 8.5


def test_gross_margin_in_expected_range():
    kpis = _sample_kpis()
    # Expected Output Spec: approximately 21.3%
    assert 15 < kpis["core"]["gross_margin_pct"] < 27


def test_operating_profit_is_negative():
    kpis = _sample_kpis()
    # Expected Output Spec: approximately -KES 1.59M
    assert kpis["core"]["operating_profit"] < 0


def test_collection_coverage_in_expected_range():
    kpis = _sample_kpis()
    # Expected Output Spec: approximately 88.5%
    assert 75 < kpis["collections"]["collection_coverage_pct"] < 100


def test_inventory_flagged_negative():
    kpis = _sample_kpis()
    assert kpis["inventory_status"]["usable_for_scoring"] is False
