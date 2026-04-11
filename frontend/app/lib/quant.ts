const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1`;

function getToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const cookie = document.cookie.split("; ").find((c) => c.startsWith("access_token="));
  return cookie?.split("=")[1];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export interface DataRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  simple_return?: number | null;
}

export interface AnalysisMetrics {
  ticker: string;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  beta: number | null;
  current_volatility: number | null;
  autocorrelation: Record<string, number>;
  period: string;
  observation_count: number;
}

export interface RiskVarResponse {
  ticker: string;
  method: string;
  confidence: number;
  holding_period: number;
  var: number;
  observation_count: number;
  note: string;
}

export async function getData(ticker: string) {
  return request<{ ticker: string; records: DataRecord[]; count: number }>(`/data/${ticker}`);
}

export async function getSummary(ticker: string) {
  return request<Record<string, number | string>>(`/data/${ticker}/summary`);
}

export async function getMetrics(ticker: string, marketTicker = "^GSPC") {
  return request<AnalysisMetrics>("/analysis/metrics", {
    method: "POST",
    body: JSON.stringify({ ticker, market_ticker: marketTicker }),
  });
}

export async function getCorrelation(tickers: string[]) {
  return request<{ tickers: string[]; correlation_matrix: Record<string, Record<string, number>> }>(
    "/analysis/correlation",
    { method: "POST", body: JSON.stringify({ tickers }) }
  );
}

export async function getVolatility(ticker: string, window = 20) {
  return request<{ ticker: string; window: number; rolling_volatility: Record<string, number> }>(
    "/analysis/volatility",
    { method: "POST", body: JSON.stringify({ ticker, window }) }
  );
}

export async function runGBM(payload: {
  S0: number;
  mu: number;
  sigma: number;
  T: number;
  n_steps: number;
  n_sims: number;
}) {
  return request<{ paths_sample: number[][]; final_prices: Record<string, number>; plot_json: any }>(
    "/simulate/gbm",
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export async function runBacktest(payload: {
  ticker: string;
  start: string;
  end?: string;
  strategy: string;
  transaction_cost: number;
  params?: Record<string, unknown>;
}) {
  return request<{
    ticker: string;
    strategy: string;
    total_return: number;
    annualized_sharpe: number;
    max_drawdown: number;
    win_rate: number;
    calmar_ratio: number;
    n_observations: number;
    plot: any;
  }>("/strategy/backtest", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRiskVar(payload: {
  ticker: string;
  method: "historical" | "parametric" | "cvar";
  confidence: number;
  holding_period: number;
}) {
  return request<RiskVarResponse>("/risk/var", { method: "POST", body: JSON.stringify(payload) });
}

export async function getPortfolioVar(payload: {
  tickers: string[];
  weights: number[];
  confidence: number;
}) {
  return request<{ var: number; confidence: number; observation_count: number }>("/risk/portfolio", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function trainPredictModel(ticker: string) {
  const end = new Date().toISOString().slice(0, 10);
  return request<{ feature_importances: Record<string, number>; walk_forward_cv: { folds: Array<{ fold: number; accuracy: number }> } }>(
    "/predict/train",
    { method: "POST", body: JSON.stringify({ ticker, start: "2024-01-01", end, model_type: "random_forest" }) }
  );
}

export async function getPredictSignal(ticker: string) {
  return request<{ signal: "UP" | "DOWN"; probability_up: number }>("/predict/signal", {
    method: "POST",
    body: JSON.stringify({ ticker }),
  });
}

export async function getLiveQuote(ticker: string) {
  return request<any>(`/live/${ticker}/quote`);
}

export async function getIntraday(ticker: string, interval = "15m", period = "1d") {
  return request<{ records: Array<{ datetime: string; close: number }> }>(
    `/live/${ticker}/intraday?interval=${interval}&period=${period}`
  );
}

export async function getMarketStatus() {
  return request<{ is_open: boolean; market_state: string }>("/live/market/status");
}
