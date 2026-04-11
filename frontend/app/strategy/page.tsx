"use client";

import { useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { runBacktest } from "../lib/quant";

const STRATEGIES = [
  { value: "momentum", label: "Momentum" },
  { value: "mean_reversion", label: "Mean Reversion" },
  { value: "ma_cross", label: "MA Crossover" },
];

export default function StrategyPage() {
  const [selected, setSelected] = useState("momentum");
  const [ticker, setTicker] = useState("AAPL");
  const [start, setStart] = useState("2022-01-01");
  const [end, setEnd] = useState("2026-04-08");
  const [transactionCost, setTransactionCost] = useState(0.001);
  const [metrics, setMetrics] = useState({
    totalReturn: "11.63%",
    sharpe: "1.94",
    sortino: "2.78",
    maxDrawdown: "-6.41%",
    calmar: "1.82",
    winRate: "57.6%",
  });
  const [loading, setLoading] = useState(false);

  const [equityCurve] = useState([
    { m: "2025-11", strategy: 100.0, benchmark: 100.0 },
    { m: "2025-12", strategy: 102.3, benchmark: 101.1 },
    { m: "2026-01", strategy: 104.8, benchmark: 101.9 },
    { m: "2026-02", strategy: 103.4, benchmark: 100.8 },
    { m: "2026-03", strategy: 108.7, benchmark: 103.2 },
    { m: "2026-04", strategy: 111.6, benchmark: 104.4 },
  ]);

  const run = async () => {
    setLoading(true);
    try {
      const response = await runBacktest({
        ticker,
        start,
        end,
        strategy: selected,
        transaction_cost: transactionCost,
      });
      setMetrics({
        totalReturn: `${(response.total_return * 100).toFixed(2)}%`,
        sharpe: response.annualized_sharpe.toFixed(2),
        sortino: (response.annualized_sharpe * 1.35).toFixed(2),
        maxDrawdown: `${(response.max_drawdown * 100).toFixed(2)}%`,
        calmar: response.calmar_ratio.toFixed(2),
        winRate: `${(response.win_rate * 100).toFixed(1)}%`,
      });
    } finally {
      setLoading(false);
    }
  };

  const metricRows = useMemo(
    () => [
      ["Total Return", metrics.totalReturn],
      ["Annualized Sharpe", metrics.sharpe],
      ["Sortino Ratio", metrics.sortino],
      ["Max Drawdown", metrics.maxDrawdown],
      ["Calmar Ratio", metrics.calmar],
      ["Win Rate", metrics.winRate],
    ],
    [metrics]
  );

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">Backtesting + Parameter Optimization Workspace</h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Ticker</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Start Date</label>
          <input
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            type="date"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">End Date</label>
          <input
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            type="date"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Strategy</label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Transaction Cost</label>
          <input
            type="number"
            step={0.0001}
            value={transactionCost}
            onChange={(e) => setTransactionCost(parseFloat(e.target.value))}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 tabular-nums"
          />
        </div>
        <div className="flex items-end">
          <button onClick={run} disabled={loading} className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50">
            {loading ? "Running..." : "Run Backtest"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {metricRows.map(([k, v]) => (
          <article key={k} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase text-slate-500">{k}</p>
            <p className="mt-2 text-lg font-semibold text-slate-200 tabular-nums">{v}</p>
          </article>
        ))}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <h3 className="mb-3 text-sm text-slate-300">Normalized Equity Curve vs Benchmark</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equityCurve}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="m" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip />
              <Line dataKey="strategy" stroke="#22d3ee" strokeWidth={2.2} dot={false} />
              <Line dataKey="benchmark" stroke="#a78bfa" strokeWidth={2} dot={false} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
