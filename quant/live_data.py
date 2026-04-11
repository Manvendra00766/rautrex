"""Live stock market data integration for Rautrex.

Fetches real-time/near real-time quotes from free APIs.
Uses yfinance for live quotes (15-20 min delay) or can integrate
with Alpha Vantage, Finnhub for real-time data.
"""

from datetime import datetime
from typing import Dict, Optional
import yfinance as yf


def get_live_quote(ticker: str) -> Dict:
    """Fetch current/latest quote for a ticker.
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dict with current price, change, volume, market cap, etc.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get latest price from fast_info (faster than full info)
        try:
            current_price = stock.fast_info.last_price
        except:
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        # Get intraday data for latest available
        hist = stock.history(period="1d", interval="1m")
        latest_candle = hist.iloc[-1] if not hist.empty else None
        
        return {
            "ticker": ticker,
            "current_price": float(current_price) if current_price else None,
            "open": float(info.get('regularMarketOpen', 0)) if info.get('regularMarketOpen') else None,
            "high": float(info.get('dayHigh', 0)) if info.get('dayHigh') else None,
            "low": float(info.get('dayLow', 0)) if info.get('dayLow') else None,
            "previous_close": float(info.get('previousClose', 0)) if info.get('previousClose') else None,
            "volume": int(info.get('volume', 0)) if info.get('volume') else None,
            "market_cap": info.get('marketCap'),
            "change": float(current_price - info.get('previousClose', 0)) if current_price and info.get('previousClose') else None,
            "change_percent": float(((current_price - info.get('previousClose', 0)) / info.get('previousClose', 1)) * 100) if current_price and info.get('previousClose') else None,
            "timestamp": datetime.now().isoformat(),
            "market_state": info.get('marketState', 'UNKNOWN'),  # REGULAR, PRE, POST, CLOSED
            "last_updated": latest_candle.name.isoformat() if latest_candle is not None else None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_intraday_data(ticker: str, interval: str = "5m", period: str = "1d") -> Dict:
    """Fetch intraday data for live charting.
    
    Args:
        ticker: Stock symbol
        interval: Data interval - 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h
        period: Time period - 1d, 5d, 1mo
        
    Returns:
        Dict with intraday OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        
        if hist.empty:
            return {
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "records": [],
                "message": "No intraday data available"
            }
        
        # Clean and format data
        hist.reset_index(inplace=True)
        
        # Handle both Datetime and Date columns
        date_col = 'Datetime' if 'Datetime' in hist.columns else 'Date'
        hist[date_col] = hist[date_col].astype(str)
        
        records = hist.rename(columns={
            date_col: 'datetime',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })[['datetime', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')
        
        return {
            "ticker": ticker,
            "interval": interval,
            "period": period,
            "records": records,
            "count": len(records),
            "latest_price": float(hist['Close'].iloc[-1]) if not hist.empty else None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_market_status() -> Dict:
    """Check if US markets are currently open.
    
    Returns:
        Dict with market status information
    """
    try:
        # Use SPY as proxy for market hours
        spy = yf.Ticker("SPY")
        info = spy.info
        
        return {
            "is_open": info.get('marketState') == 'REGULAR',
            "market_state": info.get('marketState', 'UNKNOWN'),
            "exchange_timezone": info.get('exchangeTimezoneName', 'America/New_York'),
            "timestamp": datetime.now().isoformat(),
        }
    except:
        return {
            "is_open": False,
            "market_state": "UNKNOWN",
            "timestamp": datetime.now().isoformat(),
        }
