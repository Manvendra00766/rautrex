from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from backend.models.base import Base


class Portfolio(Base):
    """User portfolio holdings and performance tracking.
    
    Each user can have one portfolio with multiple assets.
    Assets stored as JSON: [{ticker: str, weight: float}, ...]
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    assets = Column(JSON, nullable=False, default=list)  # [{ticker: "AAPL", weight: 0.5}, ...]
    total_value = Column(Float, nullable=True)  # Total portfolio value in USD
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])
