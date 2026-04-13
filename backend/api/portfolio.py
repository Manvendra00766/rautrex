from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.models.base import get_db
from backend.models.user import User
from backend.models.portfolio import Portfolio
from backend.services.portfolio_metrics import calculate_portfolio_metrics

logger = logging.getLogger("rautrex")

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


class AssetInput(BaseModel):
    ticker: str
    weight: float


class PortfolioCreate(BaseModel):
    assets: list[AssetInput]


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    assets: list[dict]
    total_value: float | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioCheckResponse(BaseModel):
    exists: bool
    portfolio: PortfolioResponse | None = None


class PortfolioMetricsResponse(BaseModel):
    exists: bool
    message: str | None = None
    total_value: float | None = None
    daily_pnl: float | None = None
    daily_pnl_pct: float | None = None
    cumulative_return: float | None = None
    volatility: float | None = None
    var_95: float | None = None
    asset_breakdown: list | None = None
    price_series: dict | None = None
    portfolio_values: list | None = None
    correlation_matrix: dict | None = None


@router.get("", response_model=PortfolioCheckResponse)
async def check_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if user has a portfolio."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio is None:
        return PortfolioCheckResponse(exists=False, portfolio=None)
    
    return PortfolioCheckResponse(
        exists=True,
        portfolio=PortfolioResponse.model_validate(portfolio),
    )


@router.post("", response_model=PortfolioResponse)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update portfolio for the current user (UPSERT logic).
    
    If portfolio exists, it will be updated with new assets.
    If not, a new portfolio will be created.
    """
    # Check if portfolio already exists
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    existing_portfolio = result.scalar_one_or_none()
    
    # Normalize weights to sum to 1.0
    total_weight = sum(asset.weight for asset in body.assets)
    if total_weight <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one asset weight must be positive",
        )
    
    # Normalize weights to exactly 1.0
    normalized_assets = [
        {
            "ticker": asset.ticker,
            "weight": asset.weight / total_weight  # Auto-adjust to sum to 1.0
        }
        for asset in body.assets
    ]
    
    if existing_portfolio is not None:
        # UPDATE: Portfolio already exists
        logger.info(f"Updating existing portfolio for user {current_user.id}")
        existing_portfolio.assets = normalized_assets
        existing_portfolio.updated_at = datetime.now(timezone.utc)
        db.add(existing_portfolio)
        await db.commit()
        await db.refresh(existing_portfolio)
        return PortfolioResponse.model_validate(existing_portfolio)
    else:
        # CREATE: New portfolio
        logger.info(f"Creating new portfolio for user {current_user.id}")
        portfolio = Portfolio(
            user_id=current_user.id,
            assets=normalized_assets,
            total_value=None,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
        return PortfolioResponse.model_validate(portfolio)
    
    return PortfolioResponse.model_validate(portfolio)


@router.get("/metrics", response_model=PortfolioMetricsResponse)
async def get_portfolio_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio metrics calculated from real market data."""
    try:
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == current_user.id)
        )
        portfolio = result.scalar_one_or_none()
        
        if portfolio is None:
            return PortfolioMetricsResponse(
                exists=False,
                message="No portfolio found. Create one to start tracking performance.",
            )
        
        # Validate portfolio has assets
        if not portfolio.assets or len(portfolio.assets) == 0:
            logger.warning(f"User {current_user.id} portfolio has no assets")
            return PortfolioMetricsResponse(
                exists=False,
                message="Portfolio exists but has no assets. Add assets to start tracking.",
            )
        
        logger.info(f"Calculating metrics for user {current_user.id} with assets: {portfolio.assets}")
        
        # Calculate metrics from real market data
        metrics = calculate_portfolio_metrics(portfolio.assets)
        
        # Update total_value in database
        portfolio.total_value = metrics["total_value"]
        portfolio.updated_at = datetime.now(timezone.utc)
        db.add(portfolio)
        await db.commit()
        
        logger.info(f"Successfully calculated metrics for user {current_user.id}")
        
        return PortfolioMetricsResponse(
            exists=True,
            **metrics
        )
    except ValueError as e:
        logger.error(f"ValueError in get_portfolio_metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Exception in get_portfolio_metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio metrics: {str(e)}",
        )


@router.post("/add-asset", response_model=PortfolioMetricsResponse)
async def add_asset(
    body: AssetInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add or update an asset in the portfolio with automatic weight rebalancing.
    
    If adding new asset makes total weight > 1.0, other assets are proportionally reduced.
    If updating existing asset weight, portfolio is automatically rebalanced.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    
    existing_assets = portfolio.assets.copy() if portfolio.assets else []
    
    # Check if ticker already exists
    asset_exists = False
    for i, asset in enumerate(existing_assets):
        if asset["ticker"] == body.ticker:
            existing_assets[i]["weight"] = body.weight
            asset_exists = True
            break
    
    if not asset_exists:
        # New asset being added
        existing_assets.append({"ticker": body.ticker, "weight": body.weight})
    
    # AUTO-REBALANCE: Normalize weights to sum to 1.0
    total_weight = sum(asset["weight"] for asset in existing_assets)
    
    if total_weight > 0:
        # Proportionally scale all weights to sum to 1.0
        for asset in existing_assets:
            asset["weight"] = asset["weight"] / total_weight
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total weight must be positive",
        )
    
    # Log the rebalancing
    weights_str = ", ".join([f"{a['ticker']}:{a['weight']:.4f}" for a in existing_assets])
    logger.info(
        f"Adding/updating asset {body.ticker} for user {current_user.id}. "
        f"Auto-rebalanced weights: {weights_str}"
    )
    
    portfolio.assets = existing_assets
    portfolio.updated_at = datetime.now(timezone.utc)
    db.add(portfolio)
    await db.commit()
    
    try:
        # Recalculate metrics with new weights
        metrics = calculate_portfolio_metrics(portfolio.assets)
        portfolio.total_value = metrics["total_value"]
        db.add(portfolio)
        await db.commit()
        
        logger.info(f"Successfully updated portfolio for user {current_user.id}")
        
        return PortfolioMetricsResponse(
            exists=True,
            **metrics
        )
    except ValueError as e:
        logger.error(f"ValueError calculating metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Exception calculating metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add asset: {str(e)}",
        )


@router.post("/optimize", response_model=PortfolioMetricsResponse)
async def optimize_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Optimize portfolio weights using equal-weight allocation.
    
    Reweights all assets to equal weights (e.g., 3 assets = 33.3% each).
    Recalculates metrics and returns updated portfolio.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    
    if not portfolio.assets or len(portfolio.assets) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio has no assets to optimize",
        )
    
    try:
        # Calculate equal weights
        num_assets = len(portfolio.assets)
        equal_weight = 1.0 / num_assets
        
        # Update weights for all assets
        tickers = [asset["ticker"] for asset in portfolio.assets]
        portfolio.assets = [
            {"ticker": ticker, "weight": equal_weight}
            for ticker in tickers
        ]
        portfolio.updated_at = datetime.now(timezone.utc)
        db.add(portfolio)
        await db.commit()
        
        logger.info(f"Optimized portfolio for user {current_user.id}: equal weights {1/num_assets:.4f}")
        
        # Recalculate metrics
        metrics = calculate_portfolio_metrics(portfolio.assets)
        portfolio.total_value = metrics["total_value"]
        db.add(portfolio)
        await db.commit()
        
        return PortfolioMetricsResponse(
            exists=True,
            **metrics
        )
    except ValueError as e:
        logger.error(f"ValueError optimizing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Exception optimizing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize portfolio: {str(e)}",
        )

