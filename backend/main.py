import logging
import time
import platform
import psutil

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.models.config import settings
from backend.models.base import init_engine, create_tables
from backend.models import user, portfolio as portfolio_model  # Import all models to register with Base
from backend.api import auth, protected, data, simulate, strategy, analysis, options, risk, predict, live, payment, portfolio as portfolio_api
from backend.routers import profile
from backend.logging_config import setup_logging

# ─── Structured logging ───
logger = setup_logging()

# ─── Rate limiter: 100 requests per minute per IP ───
limiter = Limiter(key_func=get_remote_address)

# ─── FastAPI app ───
app = FastAPI(
    title=settings.app_name,
    description="Quantitative finance platform — Rautrex",
    version="0.2.0",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@limiter.limit("100/minute")
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Rate limit: 100 req/min per IP."},
    )


# ─── CORS ───
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request logging middleware ───
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.3f}s")
    return response


# ─── Startup ───
@app.on_event("startup")
async def on_startup():
    init_engine(settings.database_url)
    await create_tables()
    app.state.start_time = time.time()
    logger.info(f"Rautrex v0.2.0 started on {platform.system()}")


# ─── Routes ───
app.include_router(auth.router, prefix="/api/v1")
app.include_router(protected.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(live.router, prefix="/api/v1")
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(strategy.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(options.router, prefix="/api/v1/options")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(predict.router, prefix="/api/v1")
app.include_router(payment.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(portfolio_api.router, prefix="/api/v1")


@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request) -> dict:
    """Enhanced health probe with system metrics for monitoring."""
    process = psutil.Process()
    return {
        "status": "healthy",
        "version": "0.2.0",
        "cpu_percent": psutil.cpu_percent(interval=0),
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "memory_percent": process.memory_percent(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
    }
