"use client";

import Link from "next/link";
import { useState } from "react";
import { useTrialStore } from "../store/trialStore";

export default function TrialExpiredModal() {
  const { isExpired } = useTrialStore();
  const [dismissed, setDismissed] = useState(false);
  if (!isExpired || dismissed) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-900 p-6 text-center text-slate-100">
        <h2 className="text-2xl font-semibold">Your free trial has ended</h2>
        <p className="mt-2 text-sm text-slate-300">
          You had full Pro access for 60 days. Upgrade now to keep premium backtests, signals, and risk analytics.
        </p>
        <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded border border-slate-700 p-2">📊 Unlimited backtesting</div>
          <div className="rounded border border-slate-700 p-2">🤖 ML signals</div>
          <div className="rounded border border-slate-700 p-2">⚡ Options + Greeks</div>
          <div className="rounded border border-slate-700 p-2">🛡️ VaR / ES</div>
        </div>
        <div className="mt-6 flex flex-col gap-3">
          <Link href="/pricing" className="rounded bg-indigo-600 px-4 py-2 font-semibold">
            Upgrade to Pro — ₹799/month
          </Link>
          <button onClick={() => setDismissed(true)} className="text-sm text-slate-400">
            Continue with free tier
          </button>
        </div>
      </div>
    </div>
  );
}
