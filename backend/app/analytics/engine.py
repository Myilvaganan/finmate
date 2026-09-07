"""Deterministic financial analytics engine. All dashboard/report numbers originate here via
SQL aggregation -- never from an LLM. See app/ai/tools.py for the AI-facing wrappers."""
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.category import Category, Merchant

INCLUDED_EXPENSE_TYPES = ("expense",)
INCLUDED_INCOME_TYPES = ("income",)
EXCLUDED_FROM_CASHFLOW = ("transfer", "card_payment")


def _base_query(db: Session, user_id: str, account_id: Optional[str], start: Optional[date], end: Optional[date]):
    q = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_excluded == False,  # noqa: E712
        Transaction.is_duplicate == False,  # noqa: E712
    )
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if start:
        q = q.filter(Transaction.transaction_date >= start)
    if end:
        q = q.filter(Transaction.transaction_date <= end)
    return q


@dataclass
class OverviewMetrics:
    total_income: float
    total_expenses: float
    net_cash_flow: float
    savings_rate: float
    transaction_count: int
    average_daily_expenses: float
    median_transaction: float
    largest_transaction: float
    smallest_transaction: float


class AnalyticsEngine:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def _sum(self, account_id, start, end, transaction_types, amount_field) -> float:
        q = _base_query(self.db, self.user_id, account_id, start, end).filter(
            Transaction.transaction_type.in_(transaction_types)
        )
        total = q.with_entities(func.sum(amount_field)).scalar()
        return round(total or 0.0, 2)

    def total_income(self, account_id=None, start=None, end=None) -> float:
        return self._sum(account_id, start, end, INCLUDED_INCOME_TYPES, Transaction.credit)

    def total_expenses(self, account_id=None, start=None, end=None) -> float:
        return self._sum(account_id, start, end, INCLUDED_EXPENSE_TYPES, Transaction.debit)

    def net_cash_flow(self, account_id=None, start=None, end=None) -> float:
        return round(self.total_income(account_id, start, end) - self.total_expenses(account_id, start, end), 2)

    def savings_rate(self, account_id=None, start=None, end=None) -> float:
        income = self.total_income(account_id, start, end)
        if income <= 0:
            return 0.0
        return round((income - self.total_expenses(account_id, start, end)) / income * 100, 2)

    def transaction_count(self, account_id=None, start=None, end=None) -> int:
        return _base_query(self.db, self.user_id, account_id, start, end).count()

    def overview(self, account_id=None, start=None, end=None) -> OverviewMetrics:
        expenses_q = _base_query(self.db, self.user_id, account_id, start, end).filter(
            Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES)
        )
        amounts = [t.debit for t in expenses_q.all()]
        days = max(1, ((end or date.today()) - start).days) if start else 1

        all_txns = _base_query(self.db, self.user_id, account_id, start, end).all()
        signed_amounts = [t.amount for t in all_txns if t.transaction_type not in EXCLUDED_FROM_CASHFLOW]

        return OverviewMetrics(
            total_income=self.total_income(account_id, start, end),
            total_expenses=self.total_expenses(account_id, start, end),
            net_cash_flow=self.net_cash_flow(account_id, start, end),
            savings_rate=self.savings_rate(account_id, start, end),
            transaction_count=self.transaction_count(account_id, start, end),
            average_daily_expenses=round(sum(amounts) / days, 2) if amounts else 0.0,
            median_transaction=round(median(signed_amounts), 2) if signed_amounts else 0.0,
            largest_transaction=round(max(signed_amounts), 2) if signed_amounts else 0.0,
            smallest_transaction=round(min(signed_amounts), 2) if signed_amounts else 0.0,
        )

    def category_breakdown(self, account_id=None, start=None, end=None) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Category, Transaction.category_id == Category.id, isouter=True)
            .with_entities(
                Category.id, Category.name, func.sum(Transaction.debit).label("total"), func.count(Transaction.id)
            )
            .group_by(Category.id)
            .order_by(func.sum(Transaction.debit).desc())
        )
        return [
            {"category_id": cid, "category": name or "Uncategorized", "total": round(total or 0, 2), "count": count}
            for cid, name, total, count in q.all()
        ]

    def merchant_ranking(self, account_id=None, start=None, end=None, limit: int = 10) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Merchant, Transaction.merchant_id == Merchant.id, isouter=True)
            .with_entities(
                Merchant.id, Merchant.display_name, func.sum(Transaction.debit).label("total"),
                func.count(Transaction.id),
            )
            .group_by(Merchant.id)
            .order_by(func.sum(Transaction.debit).desc())
            .limit(limit)
        )
        return [
            {"merchant_id": mid, "merchant": name or "Unknown", "total": round(total or 0, 2), "count": count}
            for mid, name, total, count in q.all()
        ]

    def daily_spending(self, account_id=None, start=None, end=None) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.transaction_date, func.sum(Transaction.debit))
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date)
        )
        return [{"date": d.isoformat(), "total": round(t or 0, 2)} for d, t in q.all()]

    def monthly_series(self, account_id=None, start=None, end=None) -> List[Dict]:
        rows = _base_query(self.db, self.user_id, account_id, start, end).all()
        buckets: Dict[str, Dict[str, float]] = {}
        for t in rows:
            key = t.transaction_date.strftime("%Y-%m")
            b = buckets.setdefault(key, {"income": 0.0, "expenses": 0.0})
            if t.transaction_type == "income":
                b["income"] += t.credit
            elif t.transaction_type == "expense":
                b["expenses"] += t.debit
        return [
            {"month": k, "income": round(v["income"], 2), "expenses": round(v["expenses"], 2)}
            for k, v in sorted(buckets.items())
        ]

    def essential_vs_discretionary(self, account_id=None, start=None, end=None) -> Dict[str, float]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .join(Category, Transaction.category_id == Category.id, isouter=True)
            .with_entities(Category.is_essential, func.sum(Transaction.debit))
            .group_by(Category.is_essential)
        )
        result = {"essential": 0.0, "discretionary": 0.0}
        for is_essential, total in q.all():
            key = "essential" if is_essential else "discretionary"
            result[key] += round(total or 0, 2)
        return result

    def payment_method_breakdown(self, account_id=None, start=None, end=None) -> List[Dict]:
        q = (
            _base_query(self.db, self.user_id, account_id, start, end)
            .filter(Transaction.transaction_type.in_(INCLUDED_EXPENSE_TYPES))
            .with_entities(Transaction.payment_method, func.sum(Transaction.debit))
            .group_by(Transaction.payment_method)
        )
        return [{"method": m, "total": round(t or 0, 2)} for m, t in q.all()]

    def account_balances(self) -> List[Dict]:
        from app.models.account import Account
        accounts = self.db.query(Account).filter(Account.user_id == self.user_id).all()
        return [
            {"account_id": a.id, "bank_name": a.bank_name, "balance": a.closing_balance, "currency": a.currency}
            for a in accounts
        ]

    def compare_periods(self, account_id, period_a: Tuple[date, date], period_b: Tuple[date, date]) -> Dict:
        a = self.overview(account_id, period_a[0], period_a[1])
        b = self.overview(account_id, period_b[0], period_b[1])
        pct = lambda new, old: round((new - old) / old * 100, 2) if old else 0.0  # noqa: E731
        return {
            "period_a": {"income": a.total_income, "expenses": a.total_expenses},
            "period_b": {"income": b.total_income, "expenses": b.total_expenses},
            "income_change_pct": pct(a.total_income, b.total_income),
            "expense_change_pct": pct(a.total_expenses, b.total_expenses),
        }
