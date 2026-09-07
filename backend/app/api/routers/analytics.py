from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.analytics.insights import generate_smart_insights
from app.analytics.recurring import detect_recurring
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.category import Merchant
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _period(start: Optional[date], end: Optional[date]):
    if not end:
        end = date.today()
    if not start:
        start = end - timedelta(days=30)
    return start, end


@router.get("/overview")
def overview(
    start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    metrics = engine.overview(account_id, start, end)
    return success(metrics.__dict__, meta={"period_start": start.isoformat(), "period_end": end.isoformat()})


@router.get("/income")
def income(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({"total_income": engine.total_income(account_id, start, end), "monthly": engine.monthly_series(account_id, start, end)})


@router.get("/expenses")
def expenses(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({
        "total_expenses": engine.total_expenses(account_id, start, end),
        "by_category": engine.category_breakdown(account_id, start, end),
        "daily": engine.daily_spending(account_id, start, end),
        "essential_vs_discretionary": engine.essential_vs_discretionary(account_id, start, end),
    })


@router.get("/categories")
def categories(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.category_breakdown(account_id, start, end))


@router.get("/merchants")
def merchants(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
              limit: int = 10, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success(engine.merchant_ranking(account_id, start, end, limit))


@router.get("/cashflow")
def cashflow(start_date: Optional[date] = None, end_date: Optional[date] = None, account_id: Optional[str] = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = _period(start_date, end_date)
    engine = AnalyticsEngine(db, user.id)
    return success({
        "monthly": engine.monthly_series(account_id, start, end),
        "payment_methods": engine.payment_method_breakdown(account_id, start, end),
        "accounts": engine.account_balances(),
    })


@router.get("/recurring")
def recurring(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.is_excluded == False).all()  # noqa: E712
    merchant_names = {m.id: m.display_name for m in db.query(Merchant).all()}
    candidates = detect_recurring(txns, merchant_names)
    return success([
        {
            "merchant": c.merchant_name, "average_amount": c.average_amount, "frequency": c.frequency,
            "occurrences": c.occurrences, "last_charged_date": c.last_charged_date.isoformat(),
            "next_expected_date": c.next_expected_date.isoformat(), "annualized_cost": c.annualized_cost,
            "is_subscription": c.is_subscription,
        }
        for c in candidates
    ])


@router.get("/insights")
def insights(account_id: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = AnalyticsEngine(db, user.id)
    generated = generate_smart_insights(engine, account_id, date.today())
    return success([i.__dict__ for i in generated])
