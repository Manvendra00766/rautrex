"""Modern Portfolio Theory engine for Rautrex.

All operations use NumPy/SciPy matrix math — no monte carlo loops.
Inputs (mean_returns, cov_matrix) are expected as NumPy arrays derived
from daily log or simple returns of asset prices.

Annualization conventions:
  - Daily mean returns * 252 = annualized return
  - Daily covariance * 252 = annualized covariance
  - Daily vol * sqrt(252) = annualized vol
"""

from typing import Dict, List, Tuple
import json
import numpy as np
from scipy.optimize import minimize


# =============================================================================
# 1. Portfolio statistics
# =============================================================================

def portfolio_stats(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    rf: float = 0.05,
) -> Tuple[float, float, float]:
    """Return (annualized_return, annualized_volatility, sharpe_ratio).

    Uses vectorized matrix ops — O(n^2) for covariance quadratic form,
    no explicit loops over assets.
    """
    ann_ret = weights @ mean_returns * 252
    ann_vol = np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(252)
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0
    return float(ann_ret), float(ann_vol), float(sharpe)


# =============================================================================
# 2. Efficient frontier
# =============================================================================

def efficient_frontier(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    n_points: int = 100,
) -> List[Tuple[float, float]]:
    """Compute the efficient frontier by solving for minimum-variance portfolios
    at evenly spaced target-returns between the min and max feasible returns.

    Each point comes from a constrained optimization:
      minimize  w^T Σ w
      subject to  w . μ = target_return
                  sum(w)  = 1
                  w_i >= 0  (long-only)
    """
    n_assets = len(mean_returns)
    init_weights = np.ones(n_assets) / n_assets
    bounds = tuple((0, 1) for _ in range(n_assets))
    sum_one = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    # Feasible return range: from min-variance portfolio return to max
    # single-asset return. Using these as the target grid avoids infeasible
    # targets that would cause the optimizer to fail.
    min_var_res = min_variance_portfolio(mean_returns, cov_matrix)
    min_var_ret = np.array(list(min_var_res.values())) @ mean_returns
    max_ret = np.max(mean_returns)
    target_returns = np.linspace(min_var_ret, max_ret, n_points)

    frontier: List[Tuple[float, float]] = []
    for target in target_returns:
        target_constraint = {"type": "eq", "fun": lambda w, t=target: w @ mean_returns - t}
        cons = [sum_one, target_constraint]
        result = minimize(
            lambda w: w @ cov_matrix @ w,
            init_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=cons,
            options={"ftol": 1e-12, "maxiter": 1000},
        )
        if result.success:
            w = result.x
            ann_vol = np.sqrt(w @ cov_matrix @ w) * np.sqrt(252)
            ann_ret = w @ mean_returns * 252
            frontier.append((float(ann_ret), float(ann_vol)))

    return frontier


# =============================================================================
# 3. Max Sharpe portfolio
# =============================================================================

def max_sharpe_portfolio(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    rf: float = 0.05,
) -> Dict[str, float]:
    """Find the tangency portfolio (maximum Sharpe ratio) by minimizing
    the negative Sharpe ratio. The optimizer handles the nonlinearity via
    SLSQP (sequential least squares).

    Returns {"asset_0": weight, ...} with all weights in [0, 1].
    """
    n_assets = len(mean_returns)
    init_weights = np.ones(n_assets) / n_assets
    bounds = tuple((0, 1) for _ in range(n_assets))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    def neg_sharpe(w: np.ndarray) -> float:
        ann_ret = w @ mean_returns * 252
        ann_vol = np.sqrt(w @ cov_matrix @ w) * np.sqrt(252)
        # Negative of Sharpe — we minimize, so this maximizes Sharpe
        return -((ann_ret - rf) / ann_vol) if ann_vol > 0 else 0.0

    result = minimize(
        neg_sharpe,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    weights = result.x if result.success else init_weights
    return {f"asset_{i}": round(float(weights[i]), 6) for i in range(n_assets)}


# =============================================================================
# 4. Minimum variance portfolio
# =============================================================================

def min_variance_portfolio(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> Dict[str, float]:
    """Find the global minimum-variance portfolio (left-most point on the
    efficient frontier). This is the classic Markowitz solution — only the
    covariance matrix matters for the objective; mean returns are irrelevant
    to the optimization but passed for interface consistency.
    """
    n_assets = len(mean_returns)
    init_weights = np.ones(n_assets) / n_assets
    bounds = tuple((0, 1) for _ in range(n_assets))
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    result = minimize(
        lambda w: w @ cov_matrix @ w,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=cons,
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    weights = result.x if result.success else init_weights
    return {f"asset_{i}": round(float(weights[i]), 6) for i in range(n_assets)}


# =============================================================================
# 5. Plotly visualization
# =============================================================================

def plot_efficient_frontier(
    frontier_points: List[Tuple[float, float]],
    portfolios_scatter: List[Dict] | None = None,
) -> str:
    """Build an interactive Plotly chart and return it as JSON.

    frontend_args:
        frontier_points   : [(ann_ret, ann_vol), ...] from efficient_frontier()
        portfolios_scatter: List of dicts with keys (volatility, return, sharpe, label)
                            for random portfolios to overlay as bubble scatter.
    Returns a JSON-serializable string (Plotly figure → json.loads-compatible).
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    # Efficient frontier line (sorted by volatility for a clean curve)
    frontier_sorted = sorted(frontier_points, key=lambda x: x[1])
    vols = [p[1] for p in frontier_sorted]
    rets = [p[0] for p in frontier_sorted]
    fig.add_trace(
        go.Scatter(
            x=vols,
            y=rets,
            mode="lines",
            name="Efficient Frontier",
            line={"color": "gold", "width": 3},
            hovertemplate="Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    # Random portfolio bubbles (if provided)
    if portfolios_scatter:
        p_vols = [p["volatility"] for p in portfolios_scatter]
        p_rets = [p["return"] for p in portfolios_scatter]
        p_sharpes = [p["sharpe"] for p in portfolios_scatter]
        p_labels = [p.get("label", "") for p in portfolios_scatter]

        # Color by Sharpe ratio using a continuous colorscale
        fig.add_trace(
            go.Scatter(
                x=p_vols,
                y=p_rets,
                mode="markers",
                name="Portfolios",
                marker={
                    "size": 8,
                    "color": p_sharpes,
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "Sharpe"},
                },
                text=p_labels,
                hovertemplate="Label: %{text}<br>Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Efficient Frontier",
        xaxis_title="Annualized Volatility (%)",
        yaxis_title="Annualized Return (%)",
        template="plotly_dark",
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )

    # Return as JSON string — the API endpoint sends this directly
    return json.dumps(fig.to_dict())
