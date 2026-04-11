# Rautrex — Quantitative Finance Platform

A production-like full-stack platform for quantitative research, strategy
development, risk management, and ML-powered predictions. Backend built with
FastAPI + SQLAlchemy async, frontend with Next.js + Recharts + Plotly.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                   Next.js (port 3000)                        │
│                                                              │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ │
│  │ Login  │ │Dashboard│ │ Market   │ │Simulate│ │Portfolio│ │
│  │        │ │        │ │ Data     │ │ GBM    │ │Optimizer│ │
│  └────────┘ └────────┘ └──────────┘ └────────┘ └─────────┘ │
│  ┌────────┐ ┌────────┐ ┌──────────┐                         │
│  │ Risk   │ │ Strategy│ │ Predict  │                         │
│  │ VaR/ES │ │Backtest │ │ ML Model │                         │
│  └────────┘ └────────┘ └──────────┘                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (JSON + Plotly JSON)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       Backend                                │
│                  FastAPI (port 8000)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Middleware: CORS │ Rate Limiting │ Request Logging │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────┐            │
│  │ /auth    │ │ /data  │ │ /simulate│ │/strategy│            │
│  │ JWT login│ │ OHLCV  │ │ GBM/BM   │ │Backtest │            │
│  └──────────┘ └────────┘ └──────────┘ └────────┘            │
│  ┌──────────┐ ┌─────────┐ ┌────────┐                        │
│  │ /analysis│ │ /options│ │/health │                        │
│  │ Metrics  │ │BS/Greeks│ │System  │                        │
│  └──────────┘ └─────────┘ └────────┘                        │
│                                                              │
│  ┌─────────────────────┬─────────────────────┐              │
│  │ Services Layer      │ Quant Engine        │              │
│  │ ├─ auth (JWT/bcrypt)│ ├─ stochastic (GBM) │              │
│  │ └─ rate limiter     │ ├─ options (B-S)    │              │
│  │                     │ ├─ portfolio (MPT)  │              │
│  │                     │ ├─ risk (VaR/ES)    │              │
│  │                     │ ├─ strategies       │              │
│  │                     │ ├─ analysis         │              │
│  │                     │ └─ ml (classification)             │
│  └─────────────────────┴─────────────────────┘              │
│                                                              │
│               Supabase Postgres (via asyncpg)                │
│                 ┌──────────────────────┐                     │
│                 │ price_records │ users │                     │
│                 └──────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Docker)

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start everything
docker compose up --build

# 3. Open services
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API docs:  http://localhost:8000/docs
```

## Quick Start (Local)

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Start the backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start the frontend (in a new terminal)
cd frontend
npm install
npm run dev

# 6. Open API docs
# http://localhost:8000/docs
```

---

## Free Deployment (Recommended)

Use **Vercel (frontend)** + **Render (backend)** + **Supabase (Postgres)**.

### 1) Deploy backend on Render
- Push this repo to GitHub.
- In Render, create a **Web Service** from this repo (or use `render.yaml`).
- Settings:
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Set env vars on Render:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `FRONTEND_URL` (your Vercel frontend URL)
  - Optional: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
- After deploy, note backend URL, e.g. `https://rautrex-backend.onrender.com`.

### 2) Deploy frontend on Vercel
- Import same GitHub repo in Vercel.
- Keep root config from `vercel.json`.
- Add env var:
  - `NEXT_PUBLIC_API_URL=https://rautrex-backend.onrender.com`
- Deploy and open your Vercel URL.

