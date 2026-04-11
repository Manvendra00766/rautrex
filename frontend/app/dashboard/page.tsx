"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { getData, getMetrics, getRiskVar } from "../lib/quant";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

const ohlc = [
  ["2026-03-24", 122390, 123210, 121880, 122940],
  ["2026-03-25", 122950, 123480, 122610, 123150],
  ["2026-03-26", 123140, 123860, 122770, 123590],
  ["2026-03-27", 123600, 124110, 123200, 123890],
  ["2026-03-30", 123920, 124780, 123710, 124620],
  ["2026-03-31", 124610, 125010, 124120, 124430],
  ["2026-04-01", 124420, 125220, 124000, 124980],
  ["2026-04-02", 124960, 125870, 124640, 125630],
  ["2026-04-03", 125640, 126130, 125220, 125450],
  ["2026-04-06", 125460, 125960, 124990, 125120],
  ["2026-04-07", 125110, 126020, 124870, 125710],
  ["2026-04-08", 125690, 126410, 125340, 126180],
];

const benchmark = [
  { date: "2026-03-24", portfolio: 122940, sp500: 5106.13 },
  { date: "2026-03-25", portfolio: 123150, sp500: 5128.48 },
  { date: "2026-03-26", portfolio: 123590, sp500: 5142.26 },
  { date: "2026-03-27", portfolio: 123890, sp500: 5155.19 },
  { date: "2026-03-30", portfolio: 124620, sp500: 5178.83 },
  { date: "2026-03-31", portfolio: 124430, sp500: 5169.46 },
  { date: "2026-04-01", portfolio: 124980, sp500: 5198.05 },
  { date: "2026-04-02", portfolio: 125630, sp500: 5217.44 },
  { date: "2026-04-03", portfolio: 125450, sp500: 5209.68 },
  { date: "2026-04-06", portfolio: 125120, sp500: 5192.17 },
  { date: "2026-04-07", portfolio: 125710, sp500: 5221.39 },
  { date: "2026-04-08", portfolio: 126180, sp500: 5240.64 },
];

export default function DashboardPage() {
  const [upgraded, setUpgraded] = useState(false);
  const [portfolioValue, setPortfolioValue] = useState(125430.52);
  const [dailyPnl, setDailyPnl] = useState(2481.37);
  const [var95, setVar95] = useState(2847.33);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      setUpgraded(params.get("upgraded") === "true");
    }
    const load = async () => {
      try {
        const [aaplData, aaplMetrics, varRes] = await Promise.all([
          getData("AAPL"),
          getMetrics("AAPL"),
          getRiskVar({ ticker: "AAPL", method: "historical", confidence: 0.95, holding_period: 1 }),
        ]);
        const records = aaplData.records || [];
        if (records.length >= 2) {
          const latest = Number(records[records.length - 1].close);
          const prev = Number(records[records.length - 2].close);
          const pnl = (latest - prev) * 1200;
          setDailyPnl(pnl);
          setPortfolioValue(125000 + latest * 2);
        }
        setVar95(varRes.var * portfolioValue);
        if (aaplMetrics.current_volatility && aaplMetrics.current_volatility > 0.2) {
          setPortfolioValue((v) => v * 0.998);
        }
      } catch {}
    };
    load();
  }, []);

  const metrics = useMemo(
    () => [
      { label: "Total Portfolio Value", value: `$${portfolioValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, delta: `${((dailyPnl / portfolioValue) * 100).toFixed(2)}% (1D)`, tone: "text-emerald-300" },
      { label: "Daily P&L", value: `${dailyPnl >= 0 ? "+" : ""}$${Math.abs(dailyPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, delta: "vs benchmark blend", tone: dailyPnl >= 0 ? "text-emerald-300" : "text-rose-300" },
      { label: "95% VaR (1D)", value: `$${Math.abs(var95).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, delta: `${((var95 / portfolioValue) * 100).toFixed(2)}% capital at risk`, tone: "text-amber-300" },
      { label: "Active Strategies", value: "4", delta: "2 mean reversion • 2 momentum", tone: "text-cyan-300" },
    ],
    [dailyPnl, portfolioValue, var95]
  );

  return (
    <div className="space-y-6">
      {upgraded && (
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-emerald-300">
          Welcome to Pro 🎉 — All features unlocked.
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((item) => (
          <article key={item.label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs uppercase tracking-wide text-slate-400">{item.label}</p>
            <p className={`mt-2 text-2xl font-semibold tabular-nums ${item.tone}`}>{item.value}</p>
            <p className="mt-1 text-xs text-slate-400 tabular-nums">{item.delta}</p>
          </article>
        ))}
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-300">Portfolio Candles + Indexed Portfolio/SPX Lines</h2>
        <Plot
          data={[
            {
              type: "candlestick",
              x: ohlc.map((d) => d[0]),
              open: ohlc.map((d) => d[1]),
              high: ohlc.map((d) => d[2]),
              low: ohlc.map((d) => d[3]),
              close: ohlc.map((d) => d[4]),
              name: "Portfolio OHLC",
              yaxis: "y1",
            },
            {
              type: "scatter",
              mode: "lines",
              x: benchmark.map((d) => d.date),
              y: benchmark.map((d) => (d.portfolio / benchmark[0].portfolio) * 100),
              name: "Portfolio Index",
              line: { color: "#22d3ee", width: 2.2 },
              yaxis: "y2",
            },
            {
              type: "scatter",
              mode: "lines",
              x: benchmark.map((d) => d.date),
              y: benchmark.map((d) => (d.sp500 / benchmark[0].sp500) * 100),
              name: "S&P 500 Index",
              line: { color: "#a78bfa", width: 2.2, dash: "dot" },
              yaxis: "y2",
            },
          ]}
          layout={{
            height: 420,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#cbd5e1" },
            margin: { l: 52, r: 52, t: 12, b: 40 },
            xaxis: { gridcolor: "#1e293b" },
            yaxis: { title: "USD", gridcolor: "#1e293b" },
            yaxis2: { title: "Indexed (Base=100)", overlaying: "y", side: "right", showgrid: false },
            legend: { orientation: "h", y: 1.08, x: 0 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%" }}
        />
      </section>
    </div>
  );
}
