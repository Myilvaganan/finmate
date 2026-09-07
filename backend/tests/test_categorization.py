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


def test_merchant_normalization_collapses_variants():
    assert normalize_merchant("SWIGGY*12345") == "Swiggy"
    assert normalize_merchant("SWIGGY INDIA") == "Swiggy"
    assert normalize_merchant("AMZN PAY") == "Amazon"


def test_credit_card_payment_classified_as_card_payment_not_expense():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="CREDIT CARD PAYMENT HDFC", debit_raw="5000")
    txn = normalize_row(row, "acc1", "INR")
    txn_type = classify_transaction_type(txn, [])
    assert txn_type == "card_payment"


def test_atm_withdrawal_classified_as_cash_withdrawal():
    row = RawTransactionRow(row_index=0, transaction_date_raw="10/01/2026", description_raw="ATM CASH WDL", debit_raw="2000")
    txn = normalize_row(row, "acc1", "INR")
    txn_type = classify_transaction_type(txn, [])
    assert txn_type == "cash_withdrawal"
