"""Tests for quant/portfolio/optimizer.py — MPT, efficient frontier, Sharpe, min-var."""

from __future__ import annotations

import json
import numpy as np
import pytest

from quant.portfolio.optimizer import (
    portfolio_stats,
    efficient_frontier,
    max_sharpe_portfolio,
    min_variance_portfolio,
    plot_efficient_frontier,
)


# ─── Portfolio Stats ────────────────────────────────────────────────


class TestPortfolioStats:
    """Test annualized return, vol, Sharpe calculations."""

    def test_portfolio_stats_annualized_return(self):
        """Annualized return = weights @ mean_returns * 252."""
        weights = np.array([0.5, 0.5])
        mean_returns = np.array([0.001, 0.0005])
        cov = np.array([[0.0002, 0.0001], [0.0001, 0.0003]])
        ann_ret, ann_vol, sharpe = portfolio_stats(weights, mean_returns, cov, rf=0.05)
        expected_ret = (0.5 * 0.001 + 0.5 * 0.0005) * 252
        assert ann_ret == pytest.approx(expected_ret)

    def test_portfolio_stats_annualized_vol(self):
        """Annualized vol = sqrt(weights @ cov @ weights) * sqrt(252)."""
        weights = np.array([0.5, 0.5])
        mean_returns = np.array([0.001, 0.0005])
        cov = np.array([[0.0002, 0.0001], [0.0001, 0.0003]])
        ann_ret, ann_vol, sharpe = portfolio_stats(weights, mean_returns, cov, rf=0.05)
        expected_vol = np.sqrt(weights @ cov @ weights) * np.sqrt(252)
        assert ann_vol == pytest.approx(expected_vol)

    def test_portfolio_stats_sharpe(self):
        """Sharpe = (ann_ret - rf) / ann_vol."""
        weights = np.array([0.5, 0.5])
        mean_returns = np.array([0.001, 0.0005])
        cov = np.array([[0.0004, 0.0001], [0.0001, 0.0004]])
        ann_ret, ann_vol, sharpe = portfolio_stats(weights, mean_returns, cov, rf=0.05)
        expected_sharpe = (ann_ret - 0.05) / ann_vol
        assert sharpe == pytest.approx(expected_sharpe)

    def test_portfolio_stats_zero_volatility(self):
        """Zero volatility portfolio returns Sharpe of 0."""
        weights = np.array([1.0])
        mean_returns = np.array([0.001])
        cov = np.array([[0.0]])
        ann_ret, ann_vol, sharpe = portfolio_stats(weights, mean_returns, cov, rf=0.05)
        assert ann_vol == pytest.approx(0.0)
        assert sharpe == 0.0


# ─── Max Sharpe ─────────────────────────────────────────────────────


class TestMaxSharpePortfolio:
    """Test tangency portfolio: weights sum, non-negativity."""

    def test_max_sharpe_weights_sum_to_one(self, sample_mean_returns, sample_cov_matrix):
        """Optimal weights must sum to 1.0."""
        weights_dict = max_sharpe_portfolio(sample_mean_returns, sample_cov_matrix, rf=0.05)
        assert sum(weights_dict.values()) == pytest.approx(1.0, abs=1e-4)

    def test_max_sharpe_all_weights_non_negative(self, sample_mean_returns, sample_cov_matrix):
        """All weights >= 0 (long-only constraint)."""
        weights_dict = max_sharpe_portfolio(sample_mean_returns, sample_cov_matrix, rf=0.05)
        for key, val in weights_dict.items():
            assert val >= -1e-8  # small tolerance for floating point

    def test_max_sharpe_has_higher_sharpe_than_min_variance(self, sample_mean_returns, sample_cov_matrix):
        """Max Sharpe portfolio should have Sharpe >= min variance portfolio."""
        max_sharpe_w = np.array(list(max_sharpe_portfolio(sample_mean_returns, sample_cov_matrix, rf=0.05).values()))
        min_var_w = np.array(list(min_variance_portfolio(sample_mean_returns, sample_cov_matrix).values()))
        _, _, sharpe_max = portfolio_stats(max_sharpe_w, sample_mean_returns, sample_cov_matrix, rf=0.05)
        _, _, sharpe_min = portfolio_stats(min_var_w, sample_mean_returns, sample_cov_matrix, rf=0.05)
        assert sharpe_max >= sharpe_min - 0.01  # small tolerance


