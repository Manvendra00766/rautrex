"""FastAPI routes for strategy backtesting.

Endpoint
--------
POST /strategy/backtest
    Ingests data, runs the requested strategy, and returns performance
    metrics + an interactive Plotly chart as JSON.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from quant.data_collector import DEFAULT_DB_URL, get_engine, ingest
from quant.strategies.backtest import (
    STRATEGIES,
    Backtester,
    MomentumStrategy,
    MeanReversionStrategy,
    MovingAverageCrossover,
)
from backend.dependencies.tier_guard import check_daily_limit
from backend.models.user import User

router = APIRouter(prefix="/strategy", tags=["strategy"])

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class BacktestRequest(BaseModel):
    ticker: str
    start: str = "2020-01-01"
    end: Optional[str] = None
    strategy: str  # "momentum" | "mean_reversion" | "ma_cross"
    params: Optional[dict] = {}
    transaction_cost: float = 0.001


class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    total_return: float
    annualized_sharpe: float
    max_drawdown: float
    win_rate: float
    calmar_ratio: float
    n_observations: int
    plot: Optional[dict] = None
    
    class Config:
        json_encoders = {
            float: lambda v: float(v) if not (v != v or v == float('inf') or v == float('-inf')) else None,
        }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/backtest", response_model=BacktestResponse)
def run_backtest(req: BacktestRequest, user: User = Depends(check_daily_limit("backtests"))):
    """Run a backtest for the requested strategy and ticker.

    Flow:
        1. Ingest OHLCV data via the data_collector (with cache check).
        2. Instantiate the requested strategy with user params.
        3. Generate signals from close prices.
        4. Run the Backtester with transaction cost modeling.
        5. Return metrics + Plotly figure JSON.

    The signal is automatically lagged by 1 period inside the Backtester
    to prevent look-ahead bias — see the module docstring for details.
    """
    strategy_cls = STRATEGIES.get(req.strategy)
    if strategy_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{req.strategy}'. "
                   f"Available: {list(STRATEGIES.keys())}",
        )

    # --- Ingest data ----------------------------------------------------------
    end_date = req.end or datetime.today().strftime("%Y-%m-%d")
    df = ingest(
        ticker=req.ticker,
        start_date=req.start,
        end_date=end_date,
        db_url=DEFAULT_DB_URL,
    )

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for '{req.ticker}' in [{req.start}, {end_date}].",
        )

    prices = df.set_index("date")["close"].sort_index()

    # --- Run strategy ---------------------------------------------------------
    try:
        strategy = strategy_cls(**(req.params or {}))
    except TypeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid params for {req.strategy}: {exc}",
        )

    signals = strategy.generate_signals(prices)
    result = Backtester.run(prices, signals, req.transaction_cost)
    result.plot_json = Backtester.plot_results(result)

    return BacktestResponse(
        ticker=req.ticker,
        strategy=req.strategy,
        total_return=float(result.total_return),
        annualized_sharpe=float(result.annualized_sharpe),
        max_drawdown=float(result.max_drawdown),
        win_rate=float(result.win_rate),
        calmar_ratio=float(result.calmar_ratio),
        n_observations=int(len(result.daily_returns)),
        plot=result.plot_json,
    )
