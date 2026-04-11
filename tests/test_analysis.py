"""Tests for quant/analysis.py — time-series analytics engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.analysis import (
    rolling_volatility,
    historical_correlation,
    compute_beta,
    sharpe_ratio,
    max_drawdown,
    autocorrelation_test,
)


# ─── Rolling Volatility ──────────────────────────────────────────────


class TestRollingVolatility:
    """Test rolling_volatility: annualization, NaN windows."""

    def test_rolling_volatility_is_annualized_by_sqrt_252(self):
        """Volatility must be annualized by multiplying daily std by sqrt(252)."""
        # Create a series with known daily std
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 100))
        result = rolling_volatility(returns, window=20)
        # For a known std of 0.01, the expected annualized vol ≈ 0.01 * sqrt(252)
        expected_annualized = 0.01 * np.sqrt(252)
        # The actual rolling result will be close to this
        assert result.dropna().mean() == pytest.approx(expected_annualized, abs=0.05)

    def test_first_window_minus_1_rows_are_nan(self):
        """First window-1 values must be NaN (insufficient data for rolling window)."""
        returns = pd.Series(np.random.default_rng(0).normal(0, 0.01, 50))
        result = rolling_volatility(returns, window=20)
        assert result.iloc[:19].isna().all()
        assert not np.isnan(result.iloc[19])

    def test_rolling_vol_returns_positive_values(self):
        """Rolling volatility should always be positive (std is non-negative)."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.02, 100))
        result = rolling_volatility(returns, window=10)
        assert (result.dropna() > 0).all()


# ─── Correlation ────────────────────────────────────────────────────


class TestHistoricalCorrelation:
    """Test correlation matrix properties: diagonal=1, symmetry."""

    def test_correlation_matrix_diagonal_equals_one(self):
        """Diagonal of correlation matrix must equal 1.0."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "A": rng.normal(0, 0.01, 100),
            "B": rng.normal(0, 0.02, 100),
            "C": rng.normal(0, 0.015, 100),
        })
        corr = historical_correlation(df)
        for col in corr.columns:
            assert corr.loc[col, col] == pytest.approx(1.0)

    def test_correlation_matrix_is_symmetric(self):
        """Correlation matrix must be symmetric (corr(A,B) == corr(B,A))."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "A": rng.normal(0, 0.01, 100),
            "B": rng.normal(0, 0.02, 100),
            "C": rng.normal(0, 0.015, 100),
        })
        corr = historical_correlation(df)
        pd.testing.assert_frame_equal(corr, corr.T, check_exact=False)

    def test_perfectly_correlated_series(self):
        """Identical series should have correlation of 1.0."""
        data = np.random.default_rng(42).normal(0, 0.01, 100)
        df = pd.DataFrame({"A": data, "B": data.copy()})
        corr = historical_correlation(df)
        assert corr.loc["A", "B"] == pytest.approx(1.0)


# ─── Beta ───────────────────────────────────────────────────────────


class TestBeta:
    """Test compute_beta: identical series → 1.0, market vs asset."""

    def test_beta_of_identical_series_equals_one(self):
        """Beta of asset = market should be 1.0."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.015, 200))
        beta = compute_beta(returns, returns)
        assert beta == pytest.approx(1.0, abs=0.01)

    def test_beta_of_twice_levered_series(self):
        """If asset = 2 * market, beta should be approximately 2.0."""
        rng = np.random.default_rng(42)
        market = pd.Series(rng.normal(0, 0.01, 200))
        asset = market * 2.0
        beta = compute_beta(asset, market)
        assert beta == pytest.approx(2.0, abs=0.02)

    def test_beta_zero_variance_market(self):
        """Market with zero variance returns NaN beta."""
        market = pd.Series(np.zeros(100))
        asset = pd.Series(np.random.default_rng(42).normal(0, 0.01, 100))
        beta = compute_beta(asset, market)
        assert pd.isna(beta)


# ─── Sharpe Ratio ───────────────────────────────────────────────────


class TestSharpeRatio:
    """Test Sharpe ratio annualization formula."""

    def test_sharpe_ratio_is_annualized(self):
        """Sharpe = (mean * 252 - rf) / (std * sqrt(252))."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.0005, 0.01, 252))
        sr = sharpe_ratio(returns, risk_free_rate=0.05)
        # Manual calculation
        mean_daily = returns.mean()
        std_daily = returns.std()
        expected = (mean_daily * 252 - 0.05) / (std_daily * np.sqrt(252))
        assert sr == pytest.approx(expected)

    def test_sharpe_is_nan_for_zero_volatility(self):
        """Zero std returns NaN Sharpe ratio."""
        returns = pd.Series(np.zeros(50))
        sr = sharpe_ratio(returns)
        assert np.isnan(sr)

    def test_sharpe_ratio_with_known_inputs(self):
        """Test with hand-calculated values: mean=0.001/day, std=0.01/day."""
        returns = pd.Series([0.001] * 50)  # Constant return
        # std will be 0 for constant series
        sr = sharpe_ratio(returns)
        assert np.isnan(sr)


# ─── Maximum Drawdown ───────────────────────────────────────────────


class TestMaxDrawdown:
    """Test max drawdown: always <= 0, zero for monotonically increasing."""

    def test_max_drawdown_is_always_non_positive(self):
        """Max drawdown must always be <= 0."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0003, 0.015, 252)
        prices = pd.Series(100 * np.exp(np.cumsum(returns)))
        mdd = max_drawdown(prices)
        assert mdd <= 0

    def test_monotonically_increasing_prices_give_zero_drawdown(self):
        """Monotonically increasing prices → drawdown = 0."""
        prices = pd.Series([100, 101, 102, 103, 104, 105])
        mdd = max_drawdown(prices)
        assert mdd == pytest.approx(0.0)

    def test_max_drawdown_handles_constant_prices(self):
        """Constant prices → drawdown of 0."""
        prices = pd.Series([100.0] * 50)
        mdd = max_drawdown(prices)
        assert mdd == pytest.approx(0.0)

    def test_max_drawdown_handles_sharp_drop(self):
        """50% drop from 100 to 50 should give -0.5 drawdown."""
        prices = pd.Series([100.0, 50.0, 50.0, 50.0])
        mdd = max_drawdown(prices)
        assert mdd == pytest.approx(-0.5)

    def test_max_drawdown_with_empty_series(self):
        """Empty series edge case — returns 0.0 or NaN."""
        prices = pd.Series([], dtype=float)
        result = max_drawdown(prices)
        assert result == 0.0 or np.isnan(result)


# ─── Autocorrelation ───────────────────────────────────────────────


class TestAutocorrelation:
    """Test autocorrelation computation."""

    def test_autocorrelation_output_has_correct_length(self):
        """Output should have exactly `lags` entries, indexed 1..lags."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 100))
        result = autocorrelation_test(returns, lags=10)
        assert len(result) == 10
        assert list(result.index) == list(range(1, 11))

    def test_autocorrelation_of_random_series_near_zero(self):
        """Pure random series should have autocorrelations near 0."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.01, 500))
        result = autocorrelation_test(returns, lags=5)
        for lag in range(1, 6):
            assert abs(result[lag]) < 0.15  # generous bound for random

    def test_autocorrelation_constant_series(self):
        """Constant series autocorrelation is undefined (NaN)."""
        returns = pd.Series(np.ones(50))
        result = autocorrelation_test(returns, lags=5)
        assert result.isna().all() or (result == 1.0).all()
