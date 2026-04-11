"""FastAPI routes for stochastic process simulation."""

import numpy as np
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from backend.dependencies.tier_guard import check_daily_limit
from backend.models.user import User

from quant.stochastic.simulations import (
    brownian_motion,
    geometric_brownian_motion,
    plot_simulations,
)

router = APIRouter(prefix="/simulate", tags=["simulation"])


class GBMRequest(BaseModel):
    S0: float = Field(default=100.0, gt=0, description="Initial price")
    mu: float = Field(default=0.05, description="Drift (expected annualized return)")
    sigma: float = Field(default=0.2, gt=0, description="Volatility (annualized)")
    T: float = Field(default=1.0, gt=0, description="Time horizon in years")
    n_steps: int = Field(default=252, gt=0, description="Number of time steps")
    n_sims: int = Field(default=1000, gt=0, le=50000, description="Number of simulation paths (max 50000)")


class BrownianRequest(BaseModel):
    T: float = Field(default=1.0, gt=0, description="Time horizon")
    n_steps: int = Field(default=252, gt=0, description="Number of time steps")
    sigma: float = Field(default=1.0, gt=0, description="Diffusion coefficient")


@router.post("/gbm")
async def simulate_gbm(req: GBMRequest, user: User = Depends(check_daily_limit("simulations"))):
    """Run GBM simulation and return sample paths, price stats, and plot."""
    paths = geometric_brownian_motion(
        S0=req.S0,
        mu=req.mu,
        sigma=req.sigma,
        T=req.T,
        n_steps=req.n_steps,
        n_sims=req.n_sims,
    )

    # First 50 paths for the response payload
    sample = paths[:50]

    # Final price distribution stats
    final = paths[:, -1]
    final_stats = {
        "mean": float(final.mean()),
        "median": float(np.median(final)),
        "std": float(final.std()),
        "min": float(final.min()),
        "max": float(final.max()),
        "p05": float(np.percentile(final, 5)),
        "p95": float(np.percentile(final, 95)),
    }

    time = np.linspace(0, req.T, req.n_steps + 1)
    plot_json = plot_simulations(sample, "Geometric Brownian Motion", time=time)

    return {
        "paths_sample": sample.tolist(),
        "final_prices": final_stats,
        "plot_json": plot_json,
    }


@router.post("/brownian")
async def simulate_brownian(req: BrownianRequest):
    """Run a single Brownian motion simulation and return path + plot."""
    time, path = brownian_motion(T=req.T, n_steps=req.n_steps, sigma=req.sigma)
    plot_json = plot_simulations(path, "Brownian Motion", time=time)

    return {
        "time": time.tolist(),
        "path": path.tolist(),
        "plot_json": plot_json,
    }
