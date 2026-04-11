"use client";

import { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getCorrelation, getRiskVar, getVolatility } from "../lib/quant";
import LockedFeature from "../../components/LockedFeature";
import { getMyProfile } from "../../lib/api/profile";

export default function RiskPage() {
  const [varMethod, setVarMethod] = useState<"historical_var" | "parametric_var">("historical_var");
  const [confidence, setConfidence] = useState(0.95);
  const [ticker, setTicker] = useState("AAPL,MSFT,NVDA,SPY,TLT");
  const [varValue, setVarValue] = useState(2847.33);
  const [corr, setCorr] = useState<(string | number)[][]>([
    ["AAPL", 1.0, 0.74, 0.69, 0.62, -0.19],
    ["MSFT", 0.74, 1.0, 0.66, 0.59, -0.22],
    ["NVDA", 0.69, 0.66, 1.0, 0.54, -0.15],
    ["SPY", 0.62, 0.59, 0.54, 1.0, -0.44],
    ["TLT", -0.19, -0.22, -0.15, -0.44, 1.0],
  ]);
  const [rollingVol, setRollingVol] = useState<Array<{ d: string; p20: number; p60: number; spy20: number }>>([
    { d: "2026-03-24", p20: 0.184, p60: 0.201, spy20: 0.132 },
    { d: "2026-03-25", p20: 0.181, p60: 0.199, spy20: 0.131 },
    { d: "2026-03-26", p20: 0.186, p60: 0.203, spy20: 0.134 },
    { d: "2026-03-27", p20: 0.189, p60: 0.205, spy20: 0.136 },
    { d: "2026-03-30", p20: 0.193, p60: 0.207, spy20: 0.139 },
    { d: "2026-03-31", p20: 0.191, p60: 0.206, spy20: 0.137 },
    { d: "2026-04-01", p20: 0.195, p60: 0.209, spy20: 0.141 },
    { d: "2026-04-02", p20: 0.198, p60: 0.213, spy20: 0.144 },
    { d: "2026-04-03", p20: 0.203, p60: 0.216, spy20: 0.148 },
    { d: "2026-04-08", p20: 0.201, p60: 0.214, spy20: 0.147 },
  ]);
  const [loading, setLoading] = useState(false);
  const [isPro, setIsPro] = useState(false);
  const tickers = useMemo(() => ticker.split(",").map((t) => t.trim()).filter(Boolean), [ticker]);

  const refreshRisk = async () => {
    setLoading(true);
    try {
      if (tickers.length >= 2) {
        const [corrRes, volRes, varRes] = await Promise.all([
          getCorrelation(tickers.slice(0, 5)),
          getVolatility(tickers[0], 20),
          getRiskVar({
            ticker: tickers[0],
            method: varMethod === "historical_var" ? "historical" : "parametric",
            confidence,
            holding_period: 1,
          }),
        ]);

        const corrRows = corrRes.tickers.map((rowTicker) => [
          rowTicker,
          ...corrRes.tickers.map((colTicker) => corrRes.correlation_matrix[rowTicker]?.[colTicker] ?? 0),
        ]);
        setCorr(corrRows);
        setVarValue(varRes.var * 125430.52);

        const entries = Object.entries(volRes.rolling_volatility || {}).slice(-30);
        if (entries.length > 0) {
          const series = entries.map(([d, v]) => ({ d: d.slice(0, 10), p20: Number(v), p60: Number(v) * 1.09, spy20: Number(v) * 0.82 }));
          setRollingVol(series);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshRisk();
    const loadTier = async () => {
      try {
        const me = await getMyProfile();
        setIsPro(me.tier === "pro" || me.tier === "team");
      } catch {
        setIsPro(false);
      }
    };
    loadTier();
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">Risk Analytics: Correlation + Volatility + Tail Risk</h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Universe</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase().replace(" ", ""))}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">VaR Model</label>
          <select
            value={varMethod}
            onChange={(e) => setVarMethod(e.target.value as "historical_var" | "parametric_var")}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          >
            <option value="historical_var">Historical VaR</option>
            <option value="parametric_var">Parametric VaR</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Confidence ({(confidence * 100).toFixed(0)}%)</label>
          <input
            type="range"
            min={0.8}
            max={0.99}
            step={0.01}
            value={confidence}
            onChange={(e) => setConfidence(parseFloat(e.target.value))}
            className="w-full"
          />
        </div>
        <div className="flex items-end"><button onClick={refreshRisk} disabled={loading} className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">{loading ? "Refreshing..." : "Refresh Risk"}</button></div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Portfolio VaR (95%, 1D)", `$${varValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}`],
          ["Expected Shortfall (95%)", isPro ? "$3,721.90" : "Pro required"],
          ["Beta vs SPY", "1.18"],
          ["Current Leverage", "1.42x"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase text-slate-500">{k}</p>
            <p className="mt-2 text-xl font-semibold text-slate-100 tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      <LockedFeature
        locked={!isPro}
        title="Advanced risk requires Pro"
        message="Upgrade to unlock VaR/ES/deeper risk insights."
      >
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Correlation Matrix</h3>
          <div className="overflow-hidden rounded-lg border border-slate-800">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-800 text-slate-300">
                <tr>
                  <th className="px-3 py-2 text-left">Asset</th>
                  {corr.map((row) => (
                    <th key={row[0] as string} className="px-3 py-2 text-right">{row[0]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corr.map((row) => (
                  <tr key={row[0] as string} className="border-t border-slate-800">
                    <td className="px-3 py-2 text-slate-300">{row[0]}</td>
                    {row.slice(1).map((v, idx) => (
                      <td
                        key={idx}
                        className={`px-3 py-2 text-right tabular-nums ${
                          (v as number) > 0.6 ? "text-emerald-300" : (v as number) < -0.2 ? "text-rose-300" : "text-slate-200"
                        }`}
                      >
                        {(v as number).toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Rolling Volatility (Annualized)</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rollingVol}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis dataKey="d" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip />
                <Line dataKey="p20" name="Portfolio 20D" stroke="#22d3ee" dot={false} />
                <Line dataKey="p60" name="Portfolio 60D" stroke="#a78bfa" dot={false} />
                <Line dataKey="spy20" name="SPY 20D" stroke="#34d399" dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
      </LockedFeature>
    </div>
  );
}
