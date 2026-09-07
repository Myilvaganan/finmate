"""Structured tool functions the chat pipeline invokes to fetch real numbers from SQLite.
The LLM never computes financial figures itself -- it only explains what these return."""
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.models.transaction import Transaction
from app.models.category import Category, Merchant


class FinancialTools:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.engine = AnalyticsEngine(db, user_id)

    def get_total_income(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"total_income": self.engine.total_income(start=start, end=end)}

    def get_total_expenses(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"total_expenses": self.engine.total_expenses(start=start, end=end)}

    def get_cash_flow(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"net_cash_flow": self.engine.net_cash_flow(start=start, end=end)}

    def get_savings_rate(self, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        return {"savings_rate_pct": self.engine.savings_rate(start=start, end=end)}

    def get_category_spending(self, category_name: str, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        q = (
            self.db.query(func.sum(Transaction.debit), func.count(Transaction.id))
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
                Transaction.transaction_type == "expense", func.lower(Category.name) == category_name.lower(),
            )
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        total, count = q.one()
        return {"category": category_name, "total": round(total or 0, 2), "transaction_count": count}

    def get_merchant_spending(self, merchant_name: str, start: Optional[date] = None, end: Optional[date] = None) -> Dict:
        q = (
            self.db.query(func.sum(Transaction.debit), func.count(Transaction.id))
            .join(Merchant, Transaction.merchant_id == Merchant.id)
            .filter(
                Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
                func.lower(Merchant.normalized_name) == merchant_name.lower(),
            )
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        total, count = q.one()
        return {"merchant": merchant_name, "total": round(total or 0, 2), "transaction_count": count}

    def get_large_transactions(self, min_amount: float, start: Optional[date] = None, end: Optional[date] = None, limit: int = 20) -> Dict:
        q = self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id, Transaction.is_excluded == False,  # noqa: E712
            Transaction.debit >= min_amount,
        )
        if start:
            q = q.filter(Transaction.transaction_date >= start)
        if end:
            q = q.filter(Transaction.transaction_date <= end)
        rows = q.order_by(Transaction.debit.desc()).limit(limit).all()
        return {
            "transactions": [
                {"date": t.transaction_date.isoformat(), "description": t.normalized_description, "amount": t.debit}
                for t in rows
            ]
        }

    def get_recurring_transactions(self) -> Dict:
        from app.models.recurring import RecurringTransaction
        rows = self.db.query(RecurringTransaction).filter(
            RecurringTransaction.user_id == self.user_id, RecurringTransaction.is_dismissed == False,  # noqa: E712
        ).all()
        return {
            "recurring": [
                {"merchant": r.merchant_name, "amount": r.average_amount, "frequency": r.frequency}
                for r in rows
            ]
        }

    def compare_periods(self, period_a: tuple, period_b: tuple) -> Dict:
        return self.engine.compare_periods(None, period_a, period_b)

    def get_account_balance(self) -> Dict:
        return {"accounts": self.engine.account_balances()}
