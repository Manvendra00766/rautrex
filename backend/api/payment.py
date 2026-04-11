from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.base import get_db
from backend.models.config import settings
from backend.models.user import User
from backend.services.email import send_payment_confirmation_email

router = APIRouter(prefix="/payment", tags=["payment"])

PLAN_PRICING = {
    "pro_monthly": 79900,
    "pro_annual": 799900,
    "team_monthly": 249900,
}

PLAN_DURATION_DAYS = {
    "pro_monthly": 30,
    "pro_annual": 365,
    "team_monthly": 30,
}


class OrderRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro_monthly|pro_annual|team_monthly)$")


class PaymentVerifySchema(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str = Field(..., pattern="^(pro_monthly|pro_annual|team_monthly)$")


@router.post("/create-order")
async def create_order(body: OrderRequest, user: User = Depends(get_current_user)):
    amount = PLAN_PRICING[body.plan]
    if not settings.razorpay_key_id:
        raise HTTPException(status_code=500, detail="Razorpay key is not configured.")
    order_id = f"order_{user.id}_{body.plan}_{int(datetime.now(timezone.utc).timestamp())}"
    return {
        "order_id": order_id,
        "amount": amount,
        "key": settings.razorpay_key_id,
        "currency": "INR",
        "receipt": f"rautrex_{user.id}_{body.plan}",
    }


@router.post("/verify")
async def verify_payment(
    data: PaymentVerifySchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = f"{data.razorpay_order_id}|{data.razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, data.razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment signature.")

    days = PLAN_DURATION_DAYS[data.plan]
    tier = "team" if data.plan.startswith("team") else "pro"
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    user.tier = tier
    user.subscription_tier = tier
    user.subscription_status = "active"
    user.subscription_expires_at = expires_at
    db.add(user)
    await db.commit()
    await db.refresh(user)

    try:
        send_payment_confirmation_email(user.email, data.plan, expires_at.date().isoformat())
    except Exception:
        pass

    return {"status": "success", "tier": user.tier, "subscription_expires_at": user.subscription_expires_at}


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    if settings.razorpay_webhook_secret:
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    return {"status": "received"}
