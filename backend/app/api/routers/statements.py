import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.job import UploadJob
from app.models.statement import Statement, StatementProcessingError
from app.models.user import User
from app.schemas.common import success
from app.services.audit import record_audit
from app.services.statement_import import StatementImportService
from app.utils.files import safe_temp_path, validate_upload
from app.workers.job_runner import run_statement_ingestion

router = APIRouter(prefix="/api/statements", tags=["statements"])


@router.post("/upload")
async def upload_statement(
    background_tasks: BackgroundTasks, file: UploadFile = File(...),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    content = await file.read()
    file_format = validate_upload(file.filename, len(content), content[:4096])

    temp_path = safe_temp_path(file.filename)
    temp_path.write_bytes(content)

    job = UploadJob(user_id=user.id, status="QUEUED", progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)

    record_audit(db, user.id, "statement_uploaded", "statement", None, {"filename": file.filename})
    background_tasks.add_task(
        run_statement_ingestion, job.id, user.id, str(temp_path), file.filename, file_format
    )
    return success({"job_id": job.id, "status": job.status})


@router.get("")
def list_statements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    statements = db.query(Statement).filter(Statement.user_id == user.id).order_by(Statement.created_at.desc()).all()
    return success([_serialize(s) for s in statements])


@router.get("/{statement_id}")
def get_statement(statement_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    statement = _get_owned(db, statement_id, user.id)
    data = _serialize(statement)
    data["warnings"] = json.loads(statement.warnings_json or "[]")
    data["balance_mismatches"] = json.loads(statement.balance_mismatch_json) if statement.balance_mismatch_json else []
    if statement.staging_transactions_json:
        data["staged_transactions"] = json.loads(statement.staging_transactions_json)
    return success(data)


@router.post("/{statement_id}/confirm")
def confirm_statement(statement_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = StatementImportService(db)
    result = service.confirm(statement_id, user.id)
    record_audit(db, user.id, "statement_imported", "statement", statement_id, result)
    return success(result)


@router.post("/{statement_id}/cancel")
def cancel_statement(statement_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = StatementImportService(db)
    service.cancel(statement_id, user.id)
    record_audit(db, user.id, "statement_cancelled", "statement", statement_id)
    return success({"cancelled": True})


@router.delete("/{statement_id}")
def delete_statement(statement_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    statement = _get_owned(db, statement_id, user.id)
    from app.models.transaction import Transaction

    account_id = statement.account_id
    txn_count = db.query(Transaction).filter(Transaction.statement_id == statement.id).count()
    # Delete children of the statement first (FK constraints are enforced on Postgres/RDS).
    db.query(StatementProcessingError).filter(StatementProcessingError.statement_id == statement.id).delete()
    db.query(UploadJob).filter(UploadJob.statement_id == statement.id).update({UploadJob.statement_id: None})
    db.query(Transaction).filter(Transaction.statement_id == statement.id).delete()
    db.delete(statement)
    db.flush()
    if account_id:
        StatementImportService(db)._refresh_account_balance(account_id)
    db.commit()
    record_audit(db, user.id, "statement_deleted", "statement", statement_id, {"transactions_deleted": txn_count})
    return success({"deleted": True, "transactions_deleted": txn_count})


def _get_owned(db: Session, statement_id: str, user_id: str) -> Statement:
    statement = db.get(Statement, statement_id)
    if not statement or statement.user_id != user_id:
        raise AppError(ErrorCode.NOT_FOUND, "Statement not found.", status_code=404)
    return statement


def _serialize(s: Statement) -> dict:
    return {
        "id": s.id, "original_filename": s.original_filename, "file_format": s.file_format,
        "detected_bank": s.detected_bank, "account_id": s.account_id,
        "period_start": s.period_start.isoformat() if s.period_start else None,
        "period_end": s.period_end.isoformat() if s.period_end else None,
        "status": s.status, "transaction_count": s.transaction_count,
        "total_income": s.total_income, "total_expenses": s.total_expenses,
        "overlap_type": s.overlap_type, "duplicate_count": s.duplicate_count,
        "created_at": s.created_at.isoformat(),
    }
