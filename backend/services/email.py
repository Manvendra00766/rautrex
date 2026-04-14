from __future__ import annotations

import json
import urllib.request

from backend.models.config import settings


def send_verification_email(to_email: str, token: str) -> None:
    if not settings.resend_api_key:
        return

    verify_link = f"{settings.frontend_url.rstrip('/')}/verify-email?token={token}"
    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": "Verify your Rautrex account",
        "html": (
            "<p>Welcome to Rautrex.</p>"
            f"<p>Please verify your email by clicking <a href=\"{verify_link}\">this link</a>.</p>"
        ),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        if response.status >= 400:
            raise RuntimeError("Failed to send verification email.")


def send_payment_confirmation_email(to_email: str, plan: str, expires_at: str) -> None:
    if not settings.resend_api_key:
        return
    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": "Your Rautrex subscription is active",
        "html": (
            f"<p>Your {plan} plan is now active.</p>"
            f"<p>Next renewal date: {expires_at}</p>"
            "<p>You're all set to use premium features.</p>"
        ),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        if response.status >= 400:
            raise RuntimeError("Failed to send payment confirmation email.")


def send_welcome_trial_email(to_email: str, trial_expires_at: str) -> None:
    if not settings.resend_api_key:
        return
    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": "Your 60-day Rautrex Pro trial has started",
        "html": (
            "<p>Your trial is active with full Pro access.</p>"
            "<ul>"
            "<li>Backtesting</li>"
            "<li>Options pricing + Greeks</li>"
            "<li>ML signals</li>"
            "<li>Risk analytics</li>"
            "</ul>"
            f"<p>Trial expiry date: {trial_expires_at}</p>"
        ),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        if response.status >= 400:
            raise RuntimeError("Failed to send welcome trial email.")
