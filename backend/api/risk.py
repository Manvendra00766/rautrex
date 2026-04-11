"""
FastAPI routes for the Rautrex risk management engine.

Endpoints wrap quant/risk/risk_models.py functions and handle data fetching,
validation, and serialization.
"""

from __future__ import annotations

import yfinance as yf
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from quant.risk.risk_models import (
    historical_var,
    parametric_var,
    conditional_var,
    monte_carlo_var,
    portfolio_var,
    drawdown_analysis,
)

router = APIRouter(prefix="/risk", tags=["risk"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class VaRRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. 'AAPL'")
    start: str | None = Field(default=None, description="Start date YYYY-MM-DD (default: 2y lookback)")
    end: str | None = Field(default=None, description="End date YYYY-MM-DD (default: today)")
    method: str = Field(default="historical", description="VaR method: 'historical', 'parametric', or 'cvar'")
    confidence: float = Field(default=0.95, ge=0.5, le=0.999, description="Confidence level")
    holding_period: int = Field(default=1, ge=1, le=30, description="Holding period in trading days")


class VaRResponse(BaseModel):
    ticker: str
    method: str
    confidence: float
    holding_period: int
    var: float
    observation_count: int
    note: str


class MCVarRequest(BaseModel):
    S0: float = Field(..., gt=0, description="Current asset price")
    mu: float = Field(..., description="Expected annual return (drift)")
    sigma: float = Field(..., gt=0, description="Annual volatility")
    T: float = Field(default=1, gt=0, le=2, description="Time horizon in years")
    n_sims: int = Field(default=10_000, ge=100, le=1_000_000, description="Number of simulations")
    confidence: float = Field(default=0.95, ge=0.5, le=0.999, description="Confidence level")


class MCVarResponse(BaseModel):
    var: float
    percentile_price: float
    mean_price: float
    method: str = "monte_carlo"
    plot_json: dict


class PortfolioVarRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=50, description="Ticker symbols")
    weights: list[float] = Field(..., min_length=2, description="Portfolio weights (should sum to 1)")
    start: str | None = Field(default=None, description="Start date YYYY-MM-DD")
    end: str | None = Field(default=None, description="End date YYYY-MM-DD")
    confidence: float = Field(default=0.95, ge=0.5, le=0.999, description="Confidence level")


class PortfolioVarResponse(BaseModel):
    tickers: list[str]
    weights: list[float]
    var: float
    confidence: float
    observation_count: int
    note: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_returns(ticker: str, start: str | None = None, end: str | None = None) -> pd.Series:
    """Fetch daily close prices and compute returns."""
    kwargs: dict = {}
    if start:
        kwargs["start"] = start
    if end:
        kwargs["end"] = start and end or end
    # Use period-based or date-based fetch
    if not start and not end:
        data = yf.Ticker(ticker).history(period="2y")
    else:
        data = yf.Ticker(ticker).history(start=start, end=end)

    if data.empty or "Close" not in data.columns:
        raise HTTPException(status_code=404, detail=f"No price data found for ticker '{ticker}'")

    return data["Close"].pct_change().dropna()


def _fetch_prices(ticker: str, start: str | None = None, end: str | None = None) -> pd.Series:
    """Fetch daily close prices."""
    if not start and not end:
        data = yf.Ticker(ticker).history(period="2y")
    else:
        data = yf.Ticker(ticker).history(start=start, end=end)

    if data.empty or "Close" not in data.columns:
        raise HTTPException(status_code=404, detail=f"No price data found for ticker '{ticker}'")

    return data["Close"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Method dispatch and descriptions
_METHODS = {
    "historical": (
        historical_var,
        "Historical VaR — no distributional assumptions, based on actual observed returns.",
    ),
    "parametric": (
        parametric_var,
        "Parametric VaR — assumes normal returns; may underestimate tail risk due to fat tails.",
    ),
    "cvar": (
        conditional_var,
        "CVaR / Expected Shortfall — average loss beyond VaR; preferred by regulators (Basel III).",
    ),
}


@router.post("/var", response_model=VaRResponse)
def post_var(req: VaRRequest):
    """Compute Value-at-Risk for a single ticker.

    VaR answers: "With X% confidence, what is the maximum loss I can expect
    over Y trading days?"  It is the most widely-used single-line risk metric
    but should never be used in isolation — always pair with CVaR to understand
    the severity of tail losses.
    """
    if req.method not in _METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown method '{req.method}'. Choose from: {list(_METHODS.keys())}",
        )

    var_fn, note = _METHODS[req.method]
    returns = _fetch_returns(req.ticker, start=req.start, end=req.end)

    # CVaR does not accept holding_period
    if req.method == "cvar":
        var_value = var_fn(returns, confidence=req.confidence)
    else:
        var_value = var_fn(returns, confidence=req.confidence, holding_period=req.holding_period)

    return VaRResponse(
        ticker=req.ticker,
        method=req.method,
        confidence=req.confidence,
        holding_period=req.holding_period if req.method != "cvar" else 1,
        var=round(var_value, 6),
        observation_count=len(returns),
        note=note,
    )


@router.post("/mc", response_model=MCVarResponse)
def post_mc_var(req: MCVarRequest):
    """Compute VaR via Monte Carlo simulation of Geometric Brownian Motion.

    Unlike historical/parametric VaR which look backward, Monte Carlo VaR
    looks forward by simulating thousands of hypothetical price paths.
    This is useful for stress testing and "what-if" scenarios that never
    occurred in history.

    Note: GBM assumes constant volatility and no jumps, so extreme tail
    events are still likely under-estimated. Consider adding a jump-diffusion
    model for assets with known gap risk (earnings, biotech, etc.).
    """
    result = monte_carlo_var(
        S0=req.S0,
        mu=req.mu,
        sigma=req.sigma,
        T=req.T,
        n_sims=req.n_sims,
        confidence=req.confidence,
    )

    return MCVarResponse(
        var=result["var"],
        percentile_price=result["percentile_price"],
        mean_price=result["mean_price"],
        plot_json=result["plot_json"],
    )


@router.post("/portfolio", response_model=PortfolioVarResponse)
def post_portfolio_var(req: PortfolioVarRequest):
    """Compute portfolio-level Historical VaR from tickers and weights.

    Portfolio VaR accounts for diversification — cross-asset correlations
    reduce overall portfolio risk compared to summing individual VaRs.

    Weight validation warning: weights should sum to approximately 1.
    Weights > 1 imply leverage; weights << 1 imply cash drag.
    """
    # Check weights are plausible
    weight_sum = sum(req.weights)
    if abs(weight_sum - 1.0) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Portfolio weights should sum to ~1.0 (current sum: {weight_sum:.4f})",
        )

    if len(req.tickers) != len(req.weights):
        raise HTTPException(
            status_code=400,
            detail="Number of tickers must match number of weights",
        )

    # Fetch aligned returns for all tickers
    returns_dict = {}
    for t in req.tickers:
        ret = _fetch_returns(t, start=req.start, end=req.end)
        if ret.empty:
            continue
        returns_dict[t] = ret

    if len(returns_dict) < 2:
        raise HTTPException(status_code=404, detail="Not enough tickers with valid data")

    df = pd.DataFrame(returns_dict).dropna()
    if df.empty:
        raise HTTPException(status_code=404, detail="No overlapping data for the requested tickers")

    weights = np.array(req.weights[:len(df.columns)])
    var_value = portfolio_var(weights, df, confidence=req.confidence)

    return PortfolioVarResponse(
        tickers=list(df.columns),
        weights=req.weights,
        var=round(var_value, 6),
        confidence=req.confidence,
        observation_count=len(df),
        note="Portfolio VaR accounts for diversification through cross-asset correlation captured in returns data.",
    )
