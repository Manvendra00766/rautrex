"""Tests for quant/risk/risk_models.py — VaR, CVaR, Monte Carlo VaR, drawdown."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quant.risk.risk_models import (
    historical_var,
    parametric_var,
    conditional_var,
    monte_carlo_var,
    portfolio_var,
    drawdown_analysis,
    DrawdownResult,
)


# ─── Historical VaR ────────────────────────────────────────────────


class TestHistoricalVaR:
    """Test historical VaR: confidence ordering, non-negativity."""

    def test_var_95_more_conservative_than_90(self):
        """Historical VaR at 95% confidence is more conservative than at 90%."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.02, 500))
        var_95 = historical_var(returns, confidence=0.95)
        var_90 = historical_var(returns, confidence=0.90)
        assert var_95 > var_90

    def test_var_is_positive(self):
        """VaR is returned as a positive number (representing potential loss)."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(-0.0001, 0.02, 500))
        var = historical_var(returns, confidence=0.95)
        assert var > 0

    def test_var_scales_with_holding_period(self):
        """10-day VaR = 1-day VaR * sqrt(10)."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.02, 500))
        var_1d = historical_var(returns, confidence=0.95, holding_period=1)
        var_10d = historical_var(returns, confidence=0.95, holding_period=10)
        expected = var_1d * np.sqrt(10)
        assert var_10d == pytest.approx(expected, rel=0.01)

    def test_var_empty_returns_nan(self):
        """Empty returns returns NaN."""
        result = historical_var(pd.Series([], dtype=float))
        assert np.isnan(result)


# ─── Conditional VaR ───────────────────────────────────────────────


class TestCVaR:
    """Test CVaR: more conservative than VaR at same confidence."""

    def test_cvar_more_negative_than_var_at_same_confidence(self):
        """CVaR must always be >= VaR (more conservative / larger loss magnitude)."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.02, 500))
        var = historical_var(returns, confidence=0.95)
        cvar = conditional_var(returns, confidence=0.95)
        assert cvar >= var  # CVaR is always more conservative (larger number)

    def test_cvar_is_positive(self):
        """CVaR is returned as a positive number."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(-0.001, 0.02, 500))
        cvar = conditional_var(returns, confidence=0.95)
        assert cvar > 0

    def test_cvar_empty_returns_nan(self):
        """Empty returns for CVaR returns NaN."""
        result = conditional_var(pd.Series([], dtype=float))
        assert np.isnan(result)


# ─── Parametric VaR ─────────────────────────────────────────────────


