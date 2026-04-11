"""Stochastic process simulations for Rautrex.

Vectorized simulation of random walks, Brownian motion,
and Geometric Brownian Motion using NumPy broadcasting.
"""

from typing import Any

import numpy as np
import plotly.graph_objects as go


def random_walk(n_steps: int, seed: int | None = None) -> np.ndarray:
    """Cumulative sum of standard normal draws.

    Args:
        n_steps: Number of steps in the walk.
        seed: Random seed for reproducibility.

    Returns:
        np.ndarray of shape (n_steps,): cumulative path values.
    """
    rng = np.random.default_rng(seed)
    draws = rng.standard_normal(n_steps)
    return np.cumsum(draws)


def brownian_motion(
    T: float, n_steps: int, sigma: float = 1.0, seed: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate a single Brownian motion path.

    W_t = sigma * sqrt(dt) * cumsum(Z)

    Args:
        T: Time horizon.
        n_steps: Number of discrete time steps.
        sigma: Volatility / diffusion coefficient.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (time_array, path_array), each of shape (n_steps+1,).
        Time array starts at 0; path starts at 0.
    """
    dt = T / n_steps
    rng = np.random.default_rng(seed)
    increments = rng.standard_normal(n_steps)
    path = np.empty(n_steps + 1)
    path[0] = 0.0
    path[1:] = sigma * np.sqrt(dt) * np.cumsum(increments)
    time = np.linspace(0, T, n_steps + 1)
    return time, path


def geometric_brownian_motion(
    S0: float,
    mu: float,
    sigma: float,
    T: float,
    n_steps: int,
    n_sims: int = 1000,
    seed: int | None = None,
) -> np.ndarray:
    """Simulate Geometric Brownian Motion paths.

    GBM is the standard model for stock prices in quantitative finance
    (Black-Scholes-Merton framework underpins it for a reason):

    1. **Log-normal prices** — S_t cannot go negative, matching limited
       liability of equity holders.
    2. **Independent stationary returns** — log returns over non-overlapping
       intervals are i.i.d. normal, consistent with efficient market intuition.
    3. **Analytical tractability** — closed-form density enables option pricing,
       risk metrics, and portfolio simulation without numerical integration.
    4. **Markov property** — the current price contains all information needed
       to forecast the distribution of future prices.

    Process: S_t = S0 * exp((mu - 0.5*sigma²)*t + sigma*W_t)

    Args:
        S0: Initial price.
        mu: Drift (expected annualized return).
        sigma: Volatility (annualized).
        T: Time horizon in years.
        n_steps: Number of discrete time steps.
        n_sims: Number of independent simulation paths.
        seed: Random seed for reproducibility.

    Returns:
        np.ndarray of shape (n_sims, n_steps+1). Each row is one simulated
        price path. Column 0 equals S0 for all rows.
    """
    dt = T / n_steps
    t = np.linspace(0, T, n_steps + 1)  # (n_steps+1,)

    rng = np.random.default_rng(seed)
    # Shape: (n_sims, n_steps)
    Z = rng.standard_normal((n_sims, n_steps))

    # W_t via cumsum along time axis → (n_sims, n_steps)
    W = np.cumsum(Z, axis=1) * np.sqrt(dt)

    # Prepend W_0 = 0 for each path → (n_sims, n_steps+1)
    W = np.hstack([np.zeros((n_sims, 1)), W])

    # Broadcast: t is (n_steps+1,), mu/sigma scalars, result (n_sims, n_steps+1)
    drift = (mu - 0.5 * sigma**2) * t  # (n_steps+1,)
    diffusion = sigma * W  # (n_sims, n_steps+1)
    paths = S0 * np.exp(drift + diffusion)

    return paths


def plot_simulations(paths: np.ndarray, title: str, time: np.ndarray | None = None, color: str = "rgba(100, 180, 255, 0.4)") -> dict[str, Any]:
    """Plot simulation paths as an interactive Plotly figure.

    Args:
        paths: Array of paths, shape (n_paths, n_steps) or (n_steps,).
        title: Figure title.
        time: Optional time axis. Falls back to index positions if None.

    Returns:
        JSON-serializable dict from fig.to_json().
    """
    fig = go.Figure()

    if paths.ndim == 1:
        paths = paths[np.newaxis, :]

    t = time if time is not None else np.arange(paths.shape[1])

    for i in range(paths.shape[0]):
        fig.add_trace(go.Scatter(
            x=t, y=paths[i],
            mode="lines",
            line=dict(width=1, color=color),
            showlegend=False,
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Value",
        template="plotly_white",
        hovermode="x unified",
    )

    return fig.to_json()
