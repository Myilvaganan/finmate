from typing import Optional
from sqlalchemy import String, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class FinancialInsight(Base, TimestampMixin):
    __tablename__ = "financial_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_metric: Mapped[str] = mapped_column(String(255), default="")
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info|warning|positive|critical
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_period: Mapped[str] = mapped_column(String(100), default="")
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
