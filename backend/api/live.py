"""FastAPI routes for live stock market data.

Endpoints
---------
GET /live/{ticker}/quote
    Returns current/latest quote with price, change, volume

GET /live/{ticker}/intraday?interval=5m&period=1d
    Returns intraday OHLCV data for live charting

GET /live/market/status
    Returns market open/closed status
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from quant.live_data import get_live_quote, get_intraday_data, get_market_status

router = APIRouter(prefix="/live", tags=["live-data"])


@router.get("/{ticker}/quote")
def live_quote(ticker: str):
    """Get current quote for a ticker.
    
    Returns real-time or near real-time price data including:
    - Current/last price
    - Day open, high, low
    - Volume, market cap
    - Price change and % change from previous close
    - Market state (REGULAR, PRE, POST, CLOSED)
    
    Note: Data may have 15-20 min delay for free tier.
    For true real-time, integrate Alpha Vantage or Polygon.io.
    """
    result = get_live_quote(ticker.upper())
    
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch live quote for {ticker}: {result['error']}"
        )
    
    return result


@router.get("/{ticker}/intraday")
def intraday_chart(
    ticker: str,
    interval: str = Query(default="5m", description="1m, 2m, 5m, 15m, 30m, 60m, 1h"),
    period: str = Query(default="1d", description="1d, 5d, 1mo"),
):
    """Get intraday data for live charting.
    
    Returns minute-level or hourly OHLCV data for the current/recent trading day.
    Perfect for displaying live price charts with automatic refresh.
    
    Intervals:
    - 1m, 2m: Last 7 days max
    - 5m, 15m, 30m: Last 60 days max
    - 60m, 1h: Last 730 days max
    """
    result = get_intraday_data(ticker.upper(), interval, period)
    
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch intraday data: {result['error']}"
        )
    
    return result


@router.get("/market/status")
def market_status():
    """Check if US stock market is currently open.
    
    Returns market state:
    - REGULAR: Market is open for trading
    - PRE: Pre-market hours
    - POST: After-hours trading
    - CLOSED: Market is closed
    """
    return get_market_status()
