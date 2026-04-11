"""
Risk management module for Rautrex.

Implements Value-at-Risk (VaR), Conditional VaR (expected shortfall),
Monte Carlo VaR, and drawdown analysis — all vectorized via NumPy/Pandas.

VaR Limitations:
    VaR answers "how much can I lose with X% confidence over a given horizon?"
    but has well-known weaknesses:
    (a) It tells you nothing about the *magnitude* of losses beyond the
        threshold — a 95% VaR of $1M says nothing about whether the worst
        5% of cases cost $1.1M or $50M.
    (b) Parametric VaR assumes normality, but real returns exhibit fat tails,
        skewness, and volatility clustering — meaning actual losses can
        far exceed the model's prediction (2008, LTCM, etc.).
    (c) VaR is not a coherent risk measure — it fails sub-additivity, so
        a portfolio's VaR can paradoxically exceed the sum of component VaRs.

Why CVaR / Expected Shortfall is preferred:
    Basel III and FRTB regulations have shifted from VaR to CVaR (Expected
    Shortfall) because it captures the *average* loss in the tail beyond the
    VaR threshold. It is a coherent risk measure (satisfies sub-additivity)
    and penalizes fat-tailed distributions properly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# 1. Historical VaR
# ---------------------------------------------------------------------------
def historical_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    holding_period: int = 1,
) -> float:
    """Compute Value-at-Risk using the historical simulation method.

    Financial intuition:
        Historical VaR makes no distributional assumptions — it simply sorts
        observed returns and picks the cutoff at the (1 - confidence) percentile.
        A 95% VaR of $100 means "on 95% of days, losses did not exceed $100."

        Scaling to a multi-day horizon via sqrt(T) assumes i.i.d. returns,
        which is a simplification — real returns show volatility clustering,
        so this can under-estimate tail risk in stressed periods.

    Limitations:
        - Requires sufficient history to estimate tail accurately
        - Cannot capture risks never before observed
        - Assumes past is representative of future distribution

    Args:
        returns:        Series or array of returns (NOT prices).
        confidence:     Confidence level (0.95 = 95% threshold).
        holding_period: Number of days to scale the VaR to (default 1).

    Returns:
        VaR as a positive number representing potential loss (e.g., 0.025 = 2.5%).
    """
    if isinstance(returns, pd.Series):
        arr = returns.dropna().values
    else:
        arr = np.asarray(returns)

    if len(arr) == 0:
        return np.nan

    var_single = -np.percentile(arr, (1 - confidence) * 100)
    # Scale VaR by sqrt of holding period (square-root-of-time rule)
    var_scaled = var_single * np.sqrt(holding_period)
    return abs(var_scaled)


# ---------------------------------------------------------------------------
# 2. Parametric VaR
# ---------------------------------------------------------------------------
def parametric_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
    holding_period: int = 1,
) -> float:
    """Compute VaR assuming returns follow a normal distribution.

    Financial intuition:
        Parametric (variance-covariance) VaR assumes returns are Gaussian
        and uses only the first two moments (mean, std).  The formula
        VaR = mu - z * sigma tells you the loss threshold on the left tail
        of the fitted normal curve.

    Limitations:
        - Normality assumption is almost always wrong — equity returns have
          fat tails (kurtosis >> 3) and often exhibit negative skew.
          This means parametric VaR *underestimates* tail risk.
        - Ignores all higher moments (skewness, kurtosis).
        - Simple and fast, but should always be compared against historical
          VaR to gauge the impact of the normality assumption.

    Args:
        returns:        Returns series or array.
        confidence:     Confidence level.
        holding_period: Number of days to scale to.

    Returns:
        VaR as a positive number (loss).
    """
    if isinstance(returns, pd.Series):
        arr = returns.dropna().values
    else:
        arr = np.asarray(returns)

    mu = arr.mean()
    sigma = arr.std(ddof=1)

    # z-score for the (1 - confidence) percentile of the standard normal
    z = stats.norm.ppf(1 - confidence)  # negative for confidence > 0.5

    var_single = -(mu + z * sigma)
    var_scaled = var_single * np.sqrt(holding_period)
    return abs(var_scaled)


# ---------------------------------------------------------------------------
# 3. Conditional VaR (CVaR / Expected Shortfall)
# ---------------------------------------------------------------------------
def conditional_var(
    returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
) -> float:
    """Compute CVaR (Expected Shortfall) — the average loss beyond the VaR threshold.

    Financial intuition:
        CVaR answers "if things go bad (worst 5%), *how bad on average*?"
        This is more conservative and informative than VaR, which only tells
        you the cutoff.  For example, VaR says "worst 5% losses start at 2%,"
        while CVaR says "when losses breach 2%, they average 4%."

        Regulators prefer CVaR because:
        (1) It is a coherent risk measure (satisfies sub-additivity).
        (2) It captures tail severity, not just tail threshold.
        (3) It penalizes fat-tailed distributions — portfolios with extreme
            tail events will have higher CVaR even if their VaR looks similar.
        (4) Basel III FRTB (Fundamental Review of the Trading Book) mandates
            CVaR over VaR for market risk capital requirements.

    Args:
        returns:    Returns series or array.
        confidence: Confidence level.

    Returns:
        CVaR as a positive number (average loss in tail).
    """
    if isinstance(returns, pd.Series):
        arr = returns.dropna().values
    else:
        arr = np.asarray(returns)

    if len(arr) == 0:
        return np.nan

    var_threshold = -np.percentile(arr, (1 - confidence) * 100)
    # CVaR = mean of all returns that fall *below* the VaR cutoff
    tail_returns = arr[arr <= -var_threshold]

    if len(tail_returns) == 0:
        return abs(var_threshold)

    cvar = -np.mean(tail_returns)
    return abs(cvar)


# ---------------------------------------------------------------------------
# 4. Monte Carlo VaR
# ---------------------------------------------------------------------------
def monte_carlo_var(
    S0: float,
    mu: float,
    sigma: float,
    T: float = 1,
    n_sims: int = 10_000,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Compute VaR via Monte Carlo simulation of Geometric Brownian Motion.

    Financial intuition:
        Instead of relying on historical data, Monte Carlo VaR simulates
        thousands of possible future price paths using GBM:
            dS = mu * S * dt + sigma * S * dW

        This lets you model hypothetical scenarios for any combination of
        drift (mu) and volatility (sigma), including stress tests that
        never occurred in history.  The downside is that results depend
        entirely on the GBM assumption — same issues with normality and
        no jump component.

    Args:
        S0:         Current asset price.
        mu:         Expected annual return (drift).
        sigma:      Annual volatility.
        T:          Time horizon in years (e.g., 1/252 for one day).
        n_sims:     Number of simulated paths.
        confidence: Confidence level.

    Returns:
        Dict with 'var' (positive loss), 'percentile_price',
        and a 'plot_json' distribution summary for charting.
    """
    # Vectorized GBM terminal price simulation
    # S_T = S0 * exp((mu - 0.5 * sigma^2) * T + sigma * sqrt(T) * Z)
    Z = np.random.standard_normal(n_sims)
    ST = S0 * np.exp((mu - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)

    var_value = S0 - np.percentile(ST, (1 - confidence) * 100)

    # Build a histogram for the distribution plot (JSON serializable)
    hist, bin_edges = np.histogram(ST, bins=50)
    plot_json = {
        "bin_centers": ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist(),
        "counts": hist.tolist(),
        "S0": S0,
        "VaR_percentile": float(np.percentile(ST, (1 - confidence) * 100)),
        "n_sims": n_sims,
    }

    return {
        "var": round(abs(var_value), 6),
        "percentile_price": round(float(np.percentile(ST, (1 - confidence) * 100)), 6),
        "mean_price": round(float(ST.mean()), 6),
        "plot_json": plot_json,
    }


# ---------------------------------------------------------------------------
# 5. Portfolio VaR
# ---------------------------------------------------------------------------
def portfolio_var(
    weights: np.ndarray | list[float],
    returns_df: pd.DataFrame,
    confidence: float = 0.95,
) -> float:
    """Compute portfolio-level Historical VaR from asset weights and returns.

    Financial intuition:
        Portfolio VaR accounts for diversification — the portfolio's risk is
        not the sum of individual VaRs because assets are rarely perfectly
        correlated.  The weighted portfolio return implicitly captures
        cross-asset correlation through the return dataframe.

        However, this still suffers from all Historical VaR limitations:
        - Correlations can spike during crises exactly when you need
          diversification (the "correlation breakdown" problem).
        - Past correlations are not reliable predictors of future ones.

    Args:
        weights:    Array of portfolio weights (must sum to 1).
        returns_df: DataFrame of per-asset daily returns (columns = assets).
        confidence: Confidence level.

    Returns:
        Portfolio VaR as a positive number (loss).
    """
    w = np.asarray(weights)
    # Compute portfolio returns via dot product (vectorized)
    portfolio_returns = returns_df.values @ w
    return historical_var(portfolio_returns, confidence=confidence)


# ---------------------------------------------------------------------------
# 6. Drawdown Analysis
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DrawdownResult:
    """Summary statistics of drawdown analysis."""

    max_drawdown: float       # Worst peak-to-trough loss
    avg_drawdown: float       # Average drawdown (only during underwater periods)
    max_drawdown_duration: int  # Longest drawdown duration in trading days


def drawdown_analysis(equity_curve: pd.Series) -> DrawdownResult:
    """Analyse drawdown characteristics of an equity curve.

    Financial intuition:
        Drawdown analysis reveals the risk profile from the investor's
        perspective — how deep and how long will I be underwater?  Two
        strategies with the same Sharpe ratio can feel dramatically
        different if one has many shallow, short drawdowns while the
        other endures a single prolonged slump.

        Duration matters: a 15% drawdown lasting 2 weeks is very different
        from a 15% drawdown lasting 2 years.  Long drawdowns trigger
        investor redemptions, margin calls, and strategy abandonment.

    Args:
        equity_curve: Series of portfolio values or NAV (NOT returns).

    Returns:
        DrawdownResult with max_drawdown, avg_drawdown, and
        max_drawdown_duration in trading days.
    """
    rolling_peak = equity_curve.cummax()
    drawdown = (equity_curve - rolling_peak) / rolling_peak

    max_dd = float(drawdown.min())
    # Average drawdown: mean of only the negative (underwater) periods
    in_drawdown = drawdown[drawdown < 0]
    avg_dd = float(in_drawdown.mean()) if len(in_drawdown) > 0 else 0.0

    # Longest drawdown duration: count consecutive days below peak
    is_underwater = drawdown < 0
    if not is_underwater.any():
        max_duration = 0
    else:
        # Group consecutive True values and find the max streak
        groups = (~is_underwater).cumsum()[is_underwater]
        max_duration = int(groups.value_counts().max()) if len(groups) > 0 else 0

    return DrawdownResult(
        max_drawdown=max_dd,
        avg_drawdown=avg_dd,
        max_drawdown_duration=max_duration,
    )
