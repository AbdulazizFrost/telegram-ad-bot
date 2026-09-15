from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)  # 1_day, 7_days, 30_days
    price: Mapped[int] = mapped_column(Integer, default=0)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} plan={self.plan} active={self.active}>"
