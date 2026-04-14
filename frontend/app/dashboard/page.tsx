"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { checkPortfolio, getPortfolioMetrics, addAssetToPortfolio, removeAssetFromPortfolio, optimizePortfolio } from "../lib/api";
import PortfolioEmptyState from "@/components/PortfolioEmptyState";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

interface Metric {
  label: string;
  value: string;
  delta: string;
  tone: string;
}

  interface PortfolioData {
    total_invested: number;
    total_value: number;
    daily_pnl: number;
    daily_pnl_pct: number;
    cumulative_return: number;
    volatility: number;
    var_95: number;
    asset_breakdown: Array<{
      ticker: string;
      amount_invested: number;
      weight: number;
      price: number;
      quantity: number;
      value: number;
    }>;
    portfolio_values: Array<{ date: string; value: number }>;
    correlation_matrix: Record<string, Record<string, number>>;
  }

export default function DashboardPage() {
  const [portfolioExists, setPortfolioExists] = useState<boolean | null>(null);
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddAssetModal, setShowAddAssetModal] = useState(false);
  const [addAssetLoading, setAddAssetLoading] = useState(false);
  const [addAssetError, setAddAssetError] = useState<string | null>(null);
  const [newTicker, setNewTicker] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [removeAssetLoading, setRemoveAssetLoading] = useState<string | null>(null);

  const loadPortfolioData = async () => {
    setLoading(true);
    setError(null);
    try {
      const check = await checkPortfolio();
      setPortfolioExists(check.exists);

      if (check.exists) {
        const metrics = await getPortfolioMetrics();
        if (metrics.exists) {
          setPortfolioData(metrics);
        } else if (metrics.message) {
          // Portfolio exists but has no assets or error occurred
          setError(metrics.message || "Portfolio has no assets. Add assets to see metrics.");
        }
      }
    } catch (err) {
      console.error("Failed to load portfolio:", err);
      setError(err instanceof Error ? err.message : "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortfolioData();
  }, []);

  const handleAddAsset = async () => {
    setAddAssetError(null);
    setAddAssetLoading(true);

    try {
      const amount = parseFloat(newAmount);
      if (!newTicker || !newAmount) {
        throw new Error("Ticker and investment amount are required");
      }
      if (amount <= 0) {
        throw new Error("Investment amount must be positive");
      }

      await addAssetToPortfolio(newTicker.toUpperCase(), amount);
      setNewTicker("");
      setNewAmount("");
      setShowAddAssetModal(false);

      // Reload portfolio data after adding asset (triggers live update)
      await loadPortfolioData();
    } catch (err) {
      setAddAssetError(err instanceof Error ? err.message : "Failed to add asset");
    } finally {
      setAddAssetLoading(false);
    }
  };

  const handleRemoveAsset = async (ticker: string) => {
    setRemoveAssetLoading(ticker);
    try {
      await removeAssetFromPortfolio(ticker);
      await loadPortfolioData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove asset");
    } finally {
      setRemoveAssetLoading(null);
    }
  };

  const handleOptimize = async () => {
    setAddAssetLoading(true);
    setError(null);

    try {
      await optimizePortfolio();
      // Reload portfolio data after optimization
      await loadPortfolioData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to optimize portfolio");
    } finally {
      setAddAssetLoading(false);
    }
  };

  const metrics: Metric[] = useMemo(() => {
    if (!portfolioData) return [];

    return [
      {
        label: "Total Invested",
        value: `$${portfolioData.total_invested.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`,
        delta: `Current Value: $${portfolioData.total_value.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`,
        tone: portfolioData.total_value >= portfolioData.total_invested ? "text-emerald-300" : "text-rose-300",
      },
      {
        label: "Daily P&L",
        value: `${portfolioData.daily_pnl >= 0 ? "+" : ""}$${Math.abs(
          portfolioData.daily_pnl
        ).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        delta: `${portfolioData.cumulative_return.toFixed(2)}% total return`,
        tone: portfolioData.daily_pnl >= 0 ? "text-emerald-300" : "text-rose-300",
      },
      {
        label: "Volatility (Annual)",
        value: `${(portfolioData.volatility * 100).toFixed(2)}%`,
        delta: `Risk level indicator`,
        tone: "text-amber-300",
      },
      {
        label: "95% VaR (Daily)",
        value: `${(portfolioData.var_95 * 100).toFixed(2)}%`,
        delta: `Maximum daily loss`,
        tone: "text-rose-300",
      },
    ];
  }, [portfolioData]);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-slate-400">Loading portfolio...</div>
      </div>
    );
  }

  // Empty state
  if (!portfolioExists) {
    return <PortfolioEmptyState onCreatePortfolio={() => (window.location.href = "/portfolio")} />;
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-300">
          {error}
        </div>
        <button
          onClick={() => setShowAddAssetModal(true)}
          className="px-4 py-2 rounded-md bg-cyan-500 text-slate-900 font-semibold hover:bg-cyan-400 transition"
        >
          Add Asset
        </button>
      </div>
    );
  }

  // Dashboard with real data
  return (
    <div className="space-y-6">
      {/* Add Asset Modal */}
      {showAddAssetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl w-96">
            <h3 className="mb-4 text-lg font-semibold text-slate-100">Add Asset</h3>

            {addAssetError && (
              <div className="mb-4 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">
                {addAssetError}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Ticker</label>
                <input
                  type="text"
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                  placeholder="AAPL, TSLA, BTC-USD"
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                  disabled={addAssetLoading}
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Investment Amount ($)</label>
                <input
                  type="number"
                  step="1000"
                  min="0"
                  value={newAmount}
                  onChange={(e) => setNewAmount(e.target.value)}
                  placeholder="10000"
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                  disabled={addAssetLoading}
                />
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={handleAddAsset}
                disabled={addAssetLoading || !newTicker || !newAmount}
                className="flex-1 rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
              >
                {addAssetLoading ? "Adding..." : "Add Asset"}
              </button>
              <button
                onClick={() => setShowAddAssetModal(false)}
                disabled={addAssetLoading}
                className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((item) => (
          <article key={item.label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs uppercase tracking-wide text-slate-400">{item.label}</p>
            <p className={`mt-2 text-2xl font-semibold tabular-nums ${item.tone}`}>{item.value}</p>
            <p className="mt-1 text-xs text-slate-400 tabular-nums">{item.delta}</p>
          </article>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowAddAssetModal(true)}
          className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 transition"
        >
          + Add Asset
        </button>
        <button
          onClick={handleOptimize}
          disabled={addAssetLoading || removeAssetLoading !== null}
          className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-amber-400 transition disabled:opacity-50"
        >
          Rebalance (Equal $)
        </button>
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Portfolio Value Over Time */}
        {portfolioData?.portfolio_values && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-300">Portfolio Value Over Time</h2>
            <Plot
              data={[
                {
                  x: portfolioData.portfolio_values.map((d) => d.date),
                  y: portfolioData.portfolio_values.map((d) => d.value),
                  type: "scatter",
                  mode: "lines",
                  fill: "tozeroy",
                  line: { color: "#22d3ee", width: 2 },
                  fillcolor: "rgba(34, 211, 238, 0.1)",
                  name: "Portfolio Value",
                },
              ]}
              layout={{
                height: 360,
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#cbd5e1" },
                margin: { l: 52, r: 20, t: 12, b: 40 },
                xaxis: { gridcolor: "#1e293b" },
                yaxis: { title: "USD", gridcolor: "#1e293b" },
                legend: { x: 0, y: 1 },
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: "100%" }}
            />
          </section>
        )}

        {/* Asset Allocation */}
        {portfolioData?.asset_breakdown && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-300">Asset Allocation</h2>
            <Plot
              data={[
                {
                  labels: portfolioData.asset_breakdown.map((a) => a.ticker),
                  values: portfolioData.asset_breakdown.map((a) => a.weight * 100),
                  type: "pie",
                  marker: { colors: ["#22d3ee", "#f59e0b", "#8b5cf6", "#ec4899", "#10b981"] },
                },
              ]}
              layout={{
                height: 360,
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#cbd5e1" },
                margin: { l: 0, r: 0, t: 12, b: 0 },
                legend: { orientation: "v", x: 1, y: 0.5 },
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: "100%" }}
            />
          </section>
        )}
      </div>

      {/* Asset Breakdown Table */}
      {portfolioData?.asset_breakdown && (
        <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-800 text-slate-300">
              <tr>
                <th className="px-4 py-3 text-left">Ticker</th>
                <th className="px-4 py-3 text-right">Amount Invested</th>
                <th className="px-4 py-3 text-right">Weight</th>
                <th className="px-4 py-3 text-right">Price</th>
                <th className="px-4 py-3 text-right">Quantity</th>
                <th className="px-4 py-3 text-right">Current Value</th>
                <th className="px-4 py-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="text-slate-200">
              {portfolioData.asset_breakdown.map((asset) => (
                <tr key={asset.ticker} className="border-t border-slate-800">
                  <td className="px-4 py-2 font-medium">{asset.ticker}</td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    ${asset.amount_invested.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-4 py-2 text-right">{(asset.weight * 100).toFixed(2)}%</td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    ${asset.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {asset.quantity.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-emerald-300">
                    ${asset.value.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <button
                      onClick={() => handleRemoveAsset(asset.ticker)}
                      disabled={removeAssetLoading !== null}
                      className="text-xs px-2 py-1 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 disabled:opacity-50"
                    >
                      {removeAssetLoading === asset.ticker ? "..." : "Remove"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
