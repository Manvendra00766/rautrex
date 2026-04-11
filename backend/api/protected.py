from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import get_db
from backend.models.user import User
from backend.models.token import ProtectedResponse
from backend.api.auth import get_current_user

router = APIRouter(tags=["Protected"])


@router.get("/protected", response_model=ProtectedResponse)
async def protected_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Sample protected route — requires a valid Bearer JWT token.

    FastAPI's Depends() handles extracting the Authorization header,
    decoding the token via get_current_user, and injecting the User object.
    If the token is invalid, a 401 is raised before this function runs.
    """
    return ProtectedResponse(
        message="Access granted — this endpoint requires authentication.",
        user_email=current_user.email,
        timestamp=datetime.now(timezone.utc),
    )
