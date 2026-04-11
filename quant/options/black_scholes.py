"""
Black-Scholes Option Pricing Engine

Implements closed-form European option pricing, Greeks,
implied volatility (Newton-Raphson), and payoff diagrams.

Uses scipy.stats.norm for the cumulative normal distribution N(x)
and the probability density function N'(x).
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm

OptionType = Literal["call", "put"]


# ---------------------------------------------------------------------------
# 1. Black-Scholes Price
# ---------------------------------------------------------------------------

def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
	"""
	Compute d1 and d2 of the Black-Scholes formula.

	d1 captures the probability-weighted moneyness adjusted for drift
	and volatility over the remaining life of the option.
	d2 is the adjusted value used to discount the strike payment.
	"""
	sqrt_T = math.sqrt(T)
	d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
	d2 = d1 - sigma * sqrt_T
	return d1, d2


def black_scholes_price(
	S: float,
	K: float,
	T: float,
	r: float,
	sigma: float,
	option_type: OptionType = "call",
) -> float:
	"""
	Compute the fair value of a European option.

	Args:
	    S:           Current spot price of the underlying
	    K:           Strike price
	    T:           Time to expiration in years (e.g. 30 days -> 30/365)
	    r:           Continuously compounded risk-free rate (e.g. 0.05 = 5%)
	    sigma:       Implied volatility as a decimal (e.g. 0.20 = 20%)
	    option_type: 'call' or 'put'

	Returns:
	    Theoretical option price.

	Formula:
	    Call = S * N(d1) - K * e^(-rT) * N(d2)
	    Put  = K * e^(-rT) * N(-d2) - S * N(-d1)

	Intuition: N(d1) is the delta (hedge ratio) - how many shares to hold
	to replicate the option. N(d2) is the risk-neutral probability the
	option expires ITM.
	"""
	if T <= 0:
		# Intrinsic value at expiry
		if option_type == "call":
			return max(S - K, 0.0)
		return max(K - S, 0.0)

	d1, d2 = _d1_d2(S, K, T, r, sigma)

	if option_type == "call":
		price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
	else:
		price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

	return price


# ---------------------------------------------------------------------------
# 2. Greeks
# ---------------------------------------------------------------------------

def greeks(
	S: float,
	K: float,
	T: float,
	r: float,
	sigma: float,
	option_type: OptionType = "call",
) -> dict[str, float]:
	"""
	Compute all first-order Greeks for an European option.

	Each Greek measures sensitivity to one market parameter while
	holding all others constant - essential for hedging and risk
	management.

	Returns:
	    dict with keys: delta, gamma, vega, theta, rho
	"""
	if T <= 0:
		return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}

	d1, d2 = _d1_d2(S, K, T, r, sigma)
	nd1 = norm.pdf(d1)  # N'(d1) - standard normal density at d1
	sqrt_T = math.sqrt(T)
	disc = math.exp(-r * T)  # discount factor

	# ---- Delta ----
	# Delta = change in option price for a $1 move in the underlying.
	# Traders use it as a hedge ratio (how many shares to offset one option)
	# and as a rough proxy for the probability the option expires ITM.
	if option_type == "call":
		delta = norm.cdf(d1)
	else:
		delta = norm.cdf(d1) - 1.0

	# ---- Gamma ----
	# Gamma = change in delta for a $1 move in the underlying.
	# High gamma means delta is very sensitive to spot moves, so the hedge
	# needs frequent rebalancing. Gamma is always positive for long options
	# and peaks for ATM near-expiry contracts.
	gamma = nd1 / (S * sigma * sqrt_T)

	# ---- Vega ----
	# Vega = change in option price for a 1-percentage-point change in sigma.
	# Despite the name it is not a Greek letter. Traders use vega to size
	# vol exposure: a vega of 0.50 means a 1 vol-point rise adds $0.50 to the
	# option's value. Long options are always long vega.
	# Here we divide by 100 so the returned value is per 1% vol change.
	vega = S * nd1 * sqrt_T / 100.0

	# ---- Theta ----
	# Theta = change in option value for one calendar day passing (per day).
	# Options lose time value as expiration approaches - this decay is
	# non-linear and accelerates for ATM options. A theta of -0.05 means
	# the option loses ~$0.05 per day from time decay alone.
	# Divided by 365 to convert from annual to daily.
	if option_type == "call":
		theta = (-(S * nd1 * sigma) / (2 * sqrt_T) - r * K * disc * norm.cdf(d2))
	else:
		theta = (-(S * nd1 * sigma) / (2 * sqrt_T) + r * K * disc * norm.cdf(-d2))
	theta /= 365.0  # per day

	# ---- Rho ----
	# Rho = change in option price for a 1-percentage-point change in the
	# risk-free rate. Rho matters most for LEAPS (long-dated options) and
	# in high-rate environments. For short-dated options it's negligible.
	if option_type == "call":
		rho = K * T * disc * norm.cdf(d2)
	else:
		rho = -K * T * disc * norm.cdf(-d2)

	return {
		"delta": float(delta),
		"gamma": float(gamma),
		"vega": float(vega),
		"theta": float(theta),
		"rho": float(rho),
	}


# ---------------------------------------------------------------------------
# 3. Implied Volatility (Newton-Raphson)
# ---------------------------------------------------------------------------

def implied_volatility(
	market_price: float,
	S: float,
	K: float,
	T: float,
	r: float,
	option_type: OptionType = "call",
	tol: float = 1e-6,
	max_iter: int = 100,
) -> float:
	"""
	Solve for the implied volatility that matches the observed market price.

	Uses Newton-Raphson iteration:
	    sigma_{n+1} = sigma_n + (market_price - BS_price(sigma_n)) / vega(sigma_n)

	Vega is the partial d_price/d_sigma, so this is simply Newton's method
	on the equation BS(sigma) - market_price = 0.

	Args:
	    market_price: Observed market price of the option
	    [other args]: Same as black_scholes_price
	    tol:          Convergence tolerance
	    max_iter:     Maximum iterations before giving up

	Returns:
	    Implied volatility as a decimal (e.g. 0.25 = 25%)

	Raises:
	    ValueError: If the price is below intrinsic value, if T <= 0,
	                or if Newton-Raphson fails to converge.
	"""
	# Validate intrinsic value floor
	if option_type == "call":
		intrinsic = max(S - K * math.exp(-r * T), 0.0)
	else:
		intrinsic = max(K * math.exp(-r * T) - S, 0.0)

	if market_price < intrinsic:
		raise ValueError(
			f"Market price {market_price} is below intrinsic value {intrinsic:.4f}"
		)

	# Initial guess using Brenner-Subrahmanyam approximation
	sigma = math.sqrt(2 * math.pi / T) * (market_price / S)
	sigma = max(sigma, 0.01)  # floor at 1%

	for i in range(max_iter):
		price = black_scholes_price(S, K, T, r, sigma, option_type)
		diff = market_price - price

		if abs(diff) < tol:
			return sigma

		# Vega returned as absolute (not per 1%) for NR iteration
		d1, _ = _d1_d2(S, K, T, r, sigma)
		vega = S * norm.pdf(d1) * math.sqrt(T)

		if vega < 1e-12:
			raise ValueError(
				"Vega too small - Newton-Raphson cannot converge. "
				"Option may be deeply ITM/OTM or near expiry."
			)

		sigma += diff / vega

		# Keep sigma positive
		sigma = max(sigma, 1e-6)

	raise ValueError(
		f"Implied volatility did not converge after {max_iter} iterations. "
		f"Last estimate: {sigma:.6f}, residual: {diff:.2e}"
	)


# ---------------------------------------------------------------------------
# 4. Option Payoff Diagram
# ---------------------------------------------------------------------------

def option_payoff_diagram(
	S_range: np.ndarray | list[float],
	K: float,
	premium: float,
	option_type: OptionType = "call",
) -> str:
	"""
	Generate a Plotly JSON figure showing the P&L of an option at expiry.

	The payoff shows the profit or loss for a long position at every
	possible underlying price at expiration, accounting for the premium paid.

	Args:
	    S_range:     Array/list of underlying prices at expiry
	    K:           Strike price
	    premium:     Premium paid per option
	    option_type: 'call' or 'put'

	Returns:
	    JSON string of a Plotly figure.

	Key reference lines:
	    - Blue line: P&L at expiry
	    - Red dashed: Strike price
	    - Green dashed: Break-even point
	"""
	S_arr = np.asarray(S_range, dtype=float)

	if option_type == "call":
		payoff = np.maximum(S_arr - K, 0) - premium
		breakeven = K + premium
	else:
		payoff = np.maximum(K - S_arr, 0) - premium
		breakeven = K - premium

	fig = go.Figure()

	# P&L line
	fig.add_trace(go.Scatter(
		x=S_arr.tolist(),
		y=payoff.tolist(),
		mode="lines",
		name="P&L",
		line=dict(color="royalblue", width=2),
	))

	# Strike reference
	fig.add_trace(go.Scatter(
		x=[K, K],
		y=[min(payoff) - 0.05 * abs(min(payoff)), max(payoff)],
		mode="lines",
		name=f"Strike ({K})",
		line=dict(color="red", width=1, dash="dash"),
		showlegend=True,
	))

	# Break-even reference
	fig.add_trace(go.Scatter(
		x=[breakeven, breakeven],
		y=[min(payoff) - 0.05 * abs(min(payoff)), max(payoff)],
		mode="lines",
		name=f"Break-even ({breakeven:.2f})",
		line=dict(color="green", width=1, dash="dash"),
		showlegend=True,
	))

	# Zero line (profit/loss boundary)
	fig.add_trace(go.Scatter(
		x=[min(S_arr), max(S_arr)],
		y=[0, 0],
		mode="lines",
		name="Zero",
		line=dict(color="gray", width=1, dash="dot"),
		showlegend=False,
	))

	fig.update_layout(
		title=f"{option_type.capitalize()} Payoff at Expiry (K={K}, Premium={premium:.2f})",
		xaxis_title="Underlying Price at Expiry",
		yaxis_title="Profit / Loss",
		hovermode="x unified",
		template="plotly_white",
		showlegend=True,
	)

	return fig.to_json()
