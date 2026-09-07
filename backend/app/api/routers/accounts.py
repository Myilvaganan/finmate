from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.account import Account
from app.models.job import UploadJob
from app.models.statement import Statement, StatementProcessingError
from app.models.transaction import Transaction
from app.models.user import User
from app.parsers.bank_detection import mask_account_number
from app.schemas.common import success
from app.services.audit import record_audit

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _serialize(a: Account) -> dict:
    return {
        "id": a.id, "bank_name": a.bank_name, "account_type": a.account_type,
        "masked_account_number": a.masked_account_number, "currency": a.currency,
        "opening_balance": a.opening_balance, "closing_balance": a.closing_balance, "is_demo": a.is_demo,
    }


@router.get("")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    return success([_serialize(a) for a in accounts])


class AccountCreate(BaseModel):
    bank_name: str
    account_type: str = "bank"
    account_number: str = ""
    currency: str = "INR"
    opening_balance: float = 0.0


@router.post("")
def create_account(payload: AccountCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = Account(
        user_id=user.id, bank_name=payload.bank_name, account_type=payload.account_type,
        masked_account_number=mask_account_number(payload.account_number) if payload.account_number else "XXXX",
        currency=payload.currency, opening_balance=payload.opening_balance, closing_balance=payload.opening_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    record_audit(db, user.id, "account_created", "account", account.id)
    return success(_serialize(account))


class AccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_type: Optional[str] = None


@router.patch("/{account_id}")
def update_account(account_id: str, payload: AccountUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _get_owned(db, account_id, user.id)
    if payload.bank_name is not None:
        account.bank_name = payload.bank_name
    if payload.account_type is not None:
        account.account_type = payload.account_type
    db.commit()
    return success(_serialize(account))


@router.delete("/{account_id}")
def delete_account(account_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = _get_owned(db, account_id, user.id)

    statement_ids = [s.id for s in db.query(Statement.id).filter(Statement.account_id == account.id).all()]
    txn_count = db.query(Transaction).filter(Transaction.account_id == account.id).count()

    if statement_ids:
        # Delete children of statements first (FK constraints on Postgres/RDS are enforced,
        # unlike the SQLite default used in early local testing).
        db.query(StatementProcessingError).filter(StatementProcessingError.statement_id.in_(statement_ids)).delete(synchronize_session=False)
        db.query(UploadJob).filter(UploadJob.statement_id.in_(statement_ids)).update({UploadJob.statement_id: None}, synchronize_session=False)
    db.query(Transaction).filter(Transaction.account_id == account.id).delete(synchronize_session=False)
    db.query(Statement).filter(Statement.account_id == account.id).delete(synchronize_session=False)
    db.delete(account)
    db.commit()
    record_audit(db, user.id, "account_deleted", "account", account_id, {"transactions_deleted": txn_count, "statements_deleted": len(statement_ids)})
    return success({"deleted": True, "transactions_deleted": txn_count})


def _get_owned(db: Session, account_id: str, user_id: str) -> Account:
    account = db.get(Account, account_id)
    if not account or account.user_id != user_id:
        raise AppError(ErrorCode.NOT_FOUND, "Account not found.", status_code=404)
    return account
