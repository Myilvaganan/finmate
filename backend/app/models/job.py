from typing import Optional
from sqlalchemy import String, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class UploadJob(Base, TimestampMixin):
    __tablename__ = "upload_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    statement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("statements.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    # QUEUED|UPLOADING|EXTRACTING|NORMALIZING|VALIDATING|CHECKING_DUPLICATES|
    # CATEGORIZING|SAVING|GENERATING_INSIGHTS|COMPLETED|FAILED|NEEDS_REVIEW
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
