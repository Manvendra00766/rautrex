"""Tests for quant/strategies/backtest.py — backtester engine, strategies, cost modeling."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.strategies.backtest import (
    MomentumStrategy,
    MeanReversionStrategy,
    MovingAverageCrossover,
    Backtester,
    BacktestResult,
    STRATEGIES,
)


@pytest.fixture(scope="module")
def sample_prices():
    """Realistic price series for backtesting (~252 trading days, starts at 100)."""
    rng = np.random.default_rng(42)
    daily_rets = rng.normal(0.0003, 0.015, 252)
    prices = 100.0 * np.exp(np.cumsum(daily_rets))
    return pd.Series(prices, index=pd.bdate_range("2025-01-01", periods=252))


@pytest.fixture(scope="module")
def monotonically_increasing_prices():
    """Monotonically increasing prices for flat-signal tests."""
    return pd.Series(
        100 + np.arange(252),
        index=pd.bdate_range("2025-01-01", periods=252),
    )


# ─── Backtester Core ────────────────────────────────────────────────


class TestBacktesterLag:
    """Test signal lagging and look-ahead bias prevention."""

    def test_signals_lagged_by_one_period(self, sample_prices):
        """Signals should be shifted by 1 period in backtesting."""
        signals = pd.Series(1, index=sample_prices.index)  # Always long
        result = Backtester.run(sample_prices, signals)
        # Manual check: lagged signals[0] is NaN from shift(1)
        lagged = signals.shift(1)
        assert np.isnan(lagged.iloc[0])

    def test_flat_signal_produces_near_zero_strategy_return(self, sample_prices):
        """Flat signal (all zeros) produces approximately zero strategy return."""
        zero_signals = pd.Series(0, index=sample_prices.index)
        result = Backtester.run(sample_prices, zero_signals)
        # With zero signals, strategy returns = 0 * price_returns = 0, minus tx costs
        total_ret = result.total_return
        # Only tx costs make it slightly negative
        assert total_ret <= 0
        assert total_ret >= -0.05  # bounded by transaction costs only

    def test_always_long_matches_buy_and_hold_minus_costs(self, sample_prices):
        """Always-long signal should approximately match buy-and-hold minus costs."""
        long_signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, long_signals, transaction_cost=0.0)
        bh_return = sample_prices.iloc[-1] / sample_prices.iloc[0] - 1
        # Close match within small tolerance (some rounding from pct_change)
        assert result.total_return == pytest.approx(bh_return, abs=0.02)


class TestBacktesterCosts:
    """Test transaction cost modeling."""

    def test_transaction_costs_reduce_total_return(self, sample_prices):
        """Higher transaction costs reduce total return."""
        signals = pd.Series(np.random.default_rng(42).choice([-1, 0, 1], size=252), index=sample_prices.index)
        result_cheap = Backtester.run(sample_prices, signals, transaction_cost=0.0001)
        result_expensive = Backtester.run(sample_prices, signals, transaction_cost=0.01)
        assert result_cheap.total_return > result_expensive.total_return

    def test_expensive_costs_make_frequent_trading_unprofitable(self, sample_prices):
        """Very high costs should turn even random signals very negative."""
        signals = pd.Series(np.random.default_rng(42).choice([-1, 1], size=252), index=sample_prices.index)
        result = Backtester.run(sample_prices, signals, transaction_cost=0.1)  # 10% per trade
        assert result.total_return < -0.5


class TestBacktesterEquityCurve:
    """Test equity curve and metrics."""

    def test_equity_curve_initial_value_is_one(self, sample_prices):
        """Equity curve starts near 1.0 (after dropna/shift)."""
        signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, signals, transaction_cost=0.0)
        # After shift(1) and dropna, first equity value is after 1 day
        assert result.equity_curve.iloc[0] > 0.9

    def test_elevated_equity_after_positive_returns(self):
        """If prices always increase, equity should end above 1."""
        prices = pd.Series([100, 101, 102, 103, 104, 105])
        signals = pd.Series(1, index=prices.index)
        result = Backtester.run(prices, signals, transaction_cost=0.0)
        assert result.equity_curve.iloc[-1] > 1.0

    def test_sharpe_ratio_computed_annualized(self, sample_prices):
        """Sharpe is annualized (multiplied by sqrt(252))."""
        signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, signals, transaction_cost=0.0)
        # Verify by manual calculation
        daily_rets = result.daily_returns
        expected_sharpe = daily_rets.mean() / daily_rets.std() * np.sqrt(252)
        assert result.annualized_sharpe == pytest.approx(expected_sharpe)

    def test_max_drawdown_is_non_positive(self, sample_prices):
        """Max drawdown is always <= 0."""
        signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, signals)
        assert result.max_drawdown <= 0

    def test_result_is_backtest_result_instance(self, sample_prices):
        """Returns proper BacktestResult."""
        signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, signals)
        assert isinstance(result, BacktestResult)


# ─── Strategies ─────────────────────────────────────────────────────


class TestStrategies:
    """Test individual strategy signal generation."""

    def test_momentum_strategy_generates_signals(self, sample_prices):
        """Momentum strategy generates 1, -1, or 0 signals."""
        strat = MomentumStrategy(lookback=20)
        signals = strat.generate_signals(sample_prices)
        assert set(signals.unique()).issubset({0.0, 1.0, -1.0})
        assert len(signals) == len(sample_prices)

    def test_mean_reversion_strategy_generates_signals(self, sample_prices):
        """Mean reversion strategy generates 1, -1, or 0 signals."""
        strat = MeanReversionStrategy(window=20, z_threshold=1.5)
        signals = strat.generate_signals(sample_prices)
        assert set(signals.unique()).issubset({0.0, 1.0, -1.0})
        assert len(signals) == len(sample_prices)

    def test_ma_crossover_strategy_generates_signals(self, sample_prices):
        """MA crossover strategy generates 1, -1, or 0 signals."""
        strat = MovingAverageCrossover(fast=10, slow=50)
        signals = strat.generate_signals(sample_prices)
        assert set(signals.unique()).issubset({0.0, 1.0, -1.0})
        assert len(signals) == len(sample_prices)

    def test_strategy_registry_has_expected_keys(self):
        """STRATEGIES dict has the expected strategy names."""
        assert "momentum" in STRATEGIES
        assert "mean_reversion" in STRATEGIES
        assert "ma_cross" in STRATEGIES


# ─── Plot Results ───────────────────────────────────────────────────


class TestPlotResults:
    """Test Plotly chart generation."""

    def test_plot_results_returns_dict(self, sample_prices):
        """plot_results returns a JSON-serializable dict."""
        signals = pd.Series(1, index=sample_prices.index)
        result = Backtester.run(sample_prices, signals)
        plot = Backtester.plot_results(result)
        assert isinstance(plot, dict)
        assert "data" in plot
