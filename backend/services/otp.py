from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("rautrex")

_OTP_TTL_MINUTES = 5
_otp_store: dict[str, dict] = {}


def _cleanup() -> None:
    now = datetime.now(timezone.utc)
    expired = [k for k, v in _otp_store.items() if v["expires_at"] <= now]
    for key in expired:
        _otp_store.pop(key, None)


def create_otp_challenge(mode: str, email: str, phone_number: str | None) -> tuple[str, str]:
    _cleanup()
    challenge_id = secrets.token_urlsafe(24)
    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    _otp_store[challenge_id] = {
        "mode": mode,
        "email": email,
        "phone_number": phone_number,
        "otp_code": otp_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES),
    }
    return challenge_id, otp_code


def verify_otp_challenge(
    challenge_id: str,
    otp_code: str,
    mode: str,
    email: str,
    phone_number: str | None,
) -> bool:
    _cleanup()
    challenge = _otp_store.get(challenge_id)
    if challenge is None:
        return False
    valid = (
        challenge["mode"] == mode
        and challenge["email"] == email
        and challenge["phone_number"] == phone_number
        and challenge["otp_code"] == otp_code
    )
    if valid:
        _otp_store.pop(challenge_id, None)
    return valid


def dispatch_otp(email: str, phone_number: str | None, otp_code: str) -> None:
    # Replace with SMTP/SMS providers in production.
    logger.info(f"OTP for {email}: {otp_code}")
    if phone_number:
        logger.info(f"OTP SMS for {phone_number}: {otp_code}")
