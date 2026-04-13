from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.base import get_db
from backend.models.config import settings
from backend.models.user import User

TIER_LIMITS = {
    "free": {"backtests_per_day": 3, "tickers": 1, "simulations_per_day": 2},
    "pro": {"backtests_per_day": 999, "tickers": 10, "simulations_per_day": 999},
    "team": {"backtests_per_day": 999, "tickers": 999, "simulations_per_day": 999},
}

_usage: dict[str, int] = {}
_bearer_optional = HTTPBearer(auto_error=False)


def require_pro(user: User = Depends(get_current_user)) -> User:
    effective = get_effective_tier(user)
    if effective not in ["pro", "team"]:
        trial_expires = user.trial_expires_at
        if trial_expires.tzinfo is None:
            trial_expires = trial_expires.replace(tzinfo=timezone.utc)
        is_expired_trial = user.tier == "trial" and datetime.now(timezone.utc) > trial_expires
        raise HTTPException(
            status_code=403,
            detail={
                "error": "trial_expired" if is_expired_trial else "upgrade_required",
                "message": "Your 2-month free trial has ended. Upgrade to continue." if is_expired_trial else "This feature requires Pro. Upgrade to unlock.",
                "upgrade_url": "/pricing",
            },
        )
    return user


def require_team(user: User = Depends(get_current_user)) -> User:
    if get_effective_tier(user) != "team":
        raise HTTPException(status_code=403, detail={"error": "upgrade_required"})
    return user


def get_effective_tier(user: User) -> str:
    if user.tier == "trial":
        trial_expires = user.trial_expires_at
        if trial_expires.tzinfo is None:
            trial_expires = trial_expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < trial_expires:
            return "pro"
        return "free"
    return user.tier


def check_daily_limit(feature: str):
    key_map = {
        "backtests": "backtests_per_day",
        "simulations": "simulations_per_day",
    }
    if feature not in key_map:
        raise ValueError(f"Unsupported feature: {feature}")

    limit_key = key_map[feature]

    async def _dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_optional),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user = None
        if credentials is not None:
            try:
                payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
                email: str | None = payload.get("sub")
                if email:
                    result = await db.execute(select(User).where(User.email == email))
                    user = result.scalar_one_or_none()
            except JWTError:
                user = None

        if user is None:
            user = User(id=0, email="guest@rautrex.local", phone_number="guest", hashed_password="", tier="free")

        tier = get_effective_tier(user)
        tier = tier if tier in TIER_LIMITS else "free"
        limit = TIER_LIMITS[tier][limit_key]
        user_key = str(user.id)
        usage_key = f"{user_key}:{feature}:{date.today().isoformat()}"
        count = _usage.get(usage_key, 0) + 1
        if count > limit:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "daily_limit_reached",
                    "message": f"You have used {limit}/{limit} {feature} for your {tier} tier.",
                    "upgrade_url": "/pricing",
                },
            )
        _usage[usage_key] = count
        return user

    return _dependency
