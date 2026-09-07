"""Demo data seeding: python -m app.seed [--reset]

Creates a demo user with 6 months of realistic transactions across ICICI Bank, Axis Bank,
and a credit card account. All seeded data is flagged is_demo=True / source="demo" so it can
be cleared independently of real imported data (see DELETE /api/settings/demo-data, TODO).
"""
import argparse
import random
from datetime import date, timedelta

from app.core.security import hash_password
from app.database.session import Base, SessionLocal, engine
from app.models.account import Account
from app.models.category import Category, Merchant
from app.models.transaction import Transaction
from app.models.user import User
from app.services.lookup import ensure_default_categories, get_or_create_merchant
from app.services.merchant_normalization import normalize_merchant
from app.utils.fingerprint import transaction_fingerprint

DEMO_EMAIL = "demo@finmate.app"
DEMO_PASSWORD = "demopassword123"

MERCHANTS_EXPENSE = [
    ("SWIGGY ORDER 8213", "Food Delivery", 250, 650),
    ("ZOMATO ORDER 5521", "Food Delivery", 200, 600),
    ("AMAZON.IN PURCHASE", "Online Shopping", 500, 4500),
    ("FLIPKART ORDER", "Online Shopping", 400, 3500),
    ("BIGBASKET GROCERY", "Groceries", 800, 2800),
    ("NETFLIX.COM", "Subscriptions", 649, 649),
    ("SPOTIFY PREMIUM", "Subscriptions", 119, 119),
    ("HPCL PETROL PUMP", "Fuel", 1000, 3000),
    ("UBER TRIP", "Transportation", 120, 450),
    ("AIRTEL POSTPAID BILL", "Utilities", 499, 999),
    ("ELECTRICITY BOARD BILL", "Utilities", 1200, 3200),
    ("APOLLO PHARMACY", "Healthcare", 200, 1500),
    ("LIC PREMIUM PAYMENT", "Insurance", 5000, 5000),
    ("HOME LOAN EMI", "EMI / Loans", 22000, 22000),
]

TRANSFER_DESCRIPTIONS = ["UPI-JOHN DOE-TRANSFER", "UPI-RENT PAYMENT-TRANSFER", "NEFT-SAVINGS TRANSFER"]
INVESTMENT_DESCRIPTIONS = [("ZERODHA SIP MUTUAL FUND", "Investments", 5000, 15000)]
ATM_DESCRIPTIONS = ["ATM CASH WDL", "CASH WITHDRAWAL ATM"]


def _account_number(seed: str) -> str:
    return f"XXXX XXXX {seed}"


def seed(reset: bool = False):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        categories = ensure_default_categories(db)
        db.commit()

        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), full_name="Demo User", plan="Demo")
            db.add(user)
            db.commit()
            db.refresh(user)

        accounts = {
            "icici": db.query(Account).filter(Account.user_id == user.id, Account.bank_name == "ICICI Bank").first()
            or Account(user_id=user.id, bank_name="ICICI Bank", account_type="bank",
                       masked_account_number=_account_number("9630"), currency="INR",
                       opening_balance=125000, closing_balance=125000, is_demo=True),
            "axis": db.query(Account).filter(Account.user_id == user.id, Account.bank_name == "Axis Bank").first()
            or Account(user_id=user.id, bank_name="Axis Bank", account_type="bank",
                       masked_account_number=_account_number("4471"), currency="INR",
                       opening_balance=45000, closing_balance=45000, is_demo=True),
            "cc": db.query(Account).filter(Account.user_id == user.id, Account.account_type == "credit_card").first()
            or Account(user_id=user.id, bank_name="HDFC Bank", account_type="credit_card",
                       masked_account_number=_account_number("2210"), currency="INR",
                       opening_balance=0, closing_balance=0, is_demo=True),
        }
        for acc in accounts.values():
            if acc.id is None:
                db.add(acc)
        db.commit()
        for acc in accounts.values():
            db.refresh(acc)

        existing_demo_txns = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.source == "demo").count()
        if existing_demo_txns > 0 and not reset:
            print(f"Demo data already present ({existing_demo_txns} transactions). Use --reset to regenerate.")
            return

        random.seed(42)
        today = date.today()
        start = today - timedelta(days=182)
        balance = accounts["icici"].opening_balance

        day = start
        salary_day_done = set()
        while day <= today:
            month_key = (day.year, day.month)
            if day.day == 1 and month_key not in salary_day_done:
                balance += 95000
                _add_txn(db, user, accounts["icici"], day, "SALARY CREDIT ACME CORP", 0, 95000, balance, "Salary", "income", categories)
                salary_day_done.add(month_key)

            if random.random() < 0.55:
                desc, cat_name, lo, hi = random.choice(MERCHANTS_EXPENSE)
                amount = round(random.uniform(lo, hi), 2)
                balance -= amount
                _add_txn(db, user, accounts["icici"], day, desc, amount, 0, balance, cat_name, "expense", categories)

            if random.random() < 0.05:
                desc, cat_name, lo, hi = INVESTMENT_DESCRIPTIONS[0]
                amount = round(random.uniform(lo, hi), 2)
                balance -= amount
                _add_txn(db, user, accounts["icici"], day, desc, amount, 0, balance, cat_name, "investment", categories)

            if random.random() < 0.03:
                amount = round(random.uniform(2000, 10000), 2)
                balance -= amount
                _add_txn(db, user, accounts["icici"], day, random.choice(ATM_DESCRIPTIONS), amount, 0, balance, "Cash Withdrawal", "cash_withdrawal", categories)

            if day.day == 5:
                amount = round(random.uniform(3000, 8000), 2)
                balance -= amount
                _add_txn(db, user, accounts["icici"], day, "CREDIT CARD PAYMENT HDFC", amount, 0, balance, "Card Payment", "card_payment", categories)

            day += timedelta(days=1)

        accounts["icici"].closing_balance = balance
        db.commit()
        print(f"Seeded demo user {DEMO_EMAIL} / password: {DEMO_PASSWORD}")
        print(f"Created {db.query(Transaction).filter(Transaction.user_id == user.id).count()} demo transactions.")
    finally:
        db.close()


def _add_txn(db, user, account, day, description, debit, credit, balance, category_name, txn_type, categories):
    merchant_name = normalize_merchant(description)
    merchant = get_or_create_merchant(db, merchant_name, merchant_name)
    category = categories.get(category_name) or categories.get("Other")
    fingerprint = transaction_fingerprint(account.id, day, description, debit, credit, "")
    db.add(Transaction(
        user_id=user.id, account_id=account.id, transaction_date=day,
        original_description=description, normalized_description=description,
        debit=debit, credit=credit, amount=credit - debit, balance=round(balance, 2),
        transaction_type=txn_type, merchant_id=merchant.id, category_id=category.id if category else None,
        payment_method="upi", source="demo", fingerprint=fingerprint,
        categorization_source="rule", confidence_score=0.9,
        is_internal_transfer=txn_type == "transfer",
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding.")
    args = parser.parse_args()
    seed(reset=args.reset)
