"""Tests for quant/options/black_scholes.py — pricing, Greeks, IV, payoff."""

from __future__ import annotations

import math
import numpy as np
import pytest
from scipy.stats import norm

from quant.options.black_scholes import (
    black_scholes_price,
    greeks,
    implied_volatility,
    option_payoff_diagram,
)


# ─── Black-Scholes Price ────────────────────────────────────────────


class TestBlackScholesPrice:
    """Test option pricing: positivity, put-call parity, intrinsic value."""

    def test_call_price_positive_itm(self):
        """Call price > 0 for in-the-money option (S > K)."""
        price = black_scholes_price(S=105.0, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="call")
        assert price > 0

    def test_put_price_positive(self):
        """Put price > 0 for any T > 0."""
        price = black_scholes_price(S=100.0, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="put")
        assert price > 0

    def test_put_call_parity(self):
        """Put-call parity: C - P = S - K*e^(-rT)."""
        S, K, T, r, sigma = 100.0, 100.0, 0.5, 0.05, 0.2
        call = black_scholes_price(S, K, T, r, sigma, "call")
        put = black_scholes_price(S, K, T, r, sigma, "put")
        lhs = call - put
        rhs = S - K * math.exp(-r * T)
        assert lhs == pytest.approx(rhs, abs=1e-6)

    def test_delta_deep_itm_call_approaches_one(self):
        """Deep ITM call delta approaches 1.0."""
        g = greeks(S=200.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="call")
        assert g["delta"] == pytest.approx(1.0, abs=0.05)

    def test_delta_deep_otm_call_approaches_zero(self):
        """Deep OTM call delta approaches 0.0."""
        g = greeks(S=50.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="call")
        assert g["delta"] == pytest.approx(0.0, abs=0.05)

    def test_vega_always_positive(self):
        """Vega is always positive for long options."""
        for S in [80.0, 100.0, 120.0]:
            g = greeks(S=S, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="call")
            assert g["vega"] > 0
            g_put = greeks(S=S, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="put")
            assert g_put["vega"] > 0

    def test_gamma_always_positive(self):
        """Gamma is always positive for both calls and puts."""
        for S in [80.0, 100.0, 120.0]:
            g = greeks(S=S, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="call")
            assert g["gamma"] > 0
            g_put = greeks(S=S, K=100.0, T=0.25, r=0.05, sigma=0.2, option_type="put")
            assert g_put["gamma"] > 0

    def test_t_zero_call_returns_intrinsic(self):
        """T=0 call returns intrinsic value: max(S - K, 0)."""
        assert black_scholes_price(S=105.0, K=100.0, T=0, r=0.05, sigma=0.2, option_type="call") == pytest.approx(5.0)
        assert black_scholes_price(S=95.0, K=100.0, T=0, r=0.05, sigma=0.2, option_type="call") == pytest.approx(0.0)

    def test_t_zero_put_returns_intrinsic(self):
        """T=0 put returns intrinsic value: max(K - S, 0)."""
        assert black_scholes_price(S=95.0, K=100.0, T=0, r=0.05, sigma=0.2, option_type="put") == pytest.approx(5.0)
        assert black_scholes_price(S=105.0, K=100.0, T=0, r=0.05, sigma=0.2, option_type="put") == pytest.approx(0.0)

    def test_price_matches_hand_calculated_atm(self):
        """ATM call price via explicit formula check."""
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.0, 0.2
        price = black_scholes_price(S, K, T, r, sigma, "call")
        # With r=0, simplified: C = S * (N(d1) - N(d2)), d1 = sigma*sqrt(T)/2, d2 = -d1
        d1 = 0.5 * sigma * math.sqrt(T)
        d2 = -d1
        expected = S * (norm.cdf(d1) - norm.cdf(d2))
        assert price == pytest.approx(expected, abs=1e-6)


# ─── Greeks ─────────────────────────────────────────────────────────


class TestGreeks:
    """Test individual Greek values."""

    def test_atm_call_delta_near_half(self):
        """ATM call delta should be slightly above 0.5 (due to time value)."""
        g = greeks(S=100.0, K=100.0, T=0.25, r=0.0, sigma=0.2)
        assert 0.5 < g["delta"] < 0.6

    def test_atm_put_delta_near_negative_half(self):
        """ATM put delta should be slightly below -0.5."""
        g = greeks(S=100.0, K=100.0, T=0.25, r=0.0, sigma=0.2, option_type="put")
        assert -0.6 < g["delta"] < -0.4

    def test_greeks_t_zero_returns_zeros(self):
        """At T=0, all Greeks are zero."""
        g = greeks(S=100.0, K=100.0, T=0, r=0.05, sigma=0.2)
        for key in ["delta", "gamma", "vega", "theta", "rho"]:
            assert g[key] == pytest.approx(0.0)

    def test_rho_positive_for_call_negative_for_put(self):
        """Call rho is positive, put rho is negative."""
        g_call = greeks(S=100.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="call")
        g_put = greeks(S=100.0, K=100.0, T=0.5, r=0.05, sigma=0.2, option_type="put")
        assert g_call["rho"] > 0
        assert g_put["rho"] < 0


# ─── Implied Volatility ─────────────────────────────────────────────


class TestImpliedVolatility:
    """Test IV recovery, convergence, error handling."""

    def test_iv_recovers_input_sigma(self):
        """Given a theoretical price, IV should recover the input sigma."""
        S, K, T, r, sigma = 100.0, 100.0, 0.5, 0.05, 0.25
        price = black_scholes_price(S, K, T, r, sigma, "call")
        recovered = implied_volatility(price, S, K, T, r, "call")
        assert recovered == pytest.approx(sigma, abs=1e-3)

    def test_iv_recovers_put_sigma(self):
        """IV recovery works for put options too."""
        S, K, T, r, sigma = 100.0, 100.0, 0.5, 0.05, 0.30
        price = black_scholes_price(S, K, T, r, sigma, "put")
        recovered = implied_volatility(price, S, K, T, r, "put")
        assert recovered == pytest.approx(sigma, abs=1e-3)

    def test_iv_within_tolerance(self):
        """IV should recover input sigma within 0.001 tolerance."""
        S, K, T, r, sigma = 100.0, 105.0, 0.25, 0.03, 0.18
        price = black_scholes_price(S, K, T, r, sigma, "call")
        recovered = implied_volatility(price, S, K, T, r, "call")
        assert abs(recovered - sigma) < 0.001

    def test_iv_raises_below_intrinsic(self):
        """IV raises ValueError if market price is below intrinsic value."""
        with pytest.raises(ValueError, match="below intrinsic"):
            implied_volatility(market_price=1.0, S=100.0, K=90.0, T=0.25, r=0.05, option_type="call")
        # Intrinsic = max(100-90*exp(-0.05*0.25), 0) ≈ 10.1


# ─── Payoff Diagram ─────────────────────────────────────────────────


class TestPayoffDiagram:
    """Test payoff diagram generation."""

    def test_payoff_returns_valid_json(self):
        """Payoff diagram returns JSON-serializable Plotly figure."""
        import json
        prices = np.linspace(80, 120, 50)
        result = option_payoff_diagram(prices, K=100.0, premium=5.0, option_type="call")
        parsed = result if isinstance(result, dict) else json.loads(result)
        assert "data" in parsed

    def test_payoff_put_returns_valid_json(self):
        """Put payoff diagram also returns valid Plotly JSON."""
        import json
        prices = np.linspace(80, 120, 50)
        result = option_payoff_diagram(prices, K=100.0, premium=3.0, option_type="put")
        parsed = result if isinstance(result, dict) else json.loads(result)
        assert "data" in parsed
