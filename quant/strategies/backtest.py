"""Modular backtesting engine for Rautrex.

Provides a Strategy base class, three concrete strategies, and a
vectorized Backtester that computes performance metrics and produces
interactive plots.

Look-ahead bias warning
-----------------------
Signals must be *lagged* by one period so that a signal generated from
today's price is only applied to *tomorrow's* return.  Using the
contemporaneous signal (signal_t * return_t) is look-ahead bias: the
model would "know" today's price movement before generating the signal,
which inflates performance unrealistically.  In the ``Backtester.run()``
method, ``signals.shift(1)`` enforces this discipline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# =============================================================================
# Base strategy
# =============================================================================


class Strategy(ABC):
    """Abstract base for all trading strategies.

    Subclasses implement ``generate_signals()`` which maps a price series
    to a signal series of 1 (long), -1 (short), or 0 (flat).
    """

    @abstractmethod
    def generate_signals(self, prices: pd.Series) -> pd.Series:
        """Return a Series of trading signals aligned with *prices* index.

        IMPORTANT:  The signals returned here represent what the strategy
        *decides* at each bar.  The ``Backtester`` will shift them forward
        by one period before applying to returns, so the signal at index t
        is applied to the return from t to t+1.
        """


# =============================================================================
# Momentum
# =============================================================================


class MomentumStrategy(Strategy):
    """Channel-breakout momentum strategy.

    Goes long when price makes a new rolling-maximum high, short on a
    new rolling-minimum low, flat otherwise.  Captures trend-following
    behavior without MA lag.
    """

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        roll_max = prices.rolling(self.lookback).max()
        roll_min = prices.rolling(self.lookback).min()

        signals = pd.Series(0, index=prices.index, dtype=float)
        signals[prices > roll_max] = 1.0
        signals[prices < roll_min] = -1.0
        return signals


# =============================================================================
# Mean reversion
# =============================================================================


class MeanReversionStrategy(Strategy):
    """Z-score mean-reversion strategy.

    Sells when the price is z_threshold std deviations *above* the rolling
    mean (expecting it to fall back), buys when it is z_threshold std
    deviations *below* the mean.
    """

    def __init__(self, window: int = 20, z_threshold: float = 1.5):
        self.window = window
        self.z_threshold = z_threshold

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        roll_mean = prices.rolling(self.window).mean()
        roll_std = prices.rolling(self.window).std()
        z_score = (prices - roll_mean) / roll_std

        signals = pd.Series(0, index=prices.index, dtype=float)
        signals[z_score > self.z_threshold] = 1.0   # sell / short
        signals[z_score < -self.z_threshold] = -1.0  # buy
        return signals


# =============================================================================
# Moving Average Crossover
# =============================================================================


class MovingAverageCrossover(Strategy):
    """Signal fires on fast/slow MA crossover.

    Generates 1 when the fast MA crosses *above* the slow MA (golden cross)
    and -1 when it crosses *below* (death cross).  Between crossovers
    the signal stays flat.
    """

    def __init__(self, fast: int = 10, slow: int = 50):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        fast_ma = prices.rolling(self.fast).mean()
        slow_ma = prices.rolling(self.slow).mean()

        # Crossover detection: today fast>slow AND yesterday fast<=slow  →  +1
        # Crossunder: today fast<slow AND yesterday fast>=slow            →  -1
        diff = fast_ma - slow_ma
        prev_diff = diff.shift(1)

        signals = pd.Series(0, index=prices.index, dtype=float)
        signals[(diff > 0) & (prev_diff <= 0)] = 1.0
        signals[(diff < 0) & (prev_diff >= 0)] = -1.0
        return signals


# =============================================================================
# Strategy registry
# =============================================================================

STRATEGIES: dict[str, type[Strategy]] = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "ma_cross": MovingAverageCrossover,
}


# =============================================================================
# Backtester
# =============================================================================


@dataclass
class BacktestResult:
    """Container for backtest outputs."""

    equity_curve: pd.Series
    daily_returns: pd.Series
    total_return: float
    annualized_sharpe: float
    max_drawdown: float
    win_rate: float
    calmar_ratio: float
    plot_json: Optional[dict] = None


class Backtester:
    """Vectorized backtester with transaction cost modeling.

    Strategy returns are computed as:
        strategy_return_t = signal_{t-1} * price_return_t

    The one-period lag prevents look-ahead bias — we can only trade on
    signals generated *before* we observe the return.  Transaction costs
    are applied only when the signal changes (i.e. a trade occurs).
    """

    def __init__(self, transaction_cost: float = 0.001):
        """
        Args:
            transaction_cost: Proportional cost per trade (e.g. 0.001 = 10 bps).
                This covers commissions, slippage, and market impact
                at a high level.  Realistic values range from 1bp (liquid
                equities) to 50bp+ (thinly traded assets).
        """
        self.transaction_cost = transaction_cost

    @staticmethod
    def run(
        prices: pd.Series,
        signals: pd.Series,
        transaction_cost: float = 0.001,
    ) -> BacktestResult:
        """Execute backtest and return performance metrics + equity curve.

        Args:
            prices: Close-price series indexed by date.
            signals: Signal series from a Strategy.generate_signals().
                Will be lagged by 1 period internally.
            transaction_cost: Proportional cost per trade.

        Returns:
            BacktestResult with equity_curve, metrics, and optionally
            a Plotly figure serialized to JSON.
        """
        # --- Lag signals to prevent look-ahead bias ---------------------------
        # signal_t-1 means we hold the position decided *before* today's close.
        # Using signal_t directly would let the signal "see" today's return,
        # which is impossible in real trading.
        lagged_signals = signals.shift(1)

        price_returns = prices.pct_change()

        # Strategy returns: position * market return
        strategy_returns = lagged_signals * price_returns

        # Transaction cost: charged when position changes (|signal_t - signal_{t-1}| > 0)
        trade_flag = lagged_signals.diff().abs()
        costs = trade_flag * transaction_cost
        strategy_returns = strategy_returns - costs

        strategy_returns.dropna(inplace=True)

        # --- Equity curve ------------------------------------------------------
        equity = (1 + strategy_returns).cumprod()

        # --- Metrics -----------------------------------------------------------
        total_return = float(equity.iloc[-1] - 1) if len(equity) > 0 else 0.0

        n_years = len(strategy_returns) / 252
        ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
        ann_sharpe = (
            float(strategy_returns.mean() / strategy_returns.std() * np.sqrt(252))
            if strategy_returns.std() > 0
            else 0.0
        )

        # Max drawdown
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0

        # Calmar ratio
        calmar = (ann_return / abs(max_dd) if abs(max_dd) > 0 else 0.0)

        # Win rate (% of trading days with positive return)
        win_rate = float((strategy_returns > 0).sum() / len(strategy_returns)) if len(strategy_returns) > 0 else 0.0

        return BacktestResult(
            equity_curve=equity,
            daily_returns=strategy_returns,
            total_return=total_return,
            annualized_sharpe=ann_sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            calmar_ratio=calmar,
        )

    @staticmethod
    def plot_results(result: BacktestResult) -> dict:
        """Generate a Plotly figure with equity curve and drawdown subplots.

        Returns:
            JSON-serializable dict (use `fig.to_json()` or pass directly
            to Plotly.js on the frontend).
        """
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=("Equity Curve", "Drawdown"),
        )

        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=result.equity_curve.index.astype(str),
                y=result.equity_curve.values,
                name="Equity",
                line=dict(color="#2196F3"),
                fill="tozeroy",
            ),
            row=1,
            col=1,
        )

        # Drawdown
        running_max = result.equity_curve.cummax()
        drawdown = (result.equity_curve - running_max) / running_max
        fig.add_trace(
            go.Scatter(
                x=drawdown.index.astype(str),
                y=drawdown.values,
                name="Drawdown",
                line=dict(color="#F44336"),
                fill="tozeroy",
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=600,
            template="plotly_white",
            showlegend=False,
            margin=dict(l=50, r=20, t=40, b=30),
        )

        import json
        return json.loads(fig.to_json())
