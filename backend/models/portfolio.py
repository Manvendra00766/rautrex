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
    Assets stored as JSON: [{ticker: str, amount_invested: float}, ...]
    Weights are calculated dynamically from amounts.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    assets = Column(JSON, nullable=False, default=list)  # [{ticker: "AAPL", amount_invested: 20000.0}, ...]
    total_invested = Column(Float, nullable=True)  # Total amount invested (sum of all amounts)
    total_value = Column(Float, nullable=True)  # Current portfolio value (including market movements)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])
