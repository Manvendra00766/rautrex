import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.base import get_db
from backend.models.user import User
from backend.models.token import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    SignupChallengeRequest,
    LoginChallengeRequest,
    SignupVerifyRequest,
    LoginVerifyRequest,
    OtpChallengeResponse,
    RegisterRequest,
    MessageResponse,
)
from backend.models.config import settings
from backend.services.auth import (
    hash_password,
    authenticate_user,
    create_access_token,
    create_refresh_token,
)
from backend.services.otp import create_otp_challenge, verify_otp_challenge, dispatch_otp
from backend.services.email import send_verification_email, send_welcome_trial_email

security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT tokens.

    We check for duplicate email before insertion to enforce uniqueness.
    In production, you'd also send a welcome email and require email verification.
    """
    # Check for existing user to avoid IntegrityError on duplicate fields
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    phone_result = await db.execute(select(User).where(User.phone_number == body.phone_number))
    if phone_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists.",
        )

    user = User(
        email=body.email,
        phone_number=body.phone_number,
        is_verified=True,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Issue both access and refresh tokens
    token_data = {"sub": user.email, "user_id": user.id}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/register", response_model=MessageResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    token = secrets.token_urlsafe(32)
    user = User(
        full_name=body.full_name,
        email=body.email,
        phone_number=f"pending_{secrets.token_hex(8)}",
        hashed_password=hash_password(body.password),
        tier="trial",
        subscription_tier="pro",
        is_verified=False,
        trial_started_at=datetime.now(timezone.utc),
        trial_expires_at=datetime.now(timezone.utc) + timedelta(days=60),
        trial_expired=False,
        subscription_status="inactive",
        email_verification_token=token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    try:
        send_verification_email(user.email, token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {exc}",
        )

    return MessageResponse(message="Registration successful. Please verify your email.")


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email_verification_token == token))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token.")
    user.is_verified = True
    user.email_verification_token = None
    db.add(user)
    await db.commit()
    try:
        send_welcome_trial_email(user.email, user.trial_expires_at.date().isoformat())
    except Exception:
        pass
    return MessageResponse(message="Email verified successfully.")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and return JWT tokens.

    Returns 401 on invalid credentials — we don't distinguish between
    'email not found' and 'wrong password' to avoid email enumeration attacks.
    """
    user = await authenticate_user(body.email, body.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified.",
        )

    token_data = {"sub": user.email, "user_id": user.id}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/signup/challenge", response_model=OtpChallengeResponse)
async def signup_challenge(body: SignupChallengeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists.")
    phone_result = await db.execute(select(User).where(User.phone_number == body.phone_number))
    if phone_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this phone number already exists.")

    challenge_id, otp_code = create_otp_challenge("signup", body.email, body.phone_number)
    dispatch_otp(body.email, body.phone_number, otp_code)
    return OtpChallengeResponse(challenge_id=challenge_id, message="OTP sent to email and phone.")


@router.post("/signup/verify", response_model=TokenResponse)
async def signup_verify(body: SignupVerifyRequest, db: AsyncSession = Depends(get_db)):
    if not verify_otp_challenge(
        challenge_id=body.challenge_id,
        otp_code=body.otp_code,
        mode="signup",
        email=body.email,
        phone_number=body.phone_number,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP.")
    return await signup(SignupRequest(email=body.email, phone_number=body.phone_number, password=body.password), db)


@router.post("/login/challenge", response_model=OtpChallengeResponse)
async def login_challenge(body: LoginChallengeRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(body.email, body.password, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified.")
    challenge_id, otp_code = create_otp_challenge("login", body.email, user.phone_number)
    dispatch_otp(body.email, user.phone_number, otp_code)
    return OtpChallengeResponse(challenge_id=challenge_id, message="OTP sent to email and phone.")


@router.post("/login/verify", response_model=TokenResponse)
async def login_verify(body: LoginVerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not verify_otp_challenge(
        challenge_id=body.challenge_id,
        otp_code=body.otp_code,
        mode="login",
        email=body.email,
        phone_number=user.phone_number,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP.")
    return await login(LoginRequest(email=body.email, password=body.password), db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode a JWT bearer token and return the associated User ORM object.

    This function is designed to be consumed as a FastAPI Depends() in
    protected route handlers. It validates the token, checks the user still
    exists in the database (e.g., catches deleted/deactivated accounts),
    and returns the user row for downstream use.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified.",
        )
    return user
