from typing import Optional
from sqlalchemy import String, Float, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_type: Mapped[str] = mapped_column(String(30), default="expense")  # income|expense|transfer|investment
    group_name: Mapped[str] = mapped_column(String(100), default="Other")
    is_essential: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class Merchant(Base, TimestampMixin):
    __tablename__ = "merchants"
    __table_args__ = (Index("ix_merchants_normalized_name", "normalized_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    default_category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)


class MerchantRule(Base, TimestampMixin):
    """Learned mapping from user corrections: pattern -> category."""
    __tablename__ = "merchant_rules"
    __table_args__ = (Index("ix_merchant_rules_user_pattern", "user_id", "merchant_pattern"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    merchant_pattern: Mapped[str] = mapped_column(String(150), nullable=False)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"), nullable=False)
    subcategory_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_by: Mapped[str] = mapped_column(String(20), default="user")  # user|system|ai
