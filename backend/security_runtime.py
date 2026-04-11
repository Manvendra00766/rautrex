from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from starlette.responses import Response

ALLOWED_ORIGINS = [
    "https://app.rautrex.com",
]
JWKS_URL = "https://your-idp.example.com/.well-known/jwks.json"
JWT_ISSUER = "https://your-idp.example.com/"
JWT_AUDIENCE = "rautrex-api"

_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": []}


def apply_security_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response: Response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


async def _get_jwks() -> dict[str, Any]:
    now = time.time()
    if now - _jwks_cache["fetched_at"] < 300 and _jwks_cache["keys"]:
        return {"keys": _jwks_cache["keys"]}
    async with httpx.AsyncClient(timeout=3.0) as client:
        jwks = (await client.get(JWKS_URL)).json()
    _jwks_cache["fetched_at"] = now
    _jwks_cache["keys"] = jwks.get("keys", [])
    return {"keys": _jwks_cache["keys"]}


async def validate_jwt_rs256(token: str) -> dict[str, Any]:
    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        jwks = await _get_jwks()
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key.")
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"verify_at_hash": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")

