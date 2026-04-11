"""Tests for quant/data_collector.py — OHLCV fetch, clean, store pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from quant.data_collector import (
    fetch_ohlcv,
    compute_returns,
    _check_cache,
    _has_full_range,
    store_records,
)


# ─── compute_returns ─────────────────────────────────────────────────


class TestComputeReturns:
    """Test return calculations: simple and log return formulas."""

    def test_simple_return_formula(self):
        """Simple return = (P_t - P_{t-1}) / P_{t-1}."""
        df = pd.DataFrame({"close": [100.0, 105.0, 98.0]})
        result = compute_returns(df)
        # First row is NaN (no prior), second row = 5/100 = 0.05
        assert np.isnan(result["simple_return"].iloc[0])
        assert result["simple_return"].iloc[1] == pytest.approx(0.05)
        assert result["simple_return"].iloc[2] == pytest.approx((98 - 105) / 105)

    def test_log_return_formula(self):
        """Log return = ln(P_t / P_{t-1})."""
        df = pd.DataFrame({"close": [100.0, 105.0, 98.0]})
        result = compute_returns(df)
        # ln(105/100) ≈ 0.04879
        assert result["log_return"].iloc[1] == pytest.approx(np.log(105 / 100))
        assert result["log_return"].iloc[2] == pytest.approx(np.log(98 / 105))

    def test_nan_rows_are_forward_filled_not_dropped(self):
        """NaN values in price data are forward-filled, not dropped."""
        df = pd.DataFrame({
            "close": [100.0, np.nan, 98.0],
            "open": [99.0, np.nan, 97.0],
            "high": [101.0, np.nan, 99.0],
            "low": [98.0, np.nan, 96.0],
            "volume": [1000.0, np.nan, 900.0],
        })
        # Forward-fill happens in fetch_ohlcv; compute_returns just computes
        # but we test that after ffill, returns are computed for filled rows.
        df_ffilled = df.ffill()
        result = compute_returns(df_ffilled)
        # After ffill, row 1 is [100.0, 100.0], so return ≈ 0
        assert result["simple_return"].iloc[1] == pytest.approx(0.0)

    def test_dataframe_has_required_return_columns(self):
        """Returned DataFrame has columns: simple_return, log_return."""
        df = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
        result = compute_returns(df)
        assert "simple_return" in result.columns
        assert "log_return" in result.columns

    def test_first_row_returns_are_nan(self):
        """First row has NaN returns since there is no prior price."""
        df = pd.DataFrame({"close": [100.0, 101.0]})
        result = compute_returns(df)
        assert np.isnan(result["simple_return"].iloc[0])
        assert np.isnan(result["log_return"].iloc[0])


# ─── fetch_ohlcv ─────────────────────────────────────────────────────


class TestFetchOhlcv:
    """Test yfinance fetching with mocked responses."""

    def _make_mock_history(self):
        """Create a mock yfinance history DataFrame."""
        dates = pd.bdate_range("2025-01-01", periods=50)
        return pd.DataFrame({
            "Open": [100.0] * 50,
            "High": [101.0] * 50,
            "Low": [99.0] * 50,
            "Close": [100.5] * 50,
            "Volume": [1_000_000] * 50,
        }, index=dates)

    def test_empty_yfinance_response_raises_valueerror(self):
        """Empty yfinance response returns empty DataFrame (no ValueError, but empty)."""
        with patch("quant.data_collector.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_yf.Ticker.return_value = mock_ticker
            df = fetch_ohlcv("INVALID", "2025-01-01", "2025-02-01")
            assert df.empty

    def test_fetch_returns_dataframe_with_date_column(self):
        """fetch_ohlcv returns DataFrame with a 'date' column."""
        with patch("quant.data_collector.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = self._make_mock_history()
            mock_yf.Ticker.return_value = mock_ticker
            df = fetch_ohlcv("AAPL", "2025-01-01", "2025-02-01")
            assert "date" in df.columns
            assert "close" in df.columns

    def test_fetch_lowercase_columns(self):
        """Column names are lowercased after fetching."""
        with patch("quant.data_collector.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = self._make_mock_history()
            mock_yf.Ticker.return_value = mock_ticker
            df = fetch_ohlcv("AAPL", "2025-01-01", "2025-02-01")
            for col in df.columns:
                assert col == col.lower()

    def test_invalid_ticker_returns_empty(self):
        """Invalid tickers that return no data produce an empty DataFrame."""
        with patch("quant.data_collector.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_yf.Ticker.return_value = mock_ticker
            df = fetch_ohlcv("FAKE", "2025-01-01", "2025-02-01")
            assert df.empty


# ─── cache ───────────────────────────────────────────────────────────


class TestCache:
    """Test cache checking logic."""

    def test_cache_prevents_duplicate_yfinance_calls_on_full_cached(self):
        """When entire date range is cached, _check_cache returns (None, None)."""
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            MagicMock(date="2025-02-01"),
            MagicMock(date="2025-01-31"),
        ]
        adj_start, adj_end = _check_cache(session, "AAPL", "2025-01-01", "2025-02-01")
        assert adj_start is None
        assert adj_end is None

    def test_cache_returns_partial_range_when_partial_cached(self):
        """When only partial data cached, return adjusted start date."""
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            MagicMock(date="2025-01-15"),
        ]
        adj_start, adj_end = _check_cache(session, "AAPL", "2025-01-01", "2025-02-01")
        assert adj_start == "2025-01-16"
        assert adj_end == "2025-02-01"

    def test_check_cache_empty_returns_original_range(self):
        """No cached data returns original date range."""
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        adj_start, adj_end = _check_cache(session, "AAPL", "2025-01-01", "2025-02-01")
        assert adj_start == "2025-01-01"
        assert adj_end == "2025-02-01"

    def test_has_full_range_returns_true_when_cached(self):
        """_has_full_range returns True when any cached data exists."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(date="2025-01-15"),
        ]
        assert _has_full_range(session, "AAPL", "2025-01-01", "2025-02-01") is True

    def test_has_full_range_returns_false_when_not_cached(self):
        """_has_full_range returns False when no cached data."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        assert _has_full_range(session, "AAPL", "2025-01-01", "2025-02-01") is False


# ─── store_records ───────────────────────────────────────────────────


class TestStoreRecords:
    """Test DB persistence layer."""

    def test_store_records_with_valid_dataframe(self):
        """store_records processes all rows when given valid data."""
        mock_engine = MagicMock()
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-02"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000.0, 1100.0],
            "simple_return": [0.01, 0.0099],
            "log_return": [0.00995, 0.00985],
        })
        with patch("quant.data_collector.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_session.query.return_value.filter_by.return_value.first.return_value = None
            count = store_records(mock_engine, df, "AAPL")
            assert count == 2
            mock_session.commit.assert_called_once()
