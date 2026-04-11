"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { runBacktest } from "../lib/quant";
import { updateOnboarding } from "../../lib/api/profile";

const personas = ["Trader", "Student", "Analyst", "Developer"] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [persona, setPersona] = useState<(typeof personas)[number]>("Trader");
  const [backtestResult, setBacktestResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const progress = (step / 3) * 100;

  const runFirstBacktest = async () => {
    setLoading(true);
    try {
      const res = await runBacktest({
        ticker: "RELIANCE.NS",
        start: new Date(Date.now() - 365 * 24 * 3600 * 1000).toISOString().slice(0, 10),
        strategy: "ma_cross",
        transaction_cost: 0.001,
      });
      setBacktestResult(res);
      setStep(3);
    } catch {
      setBacktestResult({ total_return: 0, annualized_sharpe: 0 });
      setStep(3);
    } finally {
      setLoading(false);
    }
  };

  const finish = async () => {
    await updateOnboarding({ persona, onboarding_completed: true });
    router.push("/dashboard");
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 text-slate-100">
      <div className="mb-6 h-2 w-full rounded bg-slate-800"><div className="h-2 rounded bg-cyan-500" style={{ width: `${progress}%` }} /></div>
      <div className="mb-6 flex justify-end">
        <button onClick={() => router.push("/dashboard")} className="text-xs text-slate-400 underline">Skip</button>
      </div>
      {step === 1 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-2xl font-semibold">What are you?</h1>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {personas.map((p) => (
              <button key={p} onClick={() => setPersona(p)} className={`rounded border px-3 py-2 text-left ${persona === p ? "border-cyan-400 bg-cyan-500/10" : "border-slate-700"}`}>
                {p}
              </button>
            ))}
          </div>
          <button onClick={() => setStep(2)} className="mt-6 rounded bg-cyan-500 px-4 py-2 font-semibold text-slate-950">Continue</button>
        </div>
      )}
      {step === 2 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-2xl font-semibold">Run your first backtest</h1>
          <p className="mt-2 text-sm text-slate-300">Preset: RELIANCE (1Y), MA Crossover.</p>
          <button onClick={runFirstBacktest} disabled={loading} className="mt-6 rounded bg-cyan-500 px-4 py-2 font-semibold text-slate-950">
            {loading ? "Running..." : "Run Backtest"}
          </button>
        </div>
      )}
      {step === 3 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-2xl font-semibold">Your trial is active</h1>
          <p className="mt-2 text-sm text-slate-300">Full Pro access is unlocked for 60 days. No payment needed until trial end.</p>
          {backtestResult && (
            <div className="mt-4 rounded border border-slate-700 p-3 text-sm">
              <p>Total Return: {(Number(backtestResult.total_return || 0) * 100).toFixed(2)}%</p>
              <p>Sharpe: {Number(backtestResult.annualized_sharpe || 0).toFixed(2)}</p>
            </div>
          )}
          <div className="mt-4 rounded border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200">
            ✅ Unlimited backtests • ✅ ML signals • ✅ Options + Greeks • ✅ Full risk suite
          </div>
          <div className="mt-6 flex gap-3">
            <button onClick={finish} className="rounded bg-cyan-500 px-4 py-2 font-semibold text-slate-950">Go to Dashboard →</button>
          </div>
        </div>
      )}
    </div>
  );
}