### 3) Final check
- Open frontend URL and test login/signup and dashboard API calls.
- Check backend health: `https://<your-render-service>/health`

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/signup` | No | Register new user, returns JWT tokens |
| POST | `/api/v1/auth/login` | No | Authenticate, returns JWT tokens |
| GET | `/api/v1/protected` | Yes | Sample protected endpoint |
| GET | `/api/v1/data/{ticker}` | No | Fetch OHLCV data for ticker |
| GET | `/api/v1/data/{ticker}/summary` | No | Summary statistics for cached ticker |
| POST | `/api/v1/analysis/volatility` | No | Rolling volatility for ticker |
| POST | `/api/v1/analysis/correlation` | No | Pairwise correlation matrix |
| POST | `/api/v1/analysis/metrics` | No | Sharpe, beta, max DD, vol, autocorr |
| POST | `/api/v1/simulate/gbm` | No | Geometric Brownian Motion simulation |
| POST | `/api/v1/simulate/brownian` | No | Single Brownian motion path |
| POST | `/api/v1/strategy/backtest` | No | Run strategy backtest |
| POST | `/api/v1/options/price` | No | Black-Scholes theoretical price |
| POST | `/api/v1/options/greeks` | No | Compute all 5 Greeks |
| POST | `/api/v1/options/iv` | No | Implied volatility from market price |
| GET | `/health` | No | System health and status |

### Rate Limits
- All endpoints: 100 requests/minute per IP
- `/health`: 10 requests/minute per IP

---

## Directory Structure

```
Rautrex/
├── backend/
│   ├── api/          FastAPI route handlers (thin layer)
│   ├── services/     Business logic (auth, hash, etc.)
│   ├── models/       SQLAlchemy ORM + Pydantic schemas + config
│   ├── main.py       App assembly (middleware, routers, startup)
│   └── logging_config.py  Structured JSON logger
├── quant/
│   ├── stochastic/   Stochastic calculus models (GBM, Brownian)
│   ├── options/      Options pricing (Black-Scholes, Greeks, IV)
│   ├── portfolio/    Portfolio optimization (Markowitz, efficient frontier)
│   ├── risk/         Risk metrics (VaR, ES, stress testing)
│   ├── strategies/   Trading strategies + backtesting engine
│   ├── analysis.py   Time-series analytics (Sharpe, beta, vol, etc.)
│   ├── ml/           ML prediction pipeline
│   └── data_collector.py  yfinance ingestion + caching
├── frontend/
│   ├── app/          Next.js pages (app router)
│   └── components/   Shared components (Sidebar, Layout, Skeleton)
├── data/             Raw + processed market data cache
├── notebooks/        Jupyter research notebooks
├── Dockerfile        Backend container definition
├── docker-compose.yml  Full stack orchestration
├── vercel.json       Frontend deployment config
├── .github/workflows/deploy.yml  CI pipeline
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:your-password@your-project-ref.supabase.co:5432/postgres` | Supabase Postgres async connection string |
| `SECRET_KEY` | `change-me-to-a-long-random-string` | HMAC signing key for JWT tokens |
| `APP_NAME` | `Rautrex` | Application name (shown in API docs) |
| `DEBUG` | `false` | Enable debug logging |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token time-to-live |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token time-to-live |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend backend URL |

---

## Key Features

### Quant Engine
- **Stochastic simulation** — Geometric Brownian Motion, standard Brownian Motion, random walks (vectorized via NumPy)
- **Options pricing** — Black-Scholes fair value, full Greeks (delta, gamma, vega, theta, rho), Newton-Raphson implied volatility
- **Portfolio optimization** — Markowitz efficient frontier, max Sharpe portfolio, global minimum variance (SLSQP solver)
- **Risk metrics** — Rolling volatility, Sharpe ratio, max drawdown, beta, autocorrelation tests
- **Strategy backtester** — Event-driven vectorized backtesting with transaction cost modeling; momentum, mean reversion, MA crossover strategies
- **Data pipeline** — yfinance ingestion with database-backed caching, auto-renew on cache miss, log/simple return computation

### Frontend Dashboard
- JWT-protected pages with automatic 401 redirect
- Sidebar navigation across 7 functional pages
- Interactive charts via Recharts (line, bar, histogram) and Plotly.js
- Loading skeletons for all API calls
- Responsive Tailwind layout

### Security
- bcrypt-hashed passwords with configurable work factor
- Dual-token JWT (short-lived access + long-lived refresh)
- Rate limiting via slowapi (100 req/min per IP)
- Input validation via Pydantic (min_password_length, field ranges, gt/le constraints)
- Structured JSON logging with request timing middleware

### Deployment
- Multi-stage Dockerfile (python:3.11-slim) with health check
- docker-compose for single-command local deployment
- Vercel deployment config for frontend
- GitHub Actions CI: lint (black + isort + flake8) / test / Docker build

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, Tailwind CSS, Recharts, Plotly.js, Zustand |
| Backend | FastAPI, Uvicorn, SQLAlchemy (async), Pydantic, slowapi |
| Quant | NumPy, SciPy, Pandas, scikit-learn, yfinance |
| Auth | python-jose (JWT), passlib (bcrypt) |
| Database | Supabase PostgreSQL via asyncpg |
| Deployment | Docker, docker-compose, Vercel, GitHub Actions |
