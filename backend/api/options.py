"""
FastAPI REST routes for option pricing, Greeks, and implied volatility.

Endpoints:
    POST /options/price    — Black-Scholes fair value
    POST /options/greeks   — All 5 Greeks
    POST /options/iv       — Implied volatility from market price
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from quant.options.black_scholes import (
    black_scholes_price,
    greeks as compute_greeks,
    implied_volatility,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

OptionType = Literal["call", "put"]


class OptionPriceRequest(BaseModel):
    S: float = Field(gt=0, description="Spot price of the underlying")
    K: float = Field(gt=0, description="Strike price")
    T: float = Field(gt=0, description="Time to expiry in years")
    r: float = Field(description="Risk-free rate (decimal, e.g. 0.05)")
    sigma: float = Field(gt=0, description="Volatility (decimal, e.g. 0.20)")
    option_type: OptionType = "call"


class GreeksRequest(OptionPriceRequest):
    pass


class ImpliedVolRequest(BaseModel):
    market_price: float = Field(gt=0, description="Observed market price")
    S: float = Field(gt=0, description="Spot price of the underlying")
    K: float = Field(gt=0, description="Strike price")
    T: float = Field(gt=0, description="Time to expiry in years")
    r: float = Field(description="Risk-free rate (decimal)")
    option_type: OptionType = "call"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/price")
async def price(req: OptionPriceRequest):
    """Return the Black-Scholes theoretical option price."""
    price = black_scholes_price(
        S=req.S,
        K=req.K,
        T=req.T,
        r=req.r,
        sigma=req.sigma,
        option_type=req.option_type,
    )
    return {"price": round(price, 6)}


@router.post("/greeks")
async def get_greeks(req: GreeksRequest):
    """Return all 5 Greeks: delta, gamma, vega, theta, rho."""
    result = compute_greeks(
        S=req.S,
        K=req.K,
        T=req.T,
        r=req.r,
        sigma=req.sigma,
        option_type=req.option_type,
    )
    return {k: round(v, 6) for k, v in result.items()}


@router.post("/iv")
async def implied_vol(req: ImpliedVolRequest):
    """Compute implied volatility via Newton-Raphson."""
    try:
        iv = implied_volatility(
            market_price=req.market_price,
            S=req.S,
            K=req.K,
            T=req.T,
            r=req.r,
            option_type=req.option_type,
        )
        return {"implied_volatility": round(iv, 6)}
    except ValueError as e:
        return {"error": str(e)}
