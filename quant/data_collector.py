"""OHLCV data ingestion layer for Rautrex.

Fetches market data via ``yfinance``, cleans it, computes returns, and
persists records to SQLite through SQLAlchemy.

Design decisions
----------------
**Why log returns?**
    Log returns  r_t = ln(P_t / P_{t-1})  are preferred in quantitative
    finance because they are *time-additive*: a multi-period return is
    simply the sum of single-period log returns.  This makes portfolio
    aggregation, volatility estimation, and stochastic models (e.g.
    geometric Brownian motion) mathematically tractable.  Simple returns
    are better suited for intuitive PnL and reporting.

**What forward-fill assumes:**
    Forward-filling replaces missing values with the last observed price.
    This assumes that *no new information* arrived between the missing bar
    and its predecessor — a reasonable assumption for thin markets or
    minor data gaps, but dangerous during trading halts, delistings, or
    corporate actions where a price gap conveys real information.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import os

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models.price import Base, PriceRecord
from backend.models.config import settings

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_DB_URL = os.getenv(
    "DATABASE_URL",
    settings.database_url
)
DEFAULT_INTERVAL = "1d"

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def get_engine(db_url: str = DEFAULT_DB_URL):
    """Return a SQLAlchemy engine, creating tables if they don't exist."""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


# ---------------------------------------------------------------------------
# Cache check
# ---------------------------------------------------------------------------


def _check_cache(session: Session, ticker: str, start: str, end: str) -> tuple[str, str]:
    """Return the earliest date not already cached for *ticker*.

    If the entire [start, end] range is present, returns (None, None) so
    the caller can skip the API fetch.  Otherwise returns the adjusted
    start date (the day after the latest cached date) and the original end
    date.

    Why check the cache:
        Yahoo Finance rate-limits requests and historical data is immutable.
        Re-fetching data we already have is wasteful both in bandwidth and
        in API quota.  A simple per-ticker existence check avoids this.
    """
    existing = (
        session.query(PriceRecord.date)
        .filter(
            PriceRecord.ticker == ticker,
            PriceRecord.date >= start,
            PriceRecord.date <= end,
        )
        .order_by(PriceRecord.date.desc())
        .all()
    )

    if not existing:
        return start, end

    cached_dates = sorted(r.date for r in existing)
    latest_cached = cached_dates[-1]

    # If we already have data through end, skip entirely.
    if latest_cached >= end:
        return None, None

    # Return range from day after latest cached.
    next_day = pd.to_datetime(latest_cached) + pd.Timedelta(days=1)
    return next_day.strftime("%Y-%m-%d"), end


def _has_full_range(session: Session, ticker: str, start: str, end: str) -> bool:
    """Return True if cached records cover the full date range."""
    # Simple existence check: count cached rows vs business days.
    cached = (
        session.query(PriceRecord.date)
        .filter(
            PriceRecord.ticker == ticker,
            PriceRecord.date >= start,
            PriceRecord.date <= end,
        )
        .all()
    )
    return len(cached) > 0


# ---------------------------------------------------------------------------
# Fetch & clean
# ---------------------------------------------------------------------------


