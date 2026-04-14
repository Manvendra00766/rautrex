"""Portfolio metrics calculation service using real market data."""
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger("rautrex")


def fetch_price_data(ticker: str, period: str = "1y") -> pd.Series:
    """Fetch historical price data for a ticker using yfinance.
    
    Args:
        ticker: Stock ticker (e.g., "AAPL", "MSFT", "BTC-USD")
        period: Period for historical data (e.g., "1y", "6mo", "1d")
        
    Returns:
        pd.Series: Close prices indexed by date
        
    Raises:
        ValueError: If ticker is invalid or data cannot be fetched
    """
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if data.empty:
            raise ValueError(f"No data found for ticker {ticker}")
        
        # Get Close prices
        close_prices = data["Close"]
        
        # If it's a DataFrame (multi-index case), convert to Series
        if isinstance(close_prices, pd.DataFrame):
            # Single ticker returns DataFrame with ticker column
            close_prices = close_prices.iloc[:, 0] if len(close_prices.columns) > 0 else close_prices.squeeze()
        
        # Ensure we have a Series, not a scalar
        if isinstance(close_prices, (int, float)):
            raise ValueError(f"Insufficient data for ticker {ticker}")
        
        # Ensure we have at least 10 data points for calculations
        if len(close_prices) < 10:
            raise ValueError(f"Insufficient historical data for ticker {ticker}")
        
        return close_prices
    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
        raise ValueError(f"Invalid ticker or data fetch error: {ticker}")


def calculate_log_returns(prices: pd.Series) -> np.ndarray:
    """Calculate log returns from price series.
    
    Args:
        prices: pd.Series of prices
        
    Returns:
        np.ndarray: Array of log returns
    """
    return np.diff(np.log(prices.values))


def calculate_volatility(returns: np.ndarray) -> float:
    """Calculate annualized volatility from returns.
    
    Args:
        returns: np.ndarray of returns
        
    Returns:
        float: Annualized volatility (std * sqrt(252))
    """
    return float(np.std(returns, ddof=1) * np.sqrt(252))


def calculate_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Calculate Value at Risk using percentile method.
    
    Args:
        returns: np.ndarray of returns
        confidence: Confidence level (default 0.95 for 95% VaR)
        
    Returns:
        float: Daily VaR (as percentage)
    """
    var = np.percentile(returns, (1 - confidence) * 100)
    return float(var)


def calculate_cumulative_returns(returns: np.ndarray) -> float:
    """Calculate total return from returns array.
    
    Args:
        returns: np.ndarray of log returns
        
    Returns:
        float: Total cumulative return (as percentage)
    """
    return float((np.exp(np.sum(returns)) - 1) * 100)


def calculate_portfolio_metrics(
    assets: list[dict],
    period: str = "1y"
) -> dict:
    """Calculate comprehensive portfolio metrics from real market data.
    
    Args:
        assets: List of {ticker, amount_invested} dicts
        period: Historical period for calculations
        
    Returns:
        dict: {
            total_value,
            daily_pnl,
            returns,
            volatility,
            var_95,
            asset_breakdown,
            price_series,
            correlation_matrix
        }
    """
    if not assets or len(assets) == 0:
        raise ValueError("Portfolio must contain at least one asset")
    
    # Calculate total invested and weights from amounts
    total_invested = sum(asset["amount_invested"] for asset in assets)
    if total_invested <= 0:
        raise ValueError("Total investment must be positive")
    
    # Fetch price data for all assets
    price_data = {}
    weights = {}
    amounts = {}
    
    for asset in assets:
        ticker = asset["ticker"]
        amount = asset["amount_invested"]
        weight = amount / total_invested  # Calculate weight from amount
        
        try:
            prices = fetch_price_data(ticker, period)
            price_data[ticker] = prices
            weights[ticker] = weight
            amounts[ticker] = amount
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {str(e)}")
            raise ValueError(f"Failed to fetch data for {ticker}")
    
    # Align all price series to same dates
    try:
        df_prices = pd.DataFrame({t: price_data[t] for t in price_data.keys()})
    except ValueError as e:
        if "scalar" in str(e):
            raise ValueError("Insufficient historical data for one or more assets")
        raise
    
    df_prices.dropna(inplace=True)
    
    if df_prices.empty or len(df_prices) < 10:
        raise ValueError("Insufficient valid price data available (need at least 10 trading days)")
    
    # Calculate returns for each asset
    returns_data = {}
    for ticker in df_prices.columns:
        returns_data[ticker] = calculate_log_returns(df_prices[ticker])
    
    # Calculate portfolio returns (weighted average)
    portfolio_returns = np.zeros(len(returns_data[list(returns_data.keys())[0]]))
    for ticker, returns in returns_data.items():
        portfolio_returns += returns * weights[ticker]
    
    # Calculate metrics
    volatility = calculate_volatility(portfolio_returns)
    var_95 = calculate_var(portfolio_returns, confidence=0.95)
    cumulative_return = calculate_cumulative_returns(portfolio_returns)
    
    # Calculate current portfolio value
    latest_prices = df_prices.iloc[-1]
    daily_return = portfolio_returns[-1] if len(portfolio_returns) > 0 else 0.0
    current_value = total_invested * np.exp(np.sum(portfolio_returns))
    daily_pnl = current_value - (total_invested * np.exp(np.sum(portfolio_returns[:-1])))
    
    # Asset breakdown (using actual invested amounts)
    asset_breakdown = []
    for ticker in df_prices.columns:
        price = latest_prices[ticker]
        amount = amounts[ticker]
        quantity = amount / price  # Calculate quantity from amount and current price
        value = quantity * price
        asset_breakdown.append({
            "ticker": ticker,
            "amount_invested": float(amount),
            "weight": float(weights[ticker]),
            "price": float(price),
            "quantity": float(quantity),
            "value": float(value),
        })
    
    # Price series for charts (normalized to 100)
    price_series = {}
    for ticker in df_prices.columns:
        normalized = (df_prices[ticker] / df_prices[ticker].iloc[0]) * 100
        price_series[ticker] = [
            {"date": str(date.date()), "price": float(p)}
            for date, p in normalized.items()
        ]
    
    # Portfolio price series
    portfolio_values = []
    for i in range(len(df_prices)):
        pv = total_invested * np.exp(np.sum(portfolio_returns[:i]))
        portfolio_values.append({
            "date": str(df_prices.index[i].date()),
            "value": float(pv)
        })
    
    # Correlation matrix
    correlation_returns = pd.DataFrame(returns_data)
    correlation_matrix = correlation_returns.corr().to_dict()
    
    return {
        "total_invested": float(total_invested),
        "total_value": float(current_value),
        "daily_pnl": float(daily_pnl),
        "daily_pnl_pct": float(daily_return * 100),
        "cumulative_return": float(cumulative_return),
        "volatility": float(volatility),
        "var_95": float(var_95),
        "asset_breakdown": asset_breakdown,
        "price_series": price_series,
        "portfolio_values": portfolio_values,
        "correlation_matrix": correlation_matrix,
    }
