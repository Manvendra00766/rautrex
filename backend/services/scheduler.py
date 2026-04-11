from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


async def trial_email_scheduler(db: AsyncSession) -> None:
    result = await db.execute(
        select(User).where(
            User.tier == "trial",
            User.is_verified == True,
            User.trial_expired == False,
        )
    )
    users = result.scalars().all()
    now = datetime.now(timezone.utc)
    for user in users:
        days_left = (user.trial_expires_at - now).days
        if days_left < 0:
            user.trial_expired = True
            db.add(user)
    await db.commit()
