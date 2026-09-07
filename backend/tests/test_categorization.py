from app.services.categorization import rule_based_category
from app.services.merchant_normalization import normalize_merchant
from app.services.transfer_detection import classify_transaction_type
from app.parsers.base import RawTransactionRow
from app.services.normalization import normalize_row


def test_swiggy_categorized_as_food_delivery():
    category, confidence, source = rule_based_category("SWIGGY ORDER 8213", "Swiggy", is_credit=False)
    assert category == "Food Delivery"
    assert source == "rule"


def test_netflix_categorized_as_subscription():
    category, _, _ = rule_based_category("NETFLIX.COM", "Netflix", is_credit=False)
    assert category == "Subscriptions"


def test_salary_credit_categorized_as_income():
    category, _, _ = rule_based_category("SALARY CREDIT ACME CORP", "Acme Corp", is_credit=True)
    assert category == "Salary"


def test_unknown_credit_defaults_to_other_income():
    category, confidence, source = rule_based_category("RANDOM UNKNOWN CREDIT XYZ", "Xyz", is_credit=True)
    assert category == "Other Income"
    assert source == "default"


def test_unknown_debit_returns_none_for_ai_fallback():
    category, confidence, source = rule_based_category("SOME UNKNOWN VENDOR 999", "Some Vendor", is_credit=False)
    assert category is None
    assert source == "none"


def test_learned_rule_takes_priority():
    learned = {"SPECIAL MERCHANT": "Travel"}
    category, confidence, source = rule_based_category("SPECIAL MERCHANT PURCHASE", "Special Merchant", is_credit=False, learned_rules=learned)
    assert category == "Travel"
    assert source == "user"


def test_merchant_normalization_strips_reference_hashes():
    from app.services.merchant_normalization import normalize_merchant
    assert "aplap" not in normalize_merchant("BAN/621337244960/APLAPd838b9a8d7e874c81d279dc83a4").lower()


def test_looks_like_garbage_merchant_catches_reference_codes():
    from app.services.merchant_normalization import looks_like_garbage_merchant
    assert looks_like_garbage_merchant("I Aplap Af5c804c877de932d2c7e05 Jayakumar")
    assert looks_like_garbage_merchant("Bank Aplapc438ebe1bf Cc89860e 8e2")
    assert looks_like_garbage_merchant("")
    assert not looks_like_garbage_merchant("Swiggy")
    assert not looks_like_garbage_merchant("Jayakumar")


def test_merchant_normalization_collapses_variants():
    assert normalize_merchant("SWIGGY*12345") == "Swiggy"
    assert normalize_merchant("SWIGGY INDIA") == "Swiggy"
    assert normalize_merchant("AMZN PAY") == "Amazon"


def test_credit_card_payment_classified_as_card_payment_not_expense():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="CREDIT CARD PAYMENT HDFC", debit_raw="5000")
    txn = normalize_row(row, "acc1", "INR")
    txn_type = classify_transaction_type(txn, [])
    assert txn_type == "card_payment"


def test_opening_and_closing_balance_marker_rows_are_excluded():
    from app.parsers.tabular import dataframe_to_rows
    import pandas as pd

    df = pd.DataFrame([
        {"Date": "Opening Balance", "Description": "", "Debit": "", "Credit": "", "Balance": "2,34,309.44"},
        {"Date": "01-07-2026", "Description": "UPI/P2M/Swiggy", "Debit": "500.00", "Credit": "", "Balance": "2,33,809.44"},
        {"Date": "Closing Balance", "Description": "", "Debit": "", "Credit": "", "Balance": "34,030.12"},
    ])
    rows = dataframe_to_rows(df)
    assert len(rows) == 1
    assert rows[0].transaction_date_raw == "01-07-2026"


def test_atm_withdrawal_classified_as_cash_withdrawal():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="ATM CASH WDL", debit_raw="2000")
    txn = normalize_row(row, "acc1", "INR")
    txn_type = classify_transaction_type(txn, [])
    assert txn_type == "cash_withdrawal"


def test_p2a_self_transfer_credit_not_classified_as_income():
    row = RawTransactionRow(
        row_index=0, transaction_date_raw="10/01/2026",
        description_raw="UPI/P2A/608416176462/S MYILVAG/ICIC/Paid via/", credit_raw="20000",
    )
    txn = normalize_row(row, "acc1", "INR")
    assert classify_transaction_type(txn, [], account_holder_name="Myilvaganan S") == "transfer"


def test_third_party_credit_with_own_name_as_recipient_stays_income():
    # "<sender> to <own name>" formats name both parties -- a same-name match here must not be
    # treated as a self-transfer signal, since it just means the payment gateway/sender named the
    # recipient (a very common format for genuine incoming payments, not a self-transfer).
    row = RawTransactionRow(
        row_index=0, transaction_date_raw="10/01/2026",
        description_raw="Fund transfer MMT/IMPS/002507912592/E8XTzLUkOc5E6I/Razor pay S to S MYILVAGA",
        credit_raw="5000",
    )
    txn = normalize_row(row, "acc1", "INR")
    assert classify_transaction_type(txn, [], account_holder_name="Myilvaganan S") == "income"


def test_third_party_debit_with_own_name_as_sender_label_stays_expense():
    # Own name/VPA shown as the payer label is standard on nearly every self-initiated UPI debit
    # regardless of who the recipient is -- must not be treated as a self-transfer signal.
    row = RawTransactionRow(
        row_index=0, transaction_date_raw="10/01/2026",
        description_raw="Smyilvagan UPI/Smyilvagan/92501004326963/Maintenanc/AXIS BANK/891842002735/AXIOV",
        debit_raw="2000",
    )
    txn = normalize_row(row, "acc1", "INR")
    assert classify_transaction_type(txn, [], account_holder_name="Myilvaganan S") == "expense"


def test_third_party_income_via_neft_unaffected_by_self_transfer_check():
    row = RawTransactionRow(
        row_index=0, transaction_date_raw="10/01/2026",
        description_raw="NEFT/HDFCH00862477569/NSE CLEARING LIMITED MFSS SE/HDFC BANK/0001NEFT 4606808967",
        credit_raw="15000",
    )
    txn = normalize_row(row, "acc1", "INR")
    assert classify_transaction_type(txn, [], account_holder_name="Myilvaganan S") == "income"
