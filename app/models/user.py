from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)  # user, taxi, admin
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    taxi_limit: Mapped[Optional["TaxiAdLimit"]] = relationship(
        "TaxiAdLimit", uselist=False, back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.telegram_id} username={self.username} role={self.role}>"
