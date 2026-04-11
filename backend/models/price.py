"""SQLAlchemy model for persisting OHLCV price records.

Each row represents one bar of market data for a ticker, including
pre-computed simple and log returns to avoid recomputation at query time.

Why we store log returns alongside simple returns:
    Log returns (ln(P_t / P_{t-1})) are preferred in quantitative finance
    because they are time-additive — the log return over multiple periods
    is simply the sum of single-period log returns. This property makes
    portfolio aggregation, volatility estimation, and many statistical
    models (e.g. geometric Brownian motion) mathematically tractable.
    Simple returns are still useful for intuitive PnL calculations.
"""

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PriceRecord(Base):
    """Persisted OHLCV bar with pre-computed returns.

    The unique constraint on (ticker, date) enables an upsert pattern:
    if the same ticker+date is fetched twice, the second fetch updates
    rather than duplicates the row.
    """

    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), nullable=False, index=True)
    date = Column(String(20), nullable=False, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    simple_return = Column(Float, nullable=True)
    log_return = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceRecord(ticker={self.ticker}, date={self.date}, "
            f"close={self.close})>"
        )
