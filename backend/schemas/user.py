from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserPreferencesRead(BaseModel):
    default_currency: str
    risk_free_rate: float
    var_confidence: float

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    default_currency: str = Field(..., pattern="^(USD|EUR)$")
    risk_free_rate: float = Field(..., ge=0.0, le=0.25)
    var_confidence: float = Field(..., ge=0.90, le=0.999)


class APIKeyRead(BaseModel):
    id: int
    name: str
    masked_key: str
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    key: str
    masked_key: str
    created_at: datetime


class UserRead(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    subscription_tier: str
    tier: str
    persona: str | None = None
    onboarding_completed: bool
    trial_started_at: datetime | None = None
    trial_expires_at: datetime | None = None
    trial_expired: bool = False
    renewal_date: datetime
    backtest_hours_used: int
    backtest_hours_limit: int
    preferences: UserPreferencesRead
    api_keys: list[APIKeyRead]

    class Config:
        from_attributes = True
