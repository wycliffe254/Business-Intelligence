import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.dates import parse_single_date
from src.data.cleaning import clean_dataset


def test_parse_iso_date():
    r = parse_single_date("2025-01-24")
    assert r.is_valid
    assert r.parsed == pd.Timestamp(2025, 1, 24)
    assert not r.is_ambiguous


def test_parse_unambiguous_dash_date():
    r = parse_single_date("31-03-2025")  # 31 can only be a day
    assert r.is_valid
    assert r.parsed == pd.Timestamp(2025, 3, 31)
    assert not r.is_ambiguous


def test_parse_unambiguous_slash_mdy():
    r = parse_single_date("08/19/2026")  # 19 can only be a day -> MM/DD
    assert r.is_valid
    assert r.parsed == pd.Timestamp(2026, 8, 19)


def test_parse_ambiguous_defaults_day_first():
    r = parse_single_date("03/04/2025")
    assert r.is_valid
    assert r.is_ambiguous
    assert r.parsed == pd.Timestamp(2025, 4, 3)  # day-first assumption


def test_parse_invalid_date():
    r = parse_single_date("not-a-date")
    assert not r.is_valid


def test_parse_missing_date():
    r = parse_single_date(None)
    assert not r.is_valid


def _minimal_df():
    return pd.DataFrame({
        "transaction_id": ["TXN-1", "TXN-1", "TXN-2"],
        "transaction_date": ["2025-01-01", "2025-01-01", "2025-01-02"],
        "transaction_type": ["SALE", "SALE", "SALE"],
        "document_no": ["D1", "D1", "D2"],
        "business_name": ["B"] * 3,
        "branch": ["Kiserian", "Kiserian", "Kiserian"],
        "sales_channel": ["Walk-in"] * 3,
        "customer_type": ["Retail"] * 3,
        "customer_id": ["C1"] * 3,
        "supplier_name": [None] * 3,
        "product_category": ["Paints"] * 3,
        "product_name": ["Paint"] * 3,
        "quantity": ["1", "1", "0"],
        "unit_price_kes": ["100", "100", "100"],
        "discount_pct": ["0", "0", "0"],
        "gross_sales_kes": ["100", "100", "100"],
        "net_sales_kes": ["100", "100", "100"],
        "unit_cost_kes": ["50", "50", "50"],
        "cogs_kes": ["50", "50", "50"],
        "gross_profit_kes": ["50", "50", "50"],
        "expense_category": [None] * 3,
        "expense_amount_kes": ["0", "0", "0"],
        "cash_in_kes": ["100", "100", "100"],
        "cash_out_kes": ["0", "0", "0"],
        "amount_received_kes": ["100", "100", "100"],
        "accounts_receivable_change_kes": ["0", "0", "0"],
        "accounts_payable_change_kes": ["0", "0", "0"],
        "inventory_qty_change": ["-1", "-1", "0"],
        "inventory_value_change_kes": ["-50", "-50", "0"],
        "payment_method": [None, None, None],
        "salesperson_or_staff": ["S"] * 3,
        "manual_entry_flag": ["0", "0", "0"],
    })


def test_duplicate_detection():
    result = clean_dataset(_minimal_df())
    df = result["analytical_df"]
    assert result["exclusion_summary"]["duplicate_transaction_id"] == 1
    assert df.loc[1, "is_duplicate_txn_id"]
    assert not df.loc[0, "is_duplicate_txn_id"]


def test_invalid_sale_quantity_flag():
    result = clean_dataset(_minimal_df())
    df = result["analytical_df"]
    # row 2 has quantity 0 but net_sales_kes > 0 -> invalid
    assert df.loc[2, "is_invalid_sale_quantity"]
