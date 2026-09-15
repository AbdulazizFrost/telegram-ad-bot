from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TaxiAdLimit(Base):
    __tablename__ = "taxi_ad_limits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    last_free_ad_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="taxi_limit")

    def __repr__(self) -> str:
        return f"<TaxiAdLimit user_id={self.user_id} last_ad={self.last_free_ad_at}>"
