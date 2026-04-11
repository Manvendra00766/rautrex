from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.auth import get_current_user
from backend.models.base import get_db
from backend.models.user import APIKey, User, UserPreferences
from backend.schemas.user import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyRead,
    PreferencesUpdate,
    UserPreferencesRead,
    UserRead,
)

router = APIRouter(prefix="/users", tags=["profile"])


async def _load_user(db: AsyncSession, user_id: int) -> User:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.preferences), selectinload(User.api_keys))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def _ensure_preferences(user: User) -> UserPreferences:
    if user.preferences is None:
        user.preferences = UserPreferences(
            default_currency="USD",
            risk_free_rate=0.0525,
            var_confidence=0.95,
        )
    return user.preferences


@router.get("/me", response_model=UserRead)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await _load_user(db, current_user.id)
    prefs = _ensure_preferences(user)
    if prefs.id is None:
        db.add(prefs)
        await db.commit()
        await db.refresh(user)
    active_keys = [k for k in user.api_keys if not k.revoked]
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        subscription_tier=user.subscription_tier,
        tier=user.tier,
        persona=user.persona,
        onboarding_completed=user.onboarding_completed,
        trial_started_at=user.trial_started_at,
        trial_expires_at=user.trial_expires_at,
        trial_expired=user.trial_expired,
        renewal_date=user.renewal_date,
        backtest_hours_used=user.backtest_hours_used,
        backtest_hours_limit=user.backtest_hours_limit,
        preferences=UserPreferencesRead.model_validate(user.preferences),
        api_keys=[APIKeyRead.model_validate(k) for k in active_keys],
    )


class OnboardingUpdate(BaseModel):
    persona: str = Field(..., pattern="^(Trader|Student|Analyst|Developer)$")
    onboarding_completed: bool = False


@router.patch("/me/onboarding", response_model=UserRead)
async def patch_onboarding(
    body: OnboardingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await _load_user(db, current_user.id)
    user.persona = body.persona
    user.onboarding_completed = body.onboarding_completed
    db.add(user)
    await db.commit()
    await db.refresh(user)
    prefs = _ensure_preferences(user)
    active_keys = [k for k in user.api_keys if not k.revoked]
    return UserRead(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        subscription_tier=user.subscription_tier,
        tier=user.tier,
        persona=user.persona,
        onboarding_completed=user.onboarding_completed,
        trial_started_at=user.trial_started_at,
        trial_expires_at=user.trial_expires_at,
        trial_expired=user.trial_expired,
        renewal_date=user.renewal_date,
        backtest_hours_used=user.backtest_hours_used,
        backtest_hours_limit=user.backtest_hours_limit,
        preferences=UserPreferencesRead.model_validate(prefs),
        api_keys=[APIKeyRead.model_validate(k) for k in active_keys],
    )


@router.get("/me/trial-status")
async def trial_status(current_user: User = Depends(get_current_user)):
    if current_user.tier != "trial":
        return {"on_trial": False, "tier": current_user.tier}
    now = datetime.now(timezone.utc)
    days_left = (current_user.trial_expires_at - now).days
    is_expired = now > current_user.trial_expires_at
    return {
        "on_trial": True,
        "is_expired": is_expired,
        "days_left": max(0, days_left),
        "trial_started_at": current_user.trial_started_at,
        "trial_expires_at": current_user.trial_expires_at,
        "warning_level": "urgent" if days_left <= 3 else "warning" if days_left <= 10 else "normal",
    }


@router.patch("/me/preferences", response_model=UserPreferencesRead)
async def patch_preferences(
    body: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await _load_user(db, current_user.id)
    prefs = _ensure_preferences(user)
    prefs.default_currency = body.default_currency
    prefs.risk_free_rate = body.risk_free_rate
    prefs.var_confidence = body.var_confidence
    db.add(prefs)
    await db.commit()
    await db.refresh(prefs)
    return UserPreferencesRead.model_validate(prefs)


@router.post("/me/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await _load_user(db, current_user.id)
    raw_suffix = secrets.token_hex(16)
    raw_key = f"rtx_live_{raw_suffix}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    masked_key = f"rtx_live_••••••••{raw_suffix[-4:]}"
    api_key = APIKey(
        user_id=user.id,
        name=body.name,
        key_prefix=raw_key[:16],
        key_hash=key_hash,
        masked_key=masked_key,
        last_used_at=datetime.now(timezone.utc),
        revoked=False,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        masked_key=api_key.masked_key,
        created_at=api_key.created_at,
    )
