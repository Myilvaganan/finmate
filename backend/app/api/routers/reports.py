import json
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.analytics.recurring import detect_recurring
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.category import Merchant
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import success
from app.services.audit import record_audit

router = APIRouter(prefix="/api/reports", tags=["reports"])
settings = get_settings()


class ReportRequest(BaseModel):
    report_type: str  # monthly|annual|category|income|account|transaction_export
    start_date: date
    end_date: date
    account_id: Optional[str] = None
    export_format: str = "json"  # json|csv|xlsx


@router.post("/generate")
def generate_report(payload: ReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = AnalyticsEngine(db, user.id)
    overview = engine.overview(payload.account_id, payload.start_date, payload.end_date)
    categories = engine.category_breakdown(payload.account_id, payload.start_date, payload.end_date)
    merchants = engine.merchant_ranking(payload.account_id, payload.start_date, payload.end_date)

    txns = db.query(Transaction).filter(
        Transaction.user_id == user.id, Transaction.is_excluded == False,  # noqa: E712
        Transaction.transaction_date >= payload.start_date, Transaction.transaction_date <= payload.end_date,
    )
    if payload.account_id:
        txns = txns.filter(Transaction.account_id == payload.account_id)
    rows = txns.order_by(Transaction.transaction_date).all()
    merchant_names = {m.id: m.display_name for m in db.query(Merchant).all()}
    recurring = detect_recurring(rows, merchant_names)

    report_data = {
        "report_type": payload.report_type,
        "period": {"start": payload.start_date.isoformat(), "end": payload.end_date.isoformat()},
        "overview": overview.__dict__,
        "top_categories": categories[:10],
        "top_merchants": merchants[:10],
        "recurring_payments": [
            {"merchant": r.merchant_name, "amount": r.average_amount, "frequency": r.frequency} for r in recurring
        ],
        "large_transactions": [
            {"date": t.transaction_date.isoformat(), "description": t.normalized_description, "amount": t.debit}
            for t in sorted(rows, key=lambda t: t.debit, reverse=True)[:10] if t.debit > 0
        ],
    }

    report_id = str(uuid.uuid4())
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if payload.export_format == "json":
        (reports_dir / f"{report_id}.json").write_text(json.dumps(report_data, default=str))
    else:
        df = pd.DataFrame([
            {
                "Date": t.transaction_date.isoformat(), "Description": t.normalized_description,
                "Debit": t.debit, "Credit": t.credit, "Balance": t.balance,
                "Category": t.category_id, "Type": t.transaction_type,
            }
            for t in rows
        ])
        if payload.export_format == "csv":
            df.to_csv(reports_dir / f"{report_id}.csv", index=False)
        elif payload.export_format == "xlsx":
            df.to_excel(reports_dir / f"{report_id}.xlsx", index=False)
        else:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"Unsupported export format: {payload.export_format}")

    record_audit(db, user.id, "report_generated", "report", report_id, {"type": payload.report_type})
    return success({"report_id": report_id, "format": payload.export_format, "data": report_data if payload.export_format == "json" else None})


@router.get("/{report_id}")
def get_report(report_id: str, export_format: str = "json", user: User = Depends(get_current_user)):
    try:
        uuid.UUID(report_id)
    except ValueError:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid report id.")
    if export_format not in ("json", "csv", "xlsx"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid export format.")

    reports_dir = Path(settings.REPORTS_DIR)
    path = reports_dir / f"{report_id}.{export_format}"
    if not path.exists():
        raise AppError(ErrorCode.NOT_FOUND, "Report not found.", status_code=404)
    if export_format == "json":
        return success(json.loads(path.read_text()))
    return FileResponse(path, filename=path.name)
