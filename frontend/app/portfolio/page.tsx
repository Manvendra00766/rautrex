"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { getPortfolioVar } from "../lib/quant";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

const STOCKS = [
  "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "JNJ", "V",
  "PG", "DIS", "NFLX", "BA", "INTC", "KO", "PEP", "XOM", "WMT", "HD",
];

export default function PortfolioPage() {
  const [selected, setSelected] = useState<string[]>(["AAPL", "MSFT", "NVDA", "SPY", "TLT"]);
  const [portfolioVar, setPortfolioVar] = useState(2.27);
  const [loading, setLoading] = useState(false);

  const toggleTicker = (t: string) => {
    setSelected((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const frontier = [
    { vol: 8.7, ret: 5.3 },
    { vol: 9.9, ret: 6.4 },
    { vol: 11.2, ret: 7.6 },
    { vol: 12.6, ret: 8.9 },
    { vol: 14.1, ret: 10.2 },
    { vol: 15.8, ret: 11.1 },
    { vol: 17.4, ret: 11.9 },
    { vol: 19.3, ret: 12.4 },
    { vol: 21.1, ret: 12.7 },
  ];

  const weights = useMemo(() => {
    const base = selected.slice(0, 5);
    if (base.length === 0) return [];
    const w = 1 / base.length;
    return base.map(() => Number(w.toFixed(4)));
  }, [selected]);

  const runOptimization = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const response = await getPortfolioVar({
        tickers: selected.slice(0, 5),
        weights,
        confidence: 0.95,
      });
      setPortfolioVar(response.var * 100);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">Portfolio Optimization + Rebalancing Recommendations</h2>

      <div>
        <p className="mb-3 text-sm text-slate-400">Asset Universe</p>
        <div className="flex flex-wrap gap-2">
          {STOCKS.map((t) => (
            <button
              key={t}
              onClick={() => toggleTicker(t)}
              className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                selected.includes(t)
                  ? "border-cyan-500 bg-cyan-500/20 text-cyan-300"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <button onClick={runOptimization} disabled={loading || selected.length < 2} className="mt-4 rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50">
          {loading ? "Optimizing..." : "Run Optimization"}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 lg:col-span-2">
          <Plot
            data={[
              {
                x: frontier.map((p) => p.vol),
                y: frontier.map((p) => p.ret),
                type: "scatter",
                mode: "lines+markers",
                marker: { size: 7, color: "#22d3ee" },
                line: { width: 2.4, color: "#22d3ee" },
                name: "Efficient Frontier",
              },
              {
                x: [14.1],
                y: [10.2],
                mode: "markers",
                marker: { size: 12, color: "#f59e0b", symbol: "diamond" },
                name: "Max Sharpe (1.86)",
              },
            ]}
            layout={{
              height: 360,
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              font: { color: "#cbd5e1" },
              margin: { l: 48, r: 20, t: 20, b: 40 },
              xaxis: { title: "Annualized Volatility (%)", gridcolor: "#1e293b" },
              yaxis: { title: "Annualized Return (%)", gridcolor: "#1e293b" },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%" }}
          />
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Optimal Weights</h3>
          <ul className="space-y-2 text-sm text-slate-200 tabular-nums">
            {selected.slice(0, 5).map((s, i) => (
              <li key={s} className="flex justify-between"><span>{s}</span><span>{((weights[i] || 0) * 100).toFixed(2)}%</span></li>
            ))}
            <li className="mt-2 flex justify-between border-t border-slate-800 pt-2 text-cyan-300"><span>Portfolio VaR (95%)</span><span>{portfolioVar.toFixed(2)}%</span></li>
          </ul>
        </div>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800 text-slate-300">
            <tr>
              <th className="px-4 py-3 text-left">Ticker</th>
              <th className="px-4 py-3 text-right">Current Wt</th>
              <th className="px-4 py-3 text-right">Target Wt</th>
              <th className="px-4 py-3 text-right">Delta</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="text-slate-200">
            {[
              ["AAPL", "20.10%", "24.70%", "+4.60%", "Buy"],
              ["MSFT", "24.30%", "21.15%", "-3.15%", "Trim"],
              ["NVDA", "10.20%", "13.85%", "+3.65%", "Buy"],
              ["SPY", "31.40%", "28.40%", "-3.00%", "Trim"],
              ["TLT", "14.00%", "11.90%", "-2.10%", "Trim"],
            ].map((row) => (
              <tr key={row[0]} className="border-t border-slate-800">
                <td className="px-4 py-2">{row[0]}</td>
                <td className="px-4 py-2 text-right tabular-nums">{row[1]}</td>
                <td className="px-4 py-2 text-right tabular-nums">{row[2]}</td>
                <td className="px-4 py-2 text-right tabular-nums">{row[3]}</td>
                <td className="px-4 py-2 text-right">{row[4]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
