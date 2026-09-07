"""Get-or-create helpers for reference data (categories, merchants, accounts)."""
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category, Merchant, MerchantRule
from app.services.category_rules import DEFAULT_CATEGORIES


def ensure_default_categories(db: Session) -> Dict[str, Category]:
    existing = {c.name: c for c in db.query(Category).filter(Category.is_system == True).all()}  # noqa: E712
    for name, parent_type, group, essential in DEFAULT_CATEGORIES:
        if name not in existing:
            cat = Category(name=name, parent_type=parent_type, group_name=group, is_essential=essential, is_system=True)
            db.add(cat)
            existing[name] = cat
    db.flush()
    return existing


def get_or_create_merchant(db: Session, normalized_name: str, display_name: str) -> Merchant:
    merchant = db.query(Merchant).filter(Merchant.normalized_name == normalized_name.upper()).first()
    if merchant:
        return merchant
    merchant = Merchant(normalized_name=normalized_name.upper(), display_name=display_name)
    db.add(merchant)
    db.flush()
    return merchant


def get_or_create_account(
    db: Session, user_id: str, bank_name: str, account_type: str, masked_number: str, currency: str, is_demo: bool = False
) -> Account:
    def _find() -> Optional[Account]:
        return db.query(Account).filter(
            Account.user_id == user_id, Account.bank_name == bank_name,
            Account.masked_account_number == masked_number,
        ).first()

    account = _find()
    if account:
        return account

    # Two statements for the same real account can be ingested by concurrent background jobs
    # (each in its own DB session), so the check above and this insert aren't atomic together --
    # without the unique constraint + retry, that race creates one duplicate Account per upload.
    account = Account(
        user_id=user_id, bank_name=bank_name, account_type=account_type,
        masked_account_number=masked_number, currency=currency, is_demo=is_demo,
    )
    try:
        # A SAVEPOINT (not a full rollback) so a conflict only undoes this insert, leaving
        # whatever else this session already flushed earlier in the same import untouched.
        with db.begin_nested():
            db.add(account)
            db.flush()
    except IntegrityError:
        account = _find()
        if not account:
            raise
    return account


def load_learned_rules(db: Session, user_id: str) -> Dict[str, str]:
    rules = db.query(MerchantRule).filter(MerchantRule.user_id == user_id).all()
    result = {}
    for r in rules:
        category = db.get(Category, r.category_id)
        if category:
            result[r.merchant_pattern] = category.name
    return result