class TestParametricVar:
    """Test parametric VaR formula matches manual calculation."""

    def test_parametric_var_formula(self):
        """Parametric VaR follows: mu - z * sigma, scaled by sqrt(T)."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.02, 1000))
        mu = returns.mean()
        sigma = returns.std(ddof=1)
        z = stats.norm.ppf(1 - 0.95)
        expected_var = -(mu + z * sigma)
        result = parametric_var(returns, confidence=0.95)
        assert abs(result) == pytest.approx(abs(expected_var), rel=0.01)

    def test_parametric_vs_historical_var(self):
        """Parametric and historical VaR should be in the same ballpark for normal data."""
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0, 0.015, 1000))
        h_var = historical_var(returns, confidence=0.95)
        p_var = parametric_var(returns, confidence=0.95)
        # Within a factor of 2 of each other for approximately normal data
        assert 0.5 * h_var < p_var < 2.0 * h_var


# ─── Monte Carlo VaR ───────────────────────────────────────────────


@pytest.mark.slow
class TestMonteCarloVaR:
    """Test MC VaR: convergence, structure."""

    def test_mc_var_returns_correct_keys(self):
        """Returns dict with var, percentile_price, mean_price, plot_json."""
        result = monte_carlo_var(S0=100.0, mu=0.05, sigma=0.2, T=1, n_sims=1000)
        assert "var" in result
        assert "percentile_price" in result
        assert "mean_price" in result
        assert "plot_json" in result

    def test_mc_var_converges_as_n_sims_increases(self):
        """VaR should stabilize as simulation count increases."""
        result_a = monte_carlo_var(S0=100.0, mu=0.05, sigma=0.2, T=1, n_sims=10_000, confidence=0.95)
        result_b = monte_carlo_var(S0=100.0, mu=0.05, sigma=0.2, T=1, n_sims=100_000, confidence=0.95)
        # Should be within ~5% of each other with large enough sims
        assert abs(result_a["var"] - result_b["var"]) / result_a["var"] < 0.1

    def test_mc_var_positive(self):
        """MC VaR should be positive (representing potential loss)."""
        result = monte_carlo_var(S0=100.0, mu=0.05, sigma=0.2, T=1, n_sims=5000)
        assert result["var"] > 0


# ─── Portfolio VaR ──────────────────────────────────────────────────


class TestPortfolioVaR:
    """Test portfolio-level VaR with diversification."""

    def test_portfolio_var_with_balanced_weights(self):
        """Portfolio VaR with a 2-asset portfolio is positive number."""
        rng = np.random.default_rng(42)
        n = 252
        ret_a = rng.normal(0.0005, 0.015, n)
        ret_b = rng.normal(0.0003, 0.012, n)
        df = pd.DataFrame({"A": ret_a, "B": ret_b})
        weights = np.array([0.5, 0.5])
        var = portfolio_var(weights, df, confidence=0.95)
        assert var > 0

    def test_portfolio_var_less_than_sum_of_individual_vars(self):
        """Diversified portfolio VaR < sum of individual asset VaRs (positive correlation assumed)."""
        rng = np.random.default_rng(42)
        n = 252
        ret_a = rng.normal(0.0005, 0.015, n)
        ret_b = rng.normal(0.0003, 0.020, n)
        df = pd.DataFrame({"A": ret_a, "B": ret_b})
        var_individual_a = historical_var(ret_a, 0.95)
        var_individual_b = historical_var(ret_b, 0.95)
        var_portfolio = portfolio_var(np.array([0.5, 0.5]), df, 0.95)
        # Portfolio VaR should be less than the weighted sum due to diversification
        total = 0.5 * var_individual_a + 0.5 * var_individual_b
        assert var_portfolio <= total + 0.001  # small tolerance


# ─── Drawdown Analysis ──────────────────────────────────────────────


class TestDrawdownAnalysis:
    """Test drawdown analysis: duration, severity."""

    def test_max_drawdown_duration_returns_integer(self):
        """max_drawdown_duration must return an integer (number of days)."""
        eq = pd.Series([100, 98, 96, 97, 95, 93, 94, 96, 100, 102])
        result = drawdown_analysis(eq)
        assert isinstance(result.max_drawdown_duration, int)

    def test_drawdown_result_is_drawdown_result_instance(self):
        """Returns a DrawdownResult dataclass."""
        eq = pd.Series([100, 99, 98, 97, 96, 97, 98, 99, 100])
        result = drawdown_analysis(eq)
        assert isinstance(result, DrawdownResult)

    def test_max_drawdown_always_non_positive(self):
        """Max drawdown from analysis is <= 0."""
        eq = pd.Series([100, 105, 90, 95, 100, 110])
        result = drawdown_analysis(eq)
        assert result.max_drawdown <= 0

    def test_monotonically_increasing_equity_has_zero_drawdown(self):
        """Always-rising equity → no drawdown."""
        eq = pd.Series([100, 101, 102, 103, 104, 105])
        result = drawdown_analysis(eq)
        assert result.max_drawdown == pytest.approx(0.0)
        assert result.max_drawdown_duration == 0

    def test_avg_drawdown_is_non_positive(self):
        """Average drawdown during underwater periods is <= 0."""
        eq = pd.Series([100, 98, 95, 97, 93, 90, 92, 100])
        result = drawdown_analysis(eq)
        assert result.avg_drawdown <= 0
