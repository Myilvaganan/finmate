from typing import Optional
from datetime import date
from sqlalchemy import String, ForeignKey, Float, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class RecurringTransaction(Base, TimestampMixin):
    __tablename__ = "recurring_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("merchants.id"), nullable=True)

    merchant_name: Mapped[str] = mapped_column(String(150), nullable=False)
    average_amount: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")  # weekly|monthly|quarterly|yearly
    occurrences: Mapped[int] = mapped_column(Float, default=0)
    last_charged_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    annualized_cost: Mapped[float] = mapped_column(Float, default=0.0)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
