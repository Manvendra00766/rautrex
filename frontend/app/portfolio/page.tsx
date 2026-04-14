"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { getPortfolioVar } from "../lib/quant";
import { createPortfolio } from "../lib/api";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

const STOCKS = [
  "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "JNJ", "V",
  "PG", "DIS", "NFLX", "BA", "INTC", "KO", "PEP", "XOM", "WMT", "HD",
];

export default function PortfolioPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>(["AAPL", "MSFT", "NVDA", "SPY", "TLT"]);
  const [amounts, setAmounts] = useState<Record<string, number>>({
    AAPL: 20000,
    MSFT: 20000,
    NVDA: 10000,
    SPY: 0,
    TLT: 0,
  });
  const [portfolioVar, setPortfolioVar] = useState(2.27);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const toggleTicker = (t: string) => {
    setSelected((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
    // Initialize amount if not exists
    if (!amounts[t]) {
      setAmounts(prev => ({ ...prev, [t]: 0 }));
    }
  };

  const totalInvested = Object.values(amounts).reduce((a, b) => a + b, 0);

  const weights = useMemo(() => {
    if (totalInvested === 0) return {};
    const w: Record<string, number> = {};
    selected.forEach(ticker => {
      w[ticker] = (amounts[ticker] || 0) / totalInvested;
    });
    return w;
  }, [selected, amounts, totalInvested]);

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

  const runOptimization = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const response = await getPortfolioVar({
        tickers: selected.slice(0, 5),
        weights: selected.slice(0, 5).map(t => weights[t] || 0),
        confidence: 0.95,
      });
      setPortfolioVar(response.var * 100);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePortfolio = async () => {
    if (totalInvested === 0) {
      setError("Enter investment amounts for at least 2 assets");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const assets = selected
        .filter(ticker => (amounts[ticker] || 0) > 0)
        .map(ticker => ({
          ticker,
          amount_invested: amounts[ticker],
        }));

      if (assets.length < 2) {
        throw new Error("Invest in at least 2 assets");
      }

      await createPortfolio(assets);
      setSuccess(true);

      // Redirect to dashboard after 1.5 seconds
      setTimeout(() => {
        router.push("/dashboard");
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create portfolio");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {success && (
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-emerald-300 animate-pulse">
          ✓ Portfolio created successfully! Redirecting to dashboard...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-300">
          ✗ {error}
        </div>
      )}

      <h2 className="text-sm text-slate-300">Build Your Portfolio - Enter Investment Amounts</h2>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 space-y-4">
        <p className="text-sm text-slate-400">Select assets and enter your investment amount for each</p>
        
        <div className="space-y-3">
          {selected.map((ticker) => (
            <div key={ticker} className="flex items-center gap-4">
              <span className="w-12 font-medium text-slate-300">{ticker}</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={amounts[ticker] || 0}
                onChange={(e) => setAmounts(prev => ({ ...prev, [ticker]: parseFloat(e.target.value) || 0 }))}
                placeholder="0"
                disabled={creating}
                className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none ring-cyan-400/60 focus:ring-2"
              />
              <span className="w-24 text-right text-sm text-slate-400">
                ${(amounts[ticker] || 0).toLocaleString()}
              </span>
              <button
                onClick={() => toggleTicker(ticker)}
                disabled={creating}
                className="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="pt-4 border-t border-slate-700">
          <p className="text-sm text-slate-400 mb-2">Add more assets:</p>
          <div className="flex flex-wrap gap-2">
            {STOCKS.filter(t => !selected.includes(t)).map((t) => (
              <button
                key={t}
                onClick={() => toggleTicker(t)}
                disabled={creating}
                className="rounded-full border border-slate-700 bg-slate-900 hover:border-cyan-500 hover:bg-cyan-500/10 px-3 py-1.5 text-xs text-slate-300 transition-colors"
              >
                + {t}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-4 border-t border-slate-700">
          <div className="text-lg font-semibold text-slate-100">
            Total Investment: ${totalInvested.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleCreatePortfolio}
          disabled={creating || loading || totalInvested === 0}
          className="rounded-md bg-emerald-500 px-6 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {creating ? "Creating..." : "Create Portfolio"}
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
          <h3 className="mb-3 text-sm text-slate-300">Portfolio Weights</h3>
          <ul className="space-y-2 text-sm text-slate-200 tabular-nums">
            {selected.filter(s => (amounts[s] || 0) > 0).map((s) => (
              <li key={s} className="flex justify-between">
                <span>{s}</span>
                <span>{((weights[s] || 0) * 100).toFixed(2)}%</span>
              </li>
            ))}
            {selected.filter(s => (amounts[s] || 0) > 0).length > 0 && (
              <>
                <li className="mt-2 flex justify-between border-t border-slate-800 pt-2 font-medium">
                  <span>Total</span>
                  <span>100.00%</span>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
