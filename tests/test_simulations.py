"""Tests for quant/stochastic/simulations.py — GBM, Brownian motion, random walk."""

from __future__ import annotations

import time
import numpy as np
import pytest

from quant.stochastic.simulations import (
    random_walk,
    brownian_motion,
    geometric_brownian_motion,
    plot_simulations,
)


# ─── Random Walk ────────────────────────────────────────────────────


class TestRandomWalk:
    """Test random_walk: cumsum behavior, determinism with seed."""

    def test_random_walk_length(self):
        """Output length equals n_steps."""
        result = random_walk(n_steps=100, seed=42)
        assert len(result) == 100

    def test_random_walk_deterministic_with_seed(self):
        """Same seed produces identical output."""
        a = random_walk(n_steps=50, seed=7)
        b = random_walk(n_steps=50, seed=7)
        np.testing.assert_array_equal(a, b)

    def test_random_walk_first_value_is_first_draw(self):
        """First value of cumsum is the first standard normal draw."""
        rng = np.random.default_rng(42)
        draws = rng.standard_normal(10)
        expected = np.cumsum(draws)
        result = random_walk(n_steps=10, seed=42)
        np.testing.assert_array_almost_equal(result, expected)


# ─── Brownian Motion ────────────────────────────────────────────────


class TestBrownianMotion:
    """Test brownian_motion: zero mean drift, path shape."""

    def test_brownian_motion_path_shape(self):
        """Path shape is (n_steps+1,), starts at 0."""
        time_arr, path = brownian_motion(T=1.0, n_steps=100, seed=42)
        assert len(time_arr) == 101
        assert len(path) == 101
        assert path[0] == pytest.approx(0.0)

    def test_brownian_motion_time_starts_at_zero(self):
        """Time array starts at 0 and ends at T."""
        time_arr, _ = brownian_motion(T=2.0, n_steps=50, seed=42)
        assert time_arr[0] == pytest.approx(0.0)
        assert time_arr[-1] == pytest.approx(2.0)

    def test_brownian_motion_zero_mean_drift(self):
        """Brownian motion with mu=0 should have mean drift near 0 across many paths."""
        final_values = []
        for seed in range(100):
            _, path = brownian_motion(T=1.0, n_steps=252, sigma=0.2, seed=seed)
            final_values.append(path[-1])
        mean_final = np.mean(final_values)
        assert abs(mean_final) < 0.3  # Should be near zero in expectation


# ─── Geometric Brownian Motion ──────────────────────────────────────


class TestGBM:
    """Test GBM output: shape, positivity, deterministic, S0 column."""

    def test_gbm_output_shape(self):
        """GBM output shape is (n_sims, n_steps+1)."""
        paths = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=252, n_sims=100, seed=42
        )
        assert paths.shape == (100, 253)

    def test_gbm_first_column_equals_s0(self):
        """All paths start at S0 (column 0)."""
        paths = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=252, n_sims=1000, seed=42
        )
        np.testing.assert_array_almost_equal(paths[:, 0], np.full(1000, 100.0))

    def test_gbm_prices_always_positive(self):
        """All prices are positive (log-normal property)."""
        paths = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=252, n_sims=500, seed=42
        )
        assert np.all(paths > 0)

    def test_gbm_deterministic_with_seed(self):
        """Same seed produces identical paths."""
        a = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=100, n_sims=50, seed=123
        )
        b = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=100, n_sims=50, seed=123
        )
        np.testing.assert_array_equal(a, b)

    def test_gbm_vectorized_no_python_loops(self):
        """GBM should be fast due to vectorization — not a correctness test per se,
        but verifies no hidden Python for-loops over paths."""
        n_sims = 10_000
        start = time.perf_counter()
        geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=252, n_sims=n_sims, seed=42
        )
        elapsed = time.perf_counter() - start
        # 10k paths of 252 steps should complete in well under 2 seconds if vectorized
        assert elapsed < 2.0, f"GBM took {elapsed:.2f}s — likely not vectorized"

    def test_gbm_terminal_price_distribution(self):
        """Mean terminal price should be approximately S0 * exp(mu * T)."""
        paths = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.1, T=1.0, n_steps=252, n_sims=10000, seed=42
        )
        terminal = paths[:, -1]
        expected_mean = 100.0 * np.exp(0.05 * 1.0)
        assert terminal.mean() == pytest.approx(expected_mean, rel=0.05)


# ─── Plot Simulations ───────────────────────────────────────────────


class TestPlotSimulations:
    """Test plot_simulations output."""

    def test_plot_returns_valid_json(self):
        """plot_simulations returns a valid Plotly JSON."""
        import json
        paths = geometric_brownian_motion(
            S0=100.0, mu=0.05, sigma=0.2, T=1.0, n_steps=10, n_sims=5, seed=42
        )
        result = plot_simulations(paths, "Test")
        parsed = result if isinstance(result, dict) else json.loads(result)
        assert "data" in parsed

    def test_plot_handles_1d_input(self):
        """1D paths array is handled (wrapped to 2D)."""
        import json
        _, path = brownian_motion(T=1.0, n_steps=50, seed=42)
        result = plot_simulations(path, "Test")
        parsed = result if isinstance(result, dict) else json.loads(result)
        assert "data" in parsed
