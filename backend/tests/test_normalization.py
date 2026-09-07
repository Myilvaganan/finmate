from app.parsers.base import RawTransactionRow
from app.services.normalization import normalize_row
from app.utils.dates import parse_transaction_date, is_date_ambiguous


def test_parses_ddmmyyyy_date():
    assert parse_transaction_date("15/01/2026").isoformat() == "2026-01-15"


def test_parses_iso_date():
    assert parse_transaction_date("2026-01-15").isoformat() == "2026-01-15"


def test_ambiguous_date_detection():
    assert is_date_ambiguous("05/01/2026") is True
    assert is_date_ambiguous("25/01/2026") is False


def test_separate_debit_credit_columns():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="SWIGGY", debit_raw="500", credit_raw="")
    txn = normalize_row(row, "acc1", "INR")
    assert txn.debit == 500.0
    assert txn.credit == 0.0
    assert txn.amount == -500.0


def test_single_amount_column_with_dr_type():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="SWIGGY", amount_raw="500", type_raw="Dr")
    txn = normalize_row(row, "acc1", "INR")
    assert txn.debit == 500.0
    assert txn.credit == 0.0


def test_single_amount_column_negative_value_is_debit():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="SWIGGY", amount_raw="-500")
    txn = normalize_row(row, "acc1", "INR")
    assert txn.debit == 500.0


def test_credit_column_maps_to_income_amount():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="SALARY", debit_raw="", credit_raw="90000")
    txn = normalize_row(row, "acc1", "INR")
    assert txn.credit == 90000.0
    assert txn.amount == 90000.0


def test_transfer_is_not_silently_turned_into_expense_amount_sign():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="UPI-JOHN-TRANSFER", debit_raw="1000", credit_raw="")
    txn = normalize_row(row, "acc1", "INR")
    assert txn.debit == 1000.0
    assert txn.amount == -1000.0


def test_invalid_date_returns_none():
    row = RawTransactionRow(row_index=0, transaction_date_raw="not-a-date", description_raw="X", debit_raw="10")
    assert normalize_row(row, "acc1", "INR") is None
