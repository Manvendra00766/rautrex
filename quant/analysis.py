"""
Time-series analytics engine for Rautrex.

Provides vectorized financial metric computations using NumPy/Pandas.
All functions are designed to be stateless and pure — inputs in, outputs out.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Rolling Volatility
# ---------------------------------------------------------------------------
def rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """Compute annualized rolling volatility over a given window.

    Financial intuition:
        Volatility measures the dispersion of returns around their mean and
        serves as the most common proxy for risk. By computing it over a
        rolling window, we capture how risk evolves over time — periods of
        high volatility often coincide with market stress, while low
        volatility regimes tend to be calmer.  Annualizing via sqrt(252)
        allows comparison across different sampling frequencies (daily
        returns → annualised figure), assuming i.i.d. returns.

    Args:
        returns: Daily returns (e.g., pct_change or log returns).
        window:  Rolling look-back window in trading days (default 20 ≈ 1 month).

    Returns:
        pandas Series of annualized volatility values.
    """
    return returns.rolling(window=window).std() * np.sqrt(252)


# ---------------------------------------------------------------------------
# 2. Historical Correlation
# ---------------------------------------------------------------------------
def historical_correlation(df_returns: pd.DataFrame) -> pd.DataFrame:
    """Compute the historical pairwise correlation of multiple assets' returns.

    Financial intuition:
        Correlation quantifies how asset prices move together.  A high
        positive correlation between two tickers suggests they respond to
        similar risk factors (e.g., two tech stocks during a rate-hike cycle).
        Correlation is the backbone of portfolio diversification — holding
        uncorrelated or negatively correlated assets reduces overall portfolio
        variance without necessarily sacrificing expected return.

    Args:
        df_returns: DataFrame where each column is a ticker's returns series.

    Returns:
        Correlation matrix as a DataFrame.
    """
    return df_returns.corr()


# ---------------------------------------------------------------------------
# 3. Beta
# ---------------------------------------------------------------------------
def compute_beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate the beta of an asset relative to the market.

    Financial intuition:
        Beta measures systematic (non-diversifiable) risk — how much an asset
        amplifies or dampens market movements.  A beta of 1.5 means the asset
        tends to move 50% more than the market (magnifies both gains and
        losses), while a beta of 0.5 implies half the sensitivity.  Beta is
        central to the CAPM framework and is used to determine the
        risk-adjusted expected return of an asset:  E[R] = Rf + beta * (E[Rm] - Rf).

    Args:
        asset_returns:   Returns of the specific asset.
        market_returns:  Returns of the benchmark (e.g., S&P 500).

    Returns:
        Beta coefficient as a float.
    """
    covariance = np.cov(asset_returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    return covariance / market_variance if market_variance != 0 else np.nan


# ---------------------------------------------------------------------------
# 4. Sharpe Ratio
# ---------------------------------------------------------------------------
def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """Compute the annualized Sharpe ratio.

    Financial intuition:
        The Sharpe ratio tells you how much excess return you earned per
        unit of risk taken.  It normalises return by volatility, so a
        high-return strategy with sky-high volatility might actually have a
        lower Sharpe than a boring, steady strategy.  Industry convention:
        >1.0 is acceptable, >2.0 is strong, >3.0 is exceptional (though
        suspicious — check for overfitting or look-ahead bias).

    Args:
        returns:          Daily returns series.
        risk_free_rate:   Annualised risk-free rate (default 5%).

    Returns:
        Annualized Sharpe ratio as a float.
    """
    mean_daily = returns.mean()
    std_daily = returns.std()
    if std_daily == 0:
        return np.nan
    annualized_return = mean_daily * 252
    annualized_vol = std_daily * np.sqrt(252)
    return (annualized_return - risk_free_rate) / annualized_vol


# ---------------------------------------------------------------------------
# 5. Maximum Drawdown
# ---------------------------------------------------------------------------
def max_drawdown(price_series: pd.Series) -> float:
    """Compute the maximum peak-to-trough drawdown from a price series.

    Financial intuition:
        Max drawdown represents the worst cumulative loss an investor would
        have experienced holding the asset from any peak to the subsequent
        trough.  Unlike volatility, it captures one-sided downside risk —
        the "pain" metric that actually matters to real investors.  A
        strategy with 30% max drawdown needs a 43% gain just to get back
        to even, which is why drawdown control is critical for capital
        preservation.

    Args:
        price_series: Series of raw prices (NOT returns).

    Returns:
        Maximum drawdown as a negative float (e.g., -0.35 means 35% loss).
    """
    rolling_peak = price_series.cummax()
    drawdown = (price_series - rolling_peak) / rolling_peak
    return drawdown.min()


# ---------------------------------------------------------------------------
# 6. Autocorrelation Test
# ---------------------------------------------------------------------------
def autocorrelation_test(returns: pd.Series, lags: int = 10) -> pd.Series:
    """Compute autocorrelation of returns at multiple lag values.

    Financial intuition:
        Autocorrelation detects serial dependence in returns.  In an
        efficient market, daily returns should be essentially uncorrelated
        (random walk).  Significant positive autocorrelation may indicate
        momentum or trend-following behavior, while negative autocorrelation
        suggests mean reversion.  This test is also useful for spotting
        microstructure noise in high-frequency data or illiquidity effects
        (stale prices creating artificial smoothing).

        As a rule of thumb, |autocorr| > 2/sqrt(N) may be statistically
        significant at the 5% level.

    Args:
        returns: Returns series.
        lags:    Maximum number of lags to compute (1..lags inclusive).

    Returns:
        Series of autocorrelation values indexed by lag.
    """
    results = {}
    for lag in range(1, lags + 1):
        results[lag] = returns.autocorr(lag=lag)
    return pd.Series(results, name="autocorrelation")
