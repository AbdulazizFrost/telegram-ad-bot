from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)  # 1_day, 7_days, 30_days
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending, confirmed, rejected
    receipt_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receipt_type: Mapped[str] = mapped_column(String(32), default="photo")  # photo, document
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} user_id={self.user_id} plan={self.plan} amount={self.amount} status={self.status}>"
