"""Unit tests for the analytics engine's SQL-backed aggregations, run against a throwaway
in-memory SQLite DB (not the app's TestClient) so we can seed exact Transaction rows directly."""
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analytics.date_ranges import compare, previous_equivalent_period, previous_year_period
from app.analytics.engine import AnalyticsEngine
from app.database.session import Base
from app.models.account import Account
from app.models.category import Category, Merchant
from app.models.transaction import Transaction
from app.models.user import User


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_user_account(db):
    user = User(email="a@test.com", hashed_password="x")
    db.add(user)
    db.flush()
    account = Account(user_id=user.id, bank_name="Test Bank", masked_account_number="XXXX 1")
    db.add(account)
    db.flush()
    return user, account


def _txn(user, account, d, debit=0.0, credit=0.0, category_id=None, merchant_id=None, txn_type=None, balance=None):
    return Transaction(
        user_id=user.id, account_id=account.id, transaction_date=d,
        original_description="test", normalized_description="test",
        debit=debit, credit=credit, amount=(credit - debit),
        transaction_type=txn_type or ("income" if credit else "expense"),
        category_id=category_id, merchant_id=merchant_id, balance=balance,
        fingerprint=uuid.uuid4().hex,
    )


def test_total_income_and_expenses(db):
    user, account = _seed_user_account(db)
    db.add_all([
        _txn(user, account, date(2026, 1, 5), credit=50000),
        _txn(user, account, date(2026, 1, 10), debit=200),
        _txn(user, account, date(2026, 1, 15), debit=300),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    assert engine.total_income(None, date(2026, 1, 1), date(2026, 1, 31)) == 50000
    assert engine.total_expenses(None, date(2026, 1, 1), date(2026, 1, 31)) == 500
    assert engine.net_cash_flow(None, date(2026, 1, 1), date(2026, 1, 31)) == 49500


def test_savings_rate_handles_zero_income(db):
    user, account = _seed_user_account(db)
    db.add(_txn(user, account, date(2026, 1, 10), debit=200))
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    assert engine.savings_rate(None, date(2026, 1, 1), date(2026, 1, 31)) == 0.0


def test_monthly_series_zero_fills_months_with_no_transactions(db):
    user, account = _seed_user_account(db)
    db.add_all([
        _txn(user, account, date(2026, 1, 5), credit=1000),
        _txn(user, account, date(2026, 3, 5), debit=200),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    series = engine.monthly_series(None, date(2026, 1, 1), date(2026, 3, 31))
    assert [row["month"] for row in series] == ["2026-01", "2026-02", "2026-03"]
    assert series[1] == {"month": "2026-02", "income": 0.0, "expenses": 0.0}


def test_daily_spending_zero_fills_days(db):
    user, account = _seed_user_account(db)
    db.add(_txn(user, account, date(2026, 1, 1), debit=100))
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    series = engine.daily_spending(None, date(2026, 1, 1), date(2026, 1, 3))
    assert len(series) == 3
    assert series[1]["total"] == 0.0


def test_cashflow_series_cumulative(db):
    user, account = _seed_user_account(db)
    db.add_all([
        _txn(user, account, date(2026, 1, 5), credit=1000, debit=0),
        _txn(user, account, date(2026, 1, 6), debit=200),
        _txn(user, account, date(2026, 2, 5), credit=500),
        _txn(user, account, date(2026, 2, 6), debit=800),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    series = engine.cashflow_series(None, date(2026, 1, 1), date(2026, 2, 28))
    assert series[0]["net_cash_flow"] == 800
    assert series[0]["cumulative_cash_flow"] == 800
    assert series[1]["net_cash_flow"] == -300
    assert series[1]["cumulative_cash_flow"] == 500


def test_category_breakdown_percentage_and_comparison(db):
    user, account = _seed_user_account(db)
    food = Category(name="Food", parent_type="expense")
    db.add(food)
    db.flush()
    db.add_all([
        _txn(user, account, date(2025, 12, 10), debit=1000, category_id=food.id),
        _txn(user, account, date(2026, 1, 10), debit=1500, category_id=food.id),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    result = engine.category_breakdown(None, date(2026, 1, 1), date(2026, 1, 31), compare_previous=True)
    assert result[0]["total"] == 1500
    assert result[0]["percentage"] == 100.0
    assert result[0]["previous_period_amount"] == 1000
    assert result[0]["change_percent"] == 50.0


def test_merchant_ranking_new_merchant_has_no_infinite_change(db):
    user, account = _seed_user_account(db)
    m = Merchant(normalized_name="AMAZON", display_name="Amazon")
    db.add(m)
    db.flush()
    db.add(_txn(user, account, date(2026, 1, 10), debit=500, merchant_id=m.id))
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    result = engine.merchant_ranking(None, date(2026, 1, 1), date(2026, 1, 31), compare_previous=True)
    assert result[0]["previous_period_amount"] == 0.0
    assert result[0]["change_percent"] is None  # not a misleading "infinite %"


def test_fixed_vs_variable_classifies_recurring_merchant_as_fixed(db):
    user, account = _seed_user_account(db)
    netflix = Merchant(normalized_name="NETFLIX", display_name="Netflix")
    grocer = Merchant(normalized_name="LOCAL SHOP", display_name="Local Shop")
    db.add_all([netflix, grocer])
    db.flush()
    db.add_all([
        _txn(user, account, date(2025, 11, 1), debit=649, merchant_id=netflix.id),
        _txn(user, account, date(2025, 12, 1), debit=649, merchant_id=netflix.id),
        _txn(user, account, date(2026, 1, 1), debit=649, merchant_id=netflix.id),
        _txn(user, account, date(2026, 1, 15), debit=300, merchant_id=grocer.id),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    result = engine.fixed_vs_variable(None, date(2026, 1, 1), date(2026, 1, 31))
    assert result["fixed"] == 649
    assert result["variable"] == 300


def test_account_balance_trend_tracks_own_account_only(db):
    user, account = _seed_user_account(db)
    other = Account(user_id=user.id, bank_name="Other Bank", masked_account_number="XXXX 2")
    db.add(other)
    db.flush()
    db.add_all([
        _txn(user, account, date(2026, 1, 1), debit=100, balance=900),
        _txn(user, other, date(2026, 1, 1), credit=5000, balance=5000),
    ])
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    trend = engine.account_balance_trend(account.id, date(2026, 1, 1), date(2026, 1, 31))
    assert len(trend) == 1
    assert trend[0]["account_id"] == account.id
    assert trend[0]["points"][0]["balance"] == 900


def test_spending_heatmap_full_year_zero_filled(db):
    user, account = _seed_user_account(db)
    db.add(_txn(user, account, date(2026, 6, 15), debit=500))
    db.commit()
    engine = AnalyticsEngine(db, user.id)
    heatmap = engine.spending_heatmap(2026)
    assert len(heatmap) == 365
    june15 = next(h for h in heatmap if h["date"] == "2026-06-15")
    assert june15["amount"] == 500
    assert june15["transaction_count"] == 1
    jan1 = next(h for h in heatmap if h["date"] == "2026-01-01")
    assert jan1["amount"] == 0.0


def test_previous_equivalent_period():
    prev_start, prev_end = previous_equivalent_period(date(2026, 8, 1), date(2026, 8, 31))
    assert prev_start == date(2026, 7, 1)
    assert prev_end == date(2026, 7, 31)


def test_previous_year_period_handles_leap_day():
    prev_start, prev_end = previous_year_period(date(2024, 2, 29), date(2024, 2, 29))
    assert prev_start == date(2023, 2, 28)


def test_compare_zero_previous_returns_none_percent():
    result = compare(500, 0)
    assert result.change_percent is None
    assert result.trend == "up"
