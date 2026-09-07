from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.database.session import get_db
from app.models.category import Category, Merchant
from app.models.category import MerchantRule
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import success
from app.services.audit import record_audit

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _serialize(t: Transaction, categories: dict, merchants: dict) -> dict:
    return {
        "id": t.id, "transaction_date": t.transaction_date.isoformat(),
        "description": t.original_description, "normalized_description": t.normalized_description,
        "merchant": merchants.get(t.merchant_id, ""), "category": categories.get(t.category_id, "Uncategorized"),
        "category_id": t.category_id, "transaction_type": t.transaction_type,
        "debit": t.debit, "credit": t.credit, "amount": t.amount, "balance": t.balance,
        "account_id": t.account_id, "payment_method": t.payment_method,
        "is_duplicate": t.is_duplicate, "is_excluded": t.is_excluded, "notes": t.notes,
    }


@router.get("")
def list_transactions(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    start_date: Optional[date] = None, end_date: Optional[date] = None,
    account_id: Optional[str] = None, category_id: Optional[str] = None,
    merchant: Optional[str] = None, search: Optional[str] = None,
    txn_type: Optional[str] = None, min_amount: Optional[float] = None, max_amount: Optional[float] = None,
    include_excluded: bool = False,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == user.id)
    if not include_excluded:
        q = q.filter(Transaction.is_excluded == False)  # noqa: E712
    if start_date:
        q = q.filter(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(Transaction.transaction_date <= end_date)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if txn_type:
        q = q.filter(Transaction.transaction_type == txn_type)
    if min_amount is not None:
        q = q.filter((Transaction.debit >= min_amount) | (Transaction.credit >= min_amount))
    if max_amount is not None:
        q = q.filter((Transaction.debit <= max_amount) & (Transaction.credit <= max_amount))
    if search:
        like = f"%{search}%"
        q = q.filter(Transaction.original_description.ilike(like))

    total = q.count()
    rows = (
        q.order_by(Transaction.transaction_date.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )

    categories = {c.id: c.name for c in db.query(Category).all()}
    merchants = {m.id: m.display_name for m in db.query(Merchant).all()}

    return success(
        [_serialize(t, categories, merchants) for t in rows],
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": (total + page_size - 1) // page_size},
    )


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = _get_owned(db, transaction_id, user.id)
    categories = {c.id: c.name for c in db.query(Category).all()}
    merchants = {m.id: m.display_name for m in db.query(Merchant).all()}
    return success(_serialize(txn, categories, merchants))


class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    notes: Optional[str] = None
    is_excluded: Optional[bool] = None
    merchant_display_name: Optional[str] = None


@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: str, payload: TransactionUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    txn = _get_owned(db, transaction_id, user.id)
    changes = {}

    if payload.category_id is not None and payload.category_id != txn.category_id:
        category = db.get(Category, payload.category_id)
        if not category:
            raise AppError(ErrorCode.VALIDATION_ERROR, "Category not found.")
        changes["category_id"] = {"from": txn.category_id, "to": payload.category_id}
        txn.category_id = payload.category_id
        txn.categorization_source = "user"

        # Learn from this correction for future transactions with the same merchant.
        if txn.merchant_id:
            merchant = db.get(Merchant, txn.merchant_id)
            if merchant:
                existing_rule = db.query(MerchantRule).filter(
                    MerchantRule.user_id == user.id, MerchantRule.merchant_pattern == merchant.normalized_name,
                ).first()
                if existing_rule:
                    existing_rule.category_id = payload.category_id
                else:
                    db.add(MerchantRule(
                        user_id=user.id, merchant_pattern=merchant.normalized_name,
                        category_id=payload.category_id, created_by="user",
                    ))

    if payload.notes is not None:
        txn.notes = payload.notes
        changes["notes"] = True
    if payload.is_excluded is not None:
        txn.is_excluded = payload.is_excluded
        changes["is_excluded"] = payload.is_excluded

    db.commit()
    record_audit(db, user.id, "transaction_edited", "transaction", transaction_id, changes)
    categories = {c.id: c.name for c in db.query(Category).all()}
    merchants = {m.id: m.display_name for m in db.query(Merchant).all()}
    return success(_serialize(txn, categories, merchants))


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = _get_owned(db, transaction_id, user.id)
    db.delete(txn)
    db.commit()
    record_audit(db, user.id, "transaction_deleted", "transaction", transaction_id)
    return success({"deleted": True})


class BulkActionRequest(BaseModel):
    transaction_ids: List[str]
    action: str  # exclude|include|delete|categorize
    category_id: Optional[str] = None


@router.post("/bulk")
def bulk_action(payload: BulkActionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.id.in_(payload.transaction_ids))
    rows = q.all()
    if len(rows) != len(set(payload.transaction_ids)):
        raise AppError(ErrorCode.FORBIDDEN, "One or more transactions could not be found for this user.", status_code=403)

    if payload.action == "exclude":
        for t in rows:
            t.is_excluded = True
    elif payload.action == "include":
        for t in rows:
            t.is_excluded = False
    elif payload.action == "delete":
        for t in rows:
            db.delete(t)
    elif payload.action == "categorize":
        if not payload.category_id:
            raise AppError(ErrorCode.VALIDATION_ERROR, "category_id is required for the categorize action.")
        for t in rows:
            t.category_id = payload.category_id
            t.categorization_source = "user"
    else:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"Unknown bulk action: {payload.action}")

    db.commit()
    record_audit(db, user.id, f"transaction_bulk_{payload.action}", "transaction", None, {"count": len(rows)})
    return success({"affected": len(rows)})


def _get_owned(db: Session, transaction_id: str, user_id: str) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.user_id != user_id:
        raise AppError(ErrorCode.NOT_FOUND, "Transaction not found.", status_code=404)
    return txn
