from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------- Pydantic schemas for auth requests/responses ----------
# These schemas handle request validation AND response serialization
# (response_model on FastAPI routes), eliminating duplicate validation code.


class SignupRequest(BaseModel):
    """Request body for /auth/signup."""
    email: str = Field(..., description="User email address")
    phone_number: str = Field(..., min_length=7, max_length=32, description="User phone number")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")

    @field_validator("email")
    @classmethod
    def validate_gmail(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.endswith("@gmail.com"):
            raise ValueError("Only @gmail.com addresses are allowed.")
        return normalized


class LoginRequest(BaseModel):
    """Request body for /auth/login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")

    @field_validator("email")
    @classmethod
    def validate_gmail(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.endswith("@gmail.com"):
            raise ValueError("Only @gmail.com addresses are allowed.")
        return normalized


class SignupChallengeRequest(SignupRequest):
    pass


class LoginChallengeRequest(LoginRequest):
    pass


class SignupVerifyRequest(SignupRequest):
    challenge_id: str = Field(..., min_length=10)
    otp_code: str = Field(..., min_length=6, max_length=6)


class LoginVerifyRequest(LoginRequest):
    challenge_id: str = Field(..., min_length=10)
    otp_code: str = Field(..., min_length=6, max_length=6)


class OtpChallengeResponse(BaseModel):
    challenge_id: str
    message: str


class TokenResponse(BaseModel):
    """Response body returned by signup and login endpoints."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class ProtectedResponse(BaseModel):
    """Example response for the protected endpoint."""
    message: str
    user_email: str
    timestamp: datetime


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class MessageResponse(BaseModel):
    message: str
