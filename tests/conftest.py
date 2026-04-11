"""Shared pytest fixtures for the Rautrex test suite.

All fixtures are module-scoped or function-scoped depending on reuse needs.
Heavy fixtures (DataFrames with 252 rows) are session-scoped to avoid
rebuilding them for every test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# ─── Test data fixtures ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def sample_ohlcv() -> pd.DataFrame:
    """252-row OHLCV DataFrame with realistic prices simulating a stock
    starting around $100 with ~20% annualized volatility.

    Uses a fixed seed so tests are deterministic.
    """
    rng = np.random.default_rng(42)
    n = 252
    daily_mu = 0.05 / 252
    daily_sigma = 0.20 / np.sqrt(252)
    returns = rng.normal(daily_mu, daily_sigma, n)
    prices = 100 * np.exp(np.cumsum(returns))

    volumes = rng.integers(1_000_000, 10_000_000, n).astype(float)
    dates = pd.bdate_range("2025-01-01", periods=n)

    df = pd.DataFrame(
        {
            "open": prices * (1 + rng.uniform(-0.005, 0.005, n)),
            "high": prices * (1 + np.abs(rng.uniform(0, 0.02, n))),
            "low": prices * (1 - np.abs(rng.uniform(0, 0.02, n))),
            "close": prices,
            "volume": volumes,
        },
        index=dates,
    )
    df.index.name = "date"
    return df


@pytest.fixture(scope="session")
def sample_returns(sample_ohlcv: pd.DataFrame) -> pd.Series:
    """252-row log return series derived from sample_ohlcv close prices."""
    return np.log(sample_ohlcv["close"] / sample_ohlcv["close"].shift(1)).dropna()


@pytest.fixture(scope="session")
def multi_ticker_df() -> tuple[pd.DataFrame, list[str]]:
    """DataFrame with 3 ticker columns, each 252 rows of daily returns."""
    rng = np.random.default_rng(123)
    n = 252
    tickers = ["AAPL", "GOOGL", "MSFT"]
    data = {}
    for t in tickers:
        rets = rng.normal(0.0003, 0.015, n)
        data[t] = rets
    df = pd.DataFrame(data)
    return df, tickers


@pytest.fixture(scope="session")
def sample_prices_series(sample_ohlcv: pd.DataFrame) -> pd.Series:
    """Close price series from sample_ohlcv for drawdown/max_dd tests."""
    return sample_ohlcv["close"]


@pytest.fixture(scope="session")
def sample_mean_returns() -> np.ndarray:
    """Daily mean returns for 3 assets (from sample_ohlcv-like data)."""
    return np.array([0.0005, 0.0003, 0.0008])


@pytest.fixture(scope="session")
def sample_cov_matrix() -> np.ndarray:
    """Positive semi-definite 3x3 covariance matrix for portfolio tests."""
    return np.array([
        [0.0002, 0.0001, 0.00005],
        [0.0001, 0.0003, 0.00008],
        [0.00005, 0.00008, 0.0004],
    ])


@pytest.fixture(scope="session")
def auth_headers() -> dict:
    """JWT auth header for authenticated API calls.

    Uses a fake secret matching the default Settings secret_key.
    """
    from jose import jwt
    token_data = {"sub": "test@example.com", "user_id": 1}
    token = jwt.encode(token_data, "change-me-to-a-long-random-string", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ─── API test client ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """FastAPI TestClient with startup hooks mocked.

    We patch yfinance and database calls at the fixture level so that
    no real network requests are made during tests.
    """
    with patch("quant.data_collector.yf"), \
         patch("backend.api.analysis.yf"), \
         patch("backend.api.risk.yf"), \
         patch("backend.api.predict.yf"):
        from backend.main import app
        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="session")
def test_app():
    """Return the FastAPI app instance for direct use."""
    from backend.main import app
    return app
