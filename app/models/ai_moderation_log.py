from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIModerationLog(Base):
    __tablename__ = "ai_moderation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="normal")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    was_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    def __repr__(self) -> str:
        return (
            f"<AIModerationLog id={self.id} chat={self.chat_id} msg={self.message_id} "
            f"class={self.classification} conf={self.confidence:.2f} deleted={self.was_deleted}>"
        )
