"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from "recharts";
import { getData, getPredictSignal, trainPredictModel } from "../lib/quant";
import LockedFeature from "../../components/LockedFeature";
import { getMyProfile } from "../../lib/api/profile";

export default function PredictPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [model, setModel] = useState("xgboost");

  const [featureImportances, setFeatureImportances] = useState([
    { feature: "momentum_20d", importance: 0.238 },
    { feature: "realized_vol_10d", importance: 0.177 },
    { feature: "market_beta", importance: 0.158 },
    { feature: "term_spread", importance: 0.134 },
    { feature: "rsi_14", importance: 0.119 },
    { feature: "earnings_drift", importance: 0.094 },
    { feature: "oi_put_call", importance: 0.080 },
  ]);
  const [signal, setSignal] = useState("BULLISH");
  const [probability, setProbability] = useState(68.4);
  const [expectedReturn, setExpectedReturn] = useState(0.72);
  const [loading, setLoading] = useState(false);
  const [isPro, setIsPro] = useState(false);

  useEffect(() => {
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

  const [predVsActual, setPredVsActual] = useState([
    { d: "2026-03-28", pred: 0.42, actual: 0.36 },
    { d: "2026-03-29", pred: 0.58, actual: 0.61 },
    { d: "2026-03-30", pred: -0.31, actual: -0.27 },
    { d: "2026-03-31", pred: 0.77, actual: 0.82 },
    { d: "2026-04-01", pred: 0.15, actual: 0.11 },
    { d: "2026-04-02", pred: -0.49, actual: -0.54 },
    { d: "2026-04-03", pred: 0.26, actual: 0.32 },
    { d: "2026-04-04", pred: 0.44, actual: 0.39 },
    { d: "2026-04-05", pred: 0.09, actual: 0.04 },
    { d: "2026-04-08", pred: 0.68, actual: 0.72 },
  ]);

  const run = async () => {
    setLoading(true);
    try {
      const [trainRes, signalRes, dataRes] = await Promise.all([
        trainPredictModel(ticker),
        getPredictSignal(ticker),
        getData(ticker),
      ]);
      const fi = Object.entries(trainRes.feature_importances || {})
        .map(([feature, importance]) => ({ feature, importance: Number(importance) }))
        .sort((a, b) => b.importance - a.importance)
        .slice(0, 7);
      if (fi.length > 0) setFeatureImportances(fi);
      const pUp = (signalRes.probability_up || 0) * 100;
      setProbability(pUp);
      setSignal(signalRes.signal === "UP" ? "BULLISH" : "BEARISH");
      setExpectedReturn((pUp - 50) / 25);

      const rows = (dataRes.records || []).slice(-10).map((r) => ({
        d: String(r.date).slice(0, 10),
        actual: Number((r.simple_return || 0) * 100),
        pred: Number((signalRes.probability_up - 0.5) * 2),
      }));
      if (rows.length > 0) setPredVsActual(rows);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">ML Signals, Explainability, and Prediction Diagnostics</h2>

      <div className="flex gap-3">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          className="w-32 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          placeholder="Ticker"
        />
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
        >
          <option value="random_forest">Random Forest</option>
          <option value="xgboost">XGBoost</option>
          <option value="logistic_regression">Logistic Regression</option>
        </select>
        <button onClick={run} disabled={loading} className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50">{loading ? "Running..." : "Run Model"}</button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Signal", signal],
          ["Probability Up", `${probability.toFixed(1)}%`],
          ["Expected 1D Return", `${expectedReturn >= 0 ? "+" : ""}${expectedReturn.toFixed(2)}%`],
          ["Model MAE (30D)", "0.19%"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase text-slate-500">{k}</p>
            <p className="mt-2 text-xl font-semibold text-slate-100 tabular-nums">{v}</p>
          </div>
        ))}
      </div>

      <LockedFeature
        locked={!isPro}
        title="ML Signals are Pro-only"
        message="Upgrade to Pro to unlock unlimited model runs and signal diagnostics."
      >
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Feature Importance</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={featureImportances} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis type="category" dataKey="feature" tick={{ fill: "#94a3b8", fontSize: 11 }} width={110} />
              <Tooltip />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                {featureImportances.map((_, i) => (
                  <Cell key={i} fill={i === 0 ? "#22d3ee" : "#6366f1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Predicted vs Actual Returns (%)</h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={predVsActual}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="d" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip />
              <Line dataKey="pred" stroke="#22d3ee" strokeWidth={2.1} dot={false} />
              <Line dataKey="actual" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </div>
      </LockedFeature>
    </div>
  );
}
