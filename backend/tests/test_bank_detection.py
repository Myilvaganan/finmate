from app.parsers.bank_detection import detect_bank_from_text


def test_ifsc_prefix_identifies_bank_reliably():
    text = "Account No. Branch IFSC Code\n92501XXXXX69630 BEGUR KT UTIB0003960 560211113"
    assert detect_bank_from_text(text) == "Axis Bank"


def test_counterparty_bank_mention_in_transaction_does_not_cause_false_positive():
    # A UPI transaction referencing another bank as the payee's bank must not make the whole
    # statement misattributed -- this happens constantly since every UPI ref names a bank.
    header = "S.MYILVAGANAN Registered Mobile No: XXXXXX2153\nIFSC Code UTIB0003960\n" + ("x" * 2000)
    body = "UPI/P2M/110291640732/Trading V/ICICI Ban/Pay via//P2V/ 497.96 1,28,000.00"
    text = header + body
    assert detect_bank_from_text(text) == "Axis Bank"


def test_bank_name_in_header_window_is_detected():
    text = "Statement of Account\nHDFC Bank Limited\nAccount details follow..."
    assert detect_bank_from_text(text) == "HDFC Bank"


def test_unknown_bank_returns_other():
    text = "Some random statement with no recognizable bank signature at all."
    assert detect_bank_from_text(text) == "Other"
