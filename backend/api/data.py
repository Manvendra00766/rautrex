"""FastAPI routes for market data ingestion and summary analytics.

Endpoints
---------
GET /data/{ticker}?start=&end=&interval=
    Fetches, stores, and returns OHLCV data for the given ticker.

GET /data/{ticker}/summary
    Returns summary return statistics computed from cached data.
"""

from datetime import datetime
import math

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from quant.data_collector import DEFAULT_DB_URL, get_engine, ingest, summary_stats

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/{ticker}")
def fetch_ticker(
    ticker: str,
    start: str = Query(default="2020-01-01", description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    interval: str = Query(default="1d", description="Bar interval"),
):
    """Fetch OHLCV data from Yahoo Finance, store in DB, return as JSON."""
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    try:
        df = ingest(
            ticker=ticker,
            start_date=start,
            end_date=end,
            interval=interval,
            db_url=DEFAULT_DB_URL,
        )
    except Exception as exc:
        # Return graceful error response instead of raising
        return {
            "success": False,
            "ticker": ticker,
            "error": "Failed to fetch data",
            "details": str(exc),
            "records": [],
            "count": 0,
        }

    if df.empty:
        return {
            "success": True,
            "ticker": ticker,
            "records": [],
            "count": 0,
            "message": "No data found for this ticker",
        }

    def _clean_value(value):
        try:
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return None
        except TypeError:
            pass
        return value

    records = [{k: _clean_value(v) for k, v in row.items()} for row in df.to_dict(orient="records")]
    return {
        "success": True,
        "ticker": ticker,
        "records": records,
        "count": len(records),
    }


@router.get("/{ticker}/summary")
def ticker_summary(ticker: str):
    """Return summary return statistics for *ticker*.

    The Sharpe estimate assumes 252 trading days per year and a
    risk-free rate of 0 (consistent with current low-rate environments
    for simplicity).  To adjust for a different risk-free rate, subtract
    ``rf_daily / 252`` from the mean in the ``sharpe_estimate`` calc.
    """
    engine = get_engine(DEFAULT_DB_URL)
    stats = summary_stats(engine, ticker)

    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No cached data found for ticker '{ticker}'. "
                   "Fetch data first via GET /data/{ticker}.",
        )

    return stats