# ─── Min Variance ───────────────────────────────────────────────────


class TestMinVariancePortfolio:
    """Test global min-variance portfolio."""

    def test_min_variance_weights_sum_to_one(self, sample_mean_returns, sample_cov_matrix):
        """Weights must sum to 1.0."""
        weights_dict = min_variance_portfolio(sample_mean_returns, sample_cov_matrix)
        assert sum(weights_dict.values()) == pytest.approx(1.0, abs=1e-4)

    def test_min_variance_all_weights_non_negative(self, sample_mean_returns, sample_cov_matrix):
        """All weights >= 0."""
        weights_dict = min_variance_portfolio(sample_mean_returns, sample_cov_matrix)
        for val in weights_dict.values():
            assert val >= -1e-8

    def test_single_asset_portfolio_returns_weight_one(self):
        """Single-asset portfolio returns weight of 1.0."""
        mean_returns = np.array([0.001])
        cov_matrix = np.array([[0.0004]])
        weights = min_variance_portfolio(mean_returns, cov_matrix)
        assert list(weights.values())[0] == pytest.approx(1.0)

    def test_single_asset_max_sharpe(self):
        """Single-asset max sharpe returns weight of 1.0."""
        mean_returns = np.array([0.001])
        cov_matrix = np.array([[0.0004]])
        weights = max_sharpe_portfolio(mean_returns, cov_matrix)
        assert list(weights.values())[0] == pytest.approx(1.0)


# ─── Efficient Frontier ─────────────────────────────────────────────


class TestEfficientFrontier:
    """Test frontier computation: monotonic return, valid points."""

    def test_efficient_frontier_returns_list(self, sample_mean_returns, sample_cov_matrix):
        """Frontier returns a list of (return, volatility) tuples."""
        frontier = efficient_frontier(sample_mean_returns, sample_cov_matrix, n_points=20)
        assert len(frontier) > 0
        assert isinstance(frontier[0], tuple)
        assert len(frontier[0]) == 2

    def test_efficient_frontier_monotonically_increasing_return(self, sample_mean_returns, sample_cov_matrix):
        """Returns should roughly increase with volatility along the frontier."""
        frontier = efficient_frontier(sample_mean_returns, sample_cov_matrix, n_points=50)
        frontier_sorted = sorted(frontier, key=lambda x: x[1])  # sort by vol
        returns = [p[0] for p in frontier_sorted]
        # Returns should generally increase with volatility (allow small deviations)
        assert returns[-1] >= returns[0]

    def test_efficient_frontier_positive_volatility(self, sample_mean_returns, sample_cov_matrix):
        """All frontier points have positive volatility."""
        frontier = efficient_frontier(sample_mean_returns, sample_cov_matrix, n_points=20)
        for ret, vol in frontier:
            assert vol > 0


# ─── Plot ───────────────────────────────────────────────────────────


class TestPlotEfficientFrontier:
    """Test Plotly JSON generation."""

    def test_plot_returns_valid_json_string(self):
        """plot_efficient_frontier returns a JSON string."""
        points = [(0.10, 0.15), (0.12, 0.18), (0.15, 0.20)]
        result = plot_efficient_frontier(points)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_plot_with_scatter_data(self):
        """Plot with additional portfolio scatter data."""
        points = [(0.10, 0.15), (0.12, 0.18)]
        scatter = [
            {"volatility": 0.16, "return": 0.11, "sharpe": 0.375, "label": "P1"},
            {"volatility": 0.20, "return": 0.13, "sharpe": 0.4, "label": "P2"},
        ]
        result = plot_efficient_frontier(points, scatter)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_plot_empty_frontier(self):
        """Empty frontier should still produce a valid plot."""
        result = plot_efficient_frontier([])
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
