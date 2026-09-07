from typing import Optional
from datetime import date
from sqlalchemy import String, ForeignKey, Date, Integer, Float, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Statement(Base, TimestampMixin):
    __tablename__ = "statements"
    __table_args__ = (
        Index("ix_statements_account_period", "account_id", "period_start", "period_end"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=True)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf|csv|xlsx|txt|html|image
    detected_bank: Mapped[str] = mapped_column(String(100), default="Other")
    parser_used: Mapped[str] = mapped_column(String(100), default="")

    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(30), default="PROCESSING", index=True)
    # PROCESSED|PROCESSING|DUPLICATE|OVERLAP_DETECTED|FAILED|NEEDS_REVIEW

    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_income: Mapped[float] = mapped_column(Float, default=0.0)
    total_expenses: Mapped[float] = mapped_column(Float, default=0.0)

    overlap_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # exact_duplicate|partial_overlap|full_containment|none
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    balance_mismatch_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    staging_transactions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_demo: Mapped[bool] = mapped_column(String(5), default="false")


class StatementProcessingError(Base, TimestampMixin):
    __tablename__ = "statement_processing_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    statement_id: Mapped[str] = mapped_column(String(36), ForeignKey("statements.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    error_code: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