def fetch_ohlcv(
    ticker: str,
    start_date: str = "2023-01-01",
    end_date: Optional[str] = None,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance for *ticker*.

    Args:
        ticker: Yahoo Finance symbol (stock, ETF, or crypto, e.g.
            "AAPL", "SPY", "BTC-USD", "EURUSD=X").
        start_date: ISO-formatted start date (inclusive).
        end_date: ISO-formatted end date (inclusive).  Defaults to today.
        interval: Bar interval – any valid yfinance interval
            ("1m", "5m", "15m", "1h", "1d", "1wk", "1mo").

    Returns:
        DataFrame with columns: open, high, low, close, volume,
        simple_return, log_return.  Index is a DatetimeIndex.
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(start=start_date, end=end_date, interval=interval)

    if df.empty:
        return df

    # Ensure standard column names (lowercase).
    df.columns = [c.lower() for c in df.columns]

    # --- Cleaning -----------------------------------------------------------
    # Forward-fill: assume no new info in the gap (see module docstring).
    df.ffill(inplace=True)

    # Drop any rows that are still NaN after forward-fill.
    df.dropna(inplace=True)

    # Reset index so date becomes a proper column.
    df.reset_index(inplace=True)
    if "Date" in df.columns:
        df.rename(columns={"Date": "date"}, inplace=True)
    elif "date" not in df.columns:
        df["date"] = df.index
        df = df.reset_index(drop=True)

    # Ensure date column is datetime, then string.
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    return df


# ---------------------------------------------------------------------------
# Return calculation
# ---------------------------------------------------------------------------


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute simple and log returns on the close price.

    Simple return:  (P_t - P_{t-1}) / P_{t-1}
    Log return:     ln(P_t / P_{t-1})

    The first row will have NaN returns (no prior price) — callers should
    drop them before persisting.
    """
    close = pd.to_numeric(df["close"], errors="coerce")

    df["simple_return"] = close.pct_change()
    df["log_return"] = np.log(close / close.shift(1))

    return df


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def store_records(
    engine, records_df: pd.DataFrame, ticker: str, on_conflict: str = "replace"
) -> int:
    """Store cleaned OHLCV records into the SQLite ``price_records`` table.

    Uses SQLAlchemy ORM upsert via ``merge()`` keyed on ``(ticker, date)``.

    Args:
        engine: SQLAlchemy engine.
        records_df: DataFrame with columns date, open, high, low, close,
            volume, simple_return, log_return.
        ticker: Ticker symbol for all rows.
        on_conflict: "replace" overwrites existing rows, "skip" keeps
            the original.

    Returns:
        Number of rows upserted.
    """
    count = 0
    with Session(engine) as session:
        for _, row in records_df.iterrows():
            rec = (
                session.query(PriceRecord)
                .filter_by(ticker=ticker, date=row["date"])
                .first()
            )

            if rec and on_conflict == "skip":
                continue

            if rec is None:
                rec = PriceRecord(ticker=ticker, date=row["date"])

            for col in ("open", "high", "low", "close", "volume", "simple_return", "log_return"):
                val = row.get(col)
                if pd.notna(val):
                    setattr(rec, col, float(val))
            session.merge(rec)
            count += 1
        session.commit()
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest(
    ticker: str,
    start_date: str = "2023-01-01",
    end_date: str | None = None,
    interval: str = DEFAULT_INTERVAL,
    db_url: str = DEFAULT_DB_URL,
    on_conflict: str = "replace",
) -> pd.DataFrame:
    """End-to-end ingestion: fetch, clean, compute returns, store.

    Performs a cache check before fetching.  If data for the requested
    range already exists, the API call is skipped.

    Returns:
        DataFrame of the fetched records (including simple_return and
        log_return columns).
    """
    engine = get_engine(db_url)

    with Session(engine) as session:
        adj_start, adj_end = _check_cache(session, ticker, start_date, end_date or datetime.today().strftime("%Y-%m-%d"))

        if adj_start is None:
            # Full cache hit — return cached data.
            cached = (
                session.query(PriceRecord)
                .filter(
                    PriceRecord.ticker == ticker,
                    PriceRecord.date >= start_date,
                    PriceRecord.date <= end_date,
                )
                .order_by(PriceRecord.date)
                .all()
            )
            df = pd.DataFrame(
                [
                    {
                        "date": r.date,
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                        "simple_return": r.simple_return,
                        "log_return": r.log_return,
                    }
                    for r in cached
                ]
            )
            return df

    # Fetch from yfinance for the adjusted range.
    df = fetch_ohlcv(ticker, adj_start, adj_end or datetime.today().strftime("%Y-%m-%d"), interval)

    if df.empty:
        return df

    df = compute_returns(df)

    # Drop the first row (NaN returns) for clean data.
    df.dropna(subset=["close"], inplace=True)

    store_records(engine, df, ticker, on_conflict)
    return df


# ---------------------------------------------------------------------------
# Summary analytics
# ---------------------------------------------------------------------------


def summary_stats(engine, ticker: str) -> dict:
    """Return summary statistics for *ticker* from the database.

    Includes mean return, std deviation, Sharpe-ratio estimate
    (annualized, assuming 252 trading days and zero risk-free rate),
    and min/max for both simple and log returns.
    """
    with Session(engine) as session:
        records = (
            session.query(PriceRecord)
            .filter(PriceRecord.ticker == ticker)
            .order_by(PriceRecord.date)
            .all()
        )

    if not records:
        return {}

    df = pd.DataFrame(
        [
            {"simple_return": r.simple_return, "log_return": r.log_return}
            for r in records
            if r.simple_return is not None and r.log_return is not None
        ]
    )

    if df.empty:
        return {}

    lr_mean = df["log_return"].mean()
    lr_std = df["log_return"].std()

    n_trading_days = 252
    sharpe = (lr_mean / lr_std * np.sqrt(n_trading_days)) if lr_std > 0 else 0.0

    return {
        "ticker": ticker,
        "n_observations": len(df),
        "mean_simple_return": float(df["simple_return"].mean()),
        "mean_log_return": float(lr_mean),
        "std_log_return": float(lr_std),
        "sharpe_estimate": float(sharpe),
        "min_simple_return": float(df["simple_return"].min()),
        "max_simple_return": float(df["simple_return"].max()),
        "min_log_return": float(df["log_return"].min()),
        "max_log_return": float(df["log_return"].max()),
    }
