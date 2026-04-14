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
    amount_invested: float  # Investment amount in USD/currency


class PortfolioCreate(BaseModel):
    assets: list[AssetInput]


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    assets: list[dict]
    total_invested: float | None
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
    total_invested: float | None = None
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
    """Create or update portfolio for the current user with investment amounts.
    
    User provides investment amounts, system calculates weights automatically.
    """
    # Validate all amounts are positive
    total_invested = sum(asset.amount_invested for asset in body.assets)
    if total_invested <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total investment amount must be positive",
        )
    
    # Convert amounts to asset objects
    assets_data = [
        {
            "ticker": asset.ticker,
            "amount_invested": asset.amount_invested,
        }
        for asset in body.assets
    ]
    
    # Check if portfolio already exists
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    existing_portfolio = result.scalar_one_or_none()
    
    if existing_portfolio is not None:
        # UPDATE: Portfolio already exists
        logger.info(f"Updating existing portfolio for user {current_user.id}")
        existing_portfolio.assets = assets_data
        existing_portfolio.total_invested = total_invested
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
            assets=assets_data,
            total_invested=total_invested,
            total_value=None,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
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
    """Add or update an asset in the portfolio with investment amount.
    
    System automatically recalculates portfolio weights based on amounts.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found. Create one first.",
        )
    
    if body.amount_invested <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Investment amount must be positive",
        )
    
    existing_assets = portfolio.assets.copy() if portfolio.assets else []
    
    # Check if ticker already exists
    asset_exists = False
    for i, asset in enumerate(existing_assets):
        if asset["ticker"] == body.ticker:
            existing_assets[i]["amount_invested"] = body.amount_invested
            asset_exists = True
            break
    
    if not asset_exists:
        # New asset being added
        existing_assets.append({
            "ticker": body.ticker,
            "amount_invested": body.amount_invested
        })
    
    # Recalculate total invested
    total_invested = sum(asset["amount_invested"] for asset in existing_assets)
    
    # Log the update
    assets_str = ", ".join([f"{a['ticker']}:${a['amount_invested']:.2f}" for a in existing_assets])
    logger.info(
        f"Adding/updating asset {body.ticker} for user {current_user.id}. "
        f"Total invested: ${total_invested:.2f}. Assets: {assets_str}"
    )
    
    portfolio.assets = existing_assets
    portfolio.total_invested = total_invested
    portfolio.updated_at = datetime.now(timezone.utc)
    db.add(portfolio)
    await db.commit()
    
    try:
        # Recalculate metrics with updated portfolio
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
    """Rebalance portfolio to equal dollar amounts across all assets.
    
    Each asset gets equal investment amount based on total_invested / num_assets.
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
        # Calculate equal amounts for each asset
        num_assets = len(portfolio.assets)
        equal_amount = portfolio.total_invested / num_assets if portfolio.total_invested else 0
        
        if equal_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot optimize with zero total investment",
            )
        
        # Update amounts for all assets
        tickers = [asset["ticker"] for asset in portfolio.assets]
        portfolio.assets = [
            {"ticker": ticker, "amount_invested": equal_amount}
            for ticker in tickers
        ]
        portfolio.updated_at = datetime.now(timezone.utc)
        db.add(portfolio)
        await db.commit()
        
        logger.info(f"Optimized portfolio for user {current_user.id}: equal amounts ${equal_amount:.2f} each")
        
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


@router.delete("/remove-asset/{ticker}", response_model=PortfolioMetricsResponse)
async def remove_asset(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an asset from the portfolio."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    
    # Filter out the asset
    original_count = len(portfolio.assets)
    portfolio.assets = [a for a in portfolio.assets if a["ticker"].upper() != ticker.upper()]
    
    if len(portfolio.assets) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {ticker} not found in portfolio",
        )
    
    if len(portfolio.assets) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove last asset from portfolio",
        )
    
    # Recalculate total invested
    total_invested = sum(asset["amount_invested"] for asset in portfolio.assets)
    
    portfolio.total_invested = total_invested
    portfolio.updated_at = datetime.now(timezone.utc)
    db.add(portfolio)
    await db.commit()
    
    logger.info(f"Removed asset {ticker} from user {current_user.id}")
    
    try:
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
        logger.error(f"ValueError calculating metrics after removal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Exception calculating metrics after removal: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove asset: {str(e)}",
        )