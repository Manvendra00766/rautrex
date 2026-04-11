from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.user import User
from backend.models.config import settings


# CryptContext centralizes password hashing config in one place.
# Using bcrypt (schemes=["bcrypt"]) — it's battle-tested and FastAPI ecosystem standard.
# deprecated="auto" handles migration if we switch algorithms later.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Includes a random salt internally."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    We embed the data dict (typically {"sub": user_email}) and add
    exp/iat claims. Using HS256 (HMAC-SHA256) — symmetric signing is
    simpler for single-service deployments. For microservices, we'd
    switch to RS256 asymmetric keys.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with a longer expiration (days, not minutes)."""
    return create_access_token(
        data, expires_delta=timedelta(days=settings.refresh_token_expire_days)
    )


async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[User]:
    """Look up a user by email and verify their password.

    Returns the User object on success, None on failure (email not found OR wrong password).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
