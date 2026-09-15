from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    violation_type: Mapped[str] = mapped_column(String(64), default="OTHER_AD_VIOLATION", index=True)
    user_role: Mapped[str] = mapped_column(String(32), default="user")
    subscription_status: Mapped[str] = mapped_column(String(32), default="none")
    was_taxi: Mapped[bool] = mapped_column(Boolean, default=False)
    detector_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Multimodal & Detection metadata (nullable for backwards compatibility)
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="text")
    extracted_ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_locations: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_phones: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_links: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Legacy columns present in existing databases
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=0)
    action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="delete")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=utc_now)

    def __init__(self, **kwargs):
        if "telegram_message_id" in kwargs and "message_id" not in kwargs:
            kwargs["message_id"] = kwargs["telegram_message_id"]
        elif "message_id" in kwargs and "telegram_message_id" not in kwargs:
            kwargs["telegram_message_id"] = kwargs["message_id"]

        if "deleted_at" in kwargs and "created_at" not in kwargs:
            kwargs["created_at"] = kwargs["deleted_at"]
        elif "created_at" in kwargs and "deleted_at" not in kwargs:
            kwargs["deleted_at"] = kwargs["created_at"]

        if "violation_type" in kwargs and "action" not in kwargs:
            kwargs["action"] = kwargs["violation_type"]
        elif "action" in kwargs and "violation_type" not in kwargs:
            kwargs["violation_type"] = kwargs["action"]

        super().__init__(**kwargs)


    @property
    def text_snippet(self) -> str:
        return (self.message_text or "")[:400]

    def __repr__(self) -> str:
        return f"<ModerationLog id={self.id} user={self.user_id} type={self.violation_type} reason={self.reason}>"
