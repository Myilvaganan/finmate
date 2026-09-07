from typing import List
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    plan: Mapped[str] = mapped_column(String(50), default="Free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
