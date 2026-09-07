from app.parsers.pdf_parser import _looks_like_header_row, _dedupe_columns, _clean_cell, _clean_page_text


def test_looks_like_header_row_requires_date_and_balance():
    assert _looks_like_header_row(["Date", "Mode", "Particulars", "Deposits", "Withdrawals", "Balance"])
    assert _looks_like_header_row(["Date", "Transaction Details", "Chq No.", "Withdrawal", "Deposits", "Balance"])
    assert not _looks_like_header_row(["Account No.", "Branch", "IFSC Code", "MICR Code", "CRN", "Balance", "Type"])
    assert not _looks_like_header_row(["Scheme Name: LIBERTY SAVINGS ACCOUNT", None, None, None, None, None])


def test_dedupe_columns_handles_none_and_duplicates():
    result = _dedupe_columns(["Date", None, None, "Date"])
    assert result == ["Date", "col_1", "col_2", "Date_1"]
    assert len(set(result)) == len(result)


def test_clean_cell_strips_cid_artifacts_and_collapses_whitespace():
    assert _clean_cell("Account(cid:9)No.\n  Branch") == "Account No. Branch"


def test_clean_page_text_preserves_line_breaks():
    raw = "DATE MODE PARTICULARS(cid:9)DEPOSITS\n01-08-2026  B/F  2,18,656.99"
    cleaned = _clean_page_text(raw)
    assert cleaned.count("\n") == 1
    assert "(cid:9)" not in cleaned
