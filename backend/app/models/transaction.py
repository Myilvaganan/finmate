from typing import Optional
from datetime import date, datetime
from sqlalchemy import String, ForeignKey, Date, Float, Integer, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_txn_account_date", "account_id", "transaction_date"),
        Index("ix_txn_account_merchant_date", "account_id", "merchant_id", "transaction_date"),
        Index("ix_txn_account_category_date", "account_id", "category_id", "transaction_date"),
        Index("ix_txn_fingerprint", "fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    statement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("statements.id"), nullable=True, index=True)

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str] = mapped_column(Text, default="")
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)  # signed: +credit, -debit
    transaction_type: Mapped[str] = mapped_column(String(30), default="expense", index=True)
    # income|expense|transfer|investment|cash_withdrawal|card_payment

    balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")

    merchant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("merchants.id"), nullable=True, index=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True, index=True)
    subcategory_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)

    payment_method: Mapped[str] = mapped_column(String(30), default="other")
    # upi|card|netbanking|cash|cheque|neft_rtgs|other

    source: Mapped[str] = mapped_column(String(30), default="import")  # import|manual|demo
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    categorization_source: Mapped[str] = mapped_column(String(20), default="rule")  # rule|ai|user|default

    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
