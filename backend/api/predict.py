"""FastAPI routes for ML prediction.

WARNING: These endpoints return research signals ONLY.
  - A 53% accuracy signal is NOT a reason to trade.
  - Real costs (slippage + spread + commission) will eat most thin edges.
  - Models degrade over time as regimes shift — retrain regularly
    and monitor out-of-sample performance.
"""

from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from quant.ml.predictor import (
    build_features,
    predict_next,
    train_model,
    walk_forward_validation,
    FEATURE_COLS,
)
from backend.dependencies.tier_guard import require_pro
from backend.models.user import User

router = APIRouter(prefix="/predict", tags=["prediction"])

# In-process cache for trained models.
# In production, persist to disk or a model registry.
_models: dict[str, object] = {}
_scalers: dict[str, object] = {}
_tickers_data: dict[str, pd.DataFrame] = {}


def _fetch(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV from Yahoo Finance, standardise column names."""
    raw = yf.download(ticker, start=start, end=end, progress=False)
    # yfinance may produce MultiIndex columns in newer versions
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0).str.lower()
    else:
        raw.columns = raw.columns.str.lower()
    raw = raw.reset_index()
    raw.columns = raw.columns.str.lower()
    return raw


class TrainRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. AAPL")
    start: str = Field(..., description="Start date YYYY-MM-DD")
    end: str = Field(..., description="End date YYYY-MM-DD")
    model_type: str = Field(default="random_forest", description="'random_forest' or 'logistic_regression'")


class SignalRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol")


@router.post("/train")
async def train(req: TrainRequest):
    """Train a model on historical data. Returns diagnostics."""
    df = _fetch(req.ticker, req.start, req.end)
    df_features = build_features(df)

    result = train_model(df_features, model_type=req.model_type)

    _models[req.ticker] = result.model
    _scalers[req.ticker] = result.scaler
    _tickers_data[req.ticker] = df_features

    walk = walk_forward_validation(df_features, n_splits=5)

    return {
        "ticker": req.ticker,
        "model_type": req.model_type,
        "train_accuracy": result.train_accuracy,
        "test_accuracy": result.test_accuracy,
        "classification_report": result.classification_report_str,
        "feature_importances": result.feature_importances,
        "walk_forward_cv": walk,
    }


@router.post("/signal")
async def signal(req: SignalRequest):
    """Return today's directional signal for a ticker.

    Fetches the most recent 300 trading days, rebuilds features,
    and uses a cached model (must /train first) or trains on-the-fly.
    """
    if req.ticker not in _models:
        # Auto-train on last 2 years if no cached model
        train_req = TrainRequest(
            ticker=req.ticker,
            start="2024-01-01",
            end=date.today().isoformat(),
        )
        df = _fetch(train_req.ticker, train_req.start, train_req.end)
        df_features = build_features(df)
        result = train_model(df_features, model_type=train_req.model_type)
        _models[req.ticker] = result.model
        _scalers[req.ticker] = result.scaler

    # Fetch latest 300 days for fresh features
    df_latest = _fetch(req.ticker, "2024-01-01", date.today().isoformat())
    df_features = build_features(df_latest)

    # Drop NaNs, take last row
    clean = df_features.dropna(subset=FEATURE_COLS + ["target"])
    if clean.empty:
        return {"error": "Not enough data to generate features."}

    latest = clean.iloc[[-1]]
    prediction = predict_next(_models[req.ticker], _scalers[req.ticker], latest)

    return {
        "ticker": req.ticker,
        "date": str(latest.index[-1]) if isinstance(latest.index, pd.DatetimeIndex) else None,
        "signal": "UP" if prediction["predicted_direction"] == 1 else "DOWN",
        "probability_up": prediction["probability_up"],
    }


@router.get("/signals")
async def signals(user: User = Depends(require_pro)):
    return {"message": "Pro signals endpoint unlocked.", "tier": user.tier}
