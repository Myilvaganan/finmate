from typing import Optional
from sqlalchemy import String, Float, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (Index("ix_accounts_user_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="bank")  # bank | credit_card | cash | other
    masked_account_number: Mapped[str] = mapped_column(String(50), default="")
    account_number_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0)
    closing_balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="accounts")
