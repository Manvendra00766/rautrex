"""
FastAPI routes for the Rautrex time-series analytics engine.

Endpoints wrap the quant/analysis functions and handle data fetching,
validation, and serialization.
"""

from __future__ import annotations

import yfinance as yf
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from quant.analysis import (
    rolling_volatility,
    historical_correlation,
    compute_beta,
    sharpe_ratio,
    max_drawdown,
    autocorrelation_test,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class VolatilityRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. 'AAPL'")
    window: int = Field(default=20, ge=2, le=500, description="Rolling window in trading days")


class VolatilityResponse(BaseModel):
    ticker: str
    window: int
    rolling_volatility: dict  # {date_iso: value}


class CorrelationRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=50, description="List of ticker symbols")


class CorrelationResponse(BaseModel):
    tickers: list[str]
    correlation_matrix: dict  # nested dict {ticker: {ticker: value}}


class MetricsRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. 'AAPL'")
    market_ticker: str = Field(default="^GSPC", description="Market benchmark (default S&P 500)")


class MetricsResponse(BaseModel):
    ticker: str
    sharpe_ratio: float | None
    max_drawdown: float | None
    beta: float | None
    current_volatility: float | None  # latest 20-day rolling vol
    autocorrelation: dict  # {lag: value}
    period: str  # date range fetched
    observation_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_returns(ticker: str) -> pd.Series:
    """Fetch daily close prices from Yahoo Finance and compute daily returns.

    Returns a pandas Series with a DatetimeIndex of daily pct_change values.
    Raises HTTPException on failure.
    """
    try:
        data = yf.Ticker(ticker).history(period="2y")  # ~2 years of daily data
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data for {ticker}: {exc}")

    if data.empty or "Close" not in data.columns:
        raise HTTPException(status_code=404, detail=f"No price data found for ticker '{ticker}'")

    return data["Close"].pct_change().dropna()


def _fetch_prices(ticker: str) -> pd.Series:
    """Fetch daily adjusted close prices from Yahoo Finance."""
    try:
        data = yf.Ticker(ticker).history(period="2y")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data for {ticker}: {exc}")

    if data.empty or "Close" not in data.columns:
        raise HTTPException(status_code=404, detail=f"No price data found for ticker '{ticker}'")

    return data["Close"]


def _fetch_multi_returns(tickers: list[str]) -> pd.DataFrame:
    """Fetch returns for multiple tickers, aligned on shared dates."""
    dfs = {}
    for t in tickers:
        ret = _fetch_returns(t)
        if ret.empty:
            continue
        dfs[t] = ret

    if len(dfs) < 2:
        raise HTTPException(status_code=404, detail="Not enough tickers with valid data (need at least 2)")

    df = pd.DataFrame(dfs).dropna()

    if df.empty:
        raise HTTPException(status_code=404, detail="No overlapping data for the requested tickers")

    return df


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/volatility", response_model=VolatilityResponse)
def post_volatility(req: VolatilityRequest):
    """Return annualized rolling volatility for a single ticker.

    The rolling window captures how the asset's risk profile has changed
    over time — useful for spotting volatility regimes and timing entries.
    """
    returns = _fetch_returns(req.ticker)

    if len(returns) < req.window:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data points ({len(returns)}) for window size {req.window}",
        )

    result = rolling_volatility(returns, window=req.window)
    return VolatilityResponse(
        ticker=req.ticker,
        window=req.window,
        rolling_volatility=result.dropna().apply(lambda x: round(x, 6)).to_dict(),
    )


@router.post("/correlation", response_model=CorrelationResponse)
def post_correlation(req: CorrelationRequest):
    """Return the historical correlation matrix for a list of tickers.

    Correlation reveals which assets move together — essential for
    diversification.  Low pairwise correlations mean the portfolio
    benefits from true risk reduction rather than concentrated bets.
    """
    df = _fetch_multi_returns(req.tickers)
    corr = historical_correlation(df)
    return CorrelationResponse(
        tickers=list(corr.columns),
        correlation_matrix={
            col: {idx: round(corr.loc[idx, col], 6) for idx in corr.columns}
            for col in corr.columns
        },
    )


@router.post("/metrics", response_model=MetricsResponse)
def post_metrics(req: MetricsRequest):
    """Return a bundle of key risk/return metrics for a single ticker.

    This endpoint is a one-stop summary for a quick asset health check:

    - **Sharpe ratio**: risk-adjusted return vs risk-free rate
    - **Max drawdown**: worst peak-to-trough historical loss
    - **Beta**: sensitivity to broad market moves (systematic risk)
    - **Volatility**: latest 20-day annualized standard deviation
    - **Autocorrelation**: serial dependence in returns (momentum vs mean-reversion signal)
    """
    returns = _fetch_returns(req.ticker)
    prices = _fetch_prices(req.ticker)

    if len(returns) < 2:
        raise HTTPException(status_code=400, detail=f"Not enough data for ticker '{req.ticker}'")

    # Beta requires fetching the market benchmark
    market_returns = _fetch_returns(req.market_ticker)

    # Compute all metrics
    sr = sharpe_ratio(returns)
    mdd = max_drawdown(prices)
    vol = rolling_volatility(returns, window=20)
    current_vol = vol.dropna().iloc[-1] if len(vol.dropna()) > 0 else None
    beta = compute_beta(returns, market_returns) if len(market_returns) > 0 else None
    autocorr = autocorrelation_test(returns, lags=10)

    # Align date range for reporting
    first_date = prices.index[0].strftime("%Y-%m-%d")
    last_date = prices.index[-1].strftime("%Y-%m-%d")

    return MetricsResponse(
        ticker=req.ticker,
        sharpe_ratio=round(sr, 4) if not np.isnan(sr) else None,
        max_drawdown=round(mdd, 4) if not np.isnan(mdd) else None,
        beta=round(beta, 4) if beta is not None and not np.isnan(beta) else None,
        current_volatility=round(current_vol, 6) if current_vol else None,
        autocorrelation={str(k): round(v, 6) for k, v in autocorr.items() if not np.isnan(v)},
        period=f"{first_date} to {last_date}",
        observation_count=len(returns),
    )
