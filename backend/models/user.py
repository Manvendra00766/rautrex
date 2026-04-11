from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship
from backend.models.base import Base


class User(Base):
    """Core user table for JWT authentication.

    Design choices:
    - id: integer PK (simple, works fine for single-tenant or small-scale)
    - email UNIQUE: used as the login identifier instead of username
    - hashed_password: bcrypt-hashed, never store plaintext
    - created_at/updated_at: audit timestamps, auto-managed via server_default
      and onupdate so application code doesn't need to set them
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(32), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False, default="Dr. Elena Rostova")
    role = Column(String(64), nullable=False, default="Senior Quant")
    subscription_tier = Column(String(64), nullable=False, default="Institutional Pro")
    renewal_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    backtest_hours_used = Column(Integer, nullable=False, default=45)
    backtest_hours_limit = Column(Integer, nullable=False, default=100)
    tier = Column(String(32), nullable=False, default="free")
    is_verified = Column(Boolean, nullable=False, default=False)
    trial_started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    trial_expires_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=60))
    trial_expired = Column(Boolean, nullable=False, default=False)
    razorpay_customer_id = Column(String(128), nullable=True)
    subscription_status = Column(String(32), nullable=False, default="inactive")
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True, unique=True, index=True)
    persona = Column(String(32), nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    default_currency = Column(String(8), nullable=False, default="USD")
    risk_free_rate = Column(Float, nullable=False, default=0.0525)
    var_confidence = Column(Float, nullable=False, default=0.95)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(32), nullable=False, index=True)
    key_hash = Column(String(128), nullable=False, unique=True)
    masked_key = Column(String(64), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")
