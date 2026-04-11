"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { runGBM } from "../lib/quant";

const Plot = dynamic<any>(() => import("react-plotly.js"), { ssr: false });

export default function SimulatePage() {
  const [params, setParams] = useState({
    S0: 222.84,
    mu: 0.0825,
    sigma: 0.243,
    T: 1,
    n_steps: 252,
    n_sims: 8,
  });
  const [stats, setStats] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [runCount, setRunCount] = useState(0);
  const [limitMessage, setLimitMessage] = useState<string | null>(null);

  const [paths, setPaths] = useState<number[][]>([
    [222.84, 224.12, 226.48, 225.01, 228.37, 231.14, 233.8, 236.02, 234.9, 237.66],
    [222.84, 221.3, 220.84, 222.42, 224.05, 225.33, 227.81, 228.93, 230.11, 232.44],
    [222.84, 220.78, 218.9, 216.84, 215.11, 214.72, 213.49, 216.18, 217.42, 219.77],
    [222.84, 225.6, 227.35, 229.4, 231.27, 230.89, 232.33, 235.08, 236.74, 239.63],
  ]);

  const runSimulation = async () => {
    setLoading(true);
    try {
      if (runCount >= 2) {
        setLimitMessage("You've used 2/2 free simulations today.");
        return;
      }
      const response = await runGBM(params);
      if (response.paths_sample?.length) {
        setPaths(response.paths_sample.slice(0, 4).map((p) => {
          const stride = Math.max(1, Math.floor(p.length / 10));
          return p.filter((_, i) => i % stride === 0).slice(0, 10);
        }));
      }
      setStats(response.final_prices || null);
      setRunCount((v) => v + 1);
    } finally {
      setLoading(false);
    }
  };

  const lineSeries = paths[0].map((_, i) => ({
    step: i * 28,
    p1: paths[0][i],
    p2: paths[1][i],
    p3: paths[2][i],
    p4: paths[3][i],
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">Geometric Brownian Motion Scenario Modeling</h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {[
          { key: "S0", label: "Initial Price", type: "number", step: 1 },
          { key: "mu", label: "Drift", type: "number", step: 0.0001 },
          { key: "sigma", label: "Volatility", type: "number", step: 0.001 },
          { key: "T", label: "Time (years)", type: "number", step: 0.1 },
          { key: "n_steps", label: "Steps", type: "number", step: 1 },
          { key: "n_sims", label: "Paths", type: "number", step: 1 },
        ].map((f) => (
          <div key={f.key}>
            <label className="mb-1 block text-xs text-slate-400">{f.label}</label>
            <input
              type={f.type}
              step={f.step}
              value={(params as any)[f.key]}
              onChange={(e) =>
                setParams({ ...params, [f.key]: parseFloat(e.target.value) || 0 })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 tabular-nums"
            />
          </div>
        ))}
      </div>
      <button onClick={runSimulation} disabled={loading} className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50">
        {loading ? "Running..." : "Run GBM"}
      </button>
      {limitMessage && <p className="text-sm text-amber-300">{limitMessage}</p>}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 lg:col-span-2">
          <h3 className="mb-3 text-sm text-slate-300">GBM Path Surface (sample trajectories)</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineSeries}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis dataKey="step" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip />
                <Line dataKey="p1" stroke="#22d3ee" dot={false} strokeWidth={2} />
                <Line dataKey="p2" stroke="#818cf8" dot={false} strokeWidth={1.7} />
                <Line dataKey="p3" stroke="#f43f5e" dot={false} strokeWidth={1.7} />
                <Line dataKey="p4" stroke="#34d399" dot={false} strokeWidth={1.7} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-sm">
          <h3 className="mb-3 text-slate-300">Distribution Snapshot</h3>
          <dl className="space-y-2 text-slate-200 tabular-nums">
            <div className="flex justify-between"><dt>Mean Terminal Price</dt><dd>{stats?.mean?.toFixed(2) ?? "231.48"}</dd></div>
            <div className="flex justify-between"><dt>Median</dt><dd>{stats?.median?.toFixed(2) ?? "229.92"}</dd></div>
            <div className="flex justify-between"><dt>Std Dev</dt><dd>{stats?.std?.toFixed(2) ?? "24.31"}</dd></div>
            <div className="flex justify-between"><dt>5th Percentile</dt><dd>{stats?.p05?.toFixed(2) ?? "198.33"}</dd></div>
            <div className="flex justify-between"><dt>95th Percentile</dt><dd>{stats?.p95?.toFixed(2) ?? "269.41"}</dd></div>
            <div className="flex justify-between"><dt>Max Terminal</dt><dd>{stats?.max?.toFixed(2) ?? "292.18"}</dd></div>
          </dl>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <Plot
          data={[
            {
              x: [180, 195, 210, 225, 240, 255, 270, 285],
              y: [0.02, 0.06, 0.11, 0.19, 0.24, 0.18, 0.13, 0.07],
              type: "bar",
              marker: { color: "#14b8a6" },
              name: "Terminal Price Density",
            },
          ]}
          layout={{
            height: 280,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#cbd5e1" },
            margin: { l: 40, r: 20, t: 20, b: 40 },
            xaxis: { title: "Terminal Price", gridcolor: "#1e293b" },
            yaxis: { title: "Probability", gridcolor: "#1e293b" },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%" }}
        />
      </div>
    </div>
  );
}
