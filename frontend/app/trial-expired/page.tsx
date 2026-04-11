"use client";

import Link from "next/link";

export default function TrialExpiredPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 text-center text-slate-100">
      <h1 className="text-3xl font-bold">Your free trial has ended</h1>
      <p className="mt-3 text-slate-300">
        Upgrade to keep unlimited backtesting, ML signals, options pricing, and full risk analytics.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/pricing" className="rounded bg-indigo-600 px-4 py-2 font-semibold">Upgrade to Pro</Link>
        <Link href="/dashboard" className="rounded border border-slate-600 px-4 py-2">Continue free</Link>
      </div>
    </div>
  );
}
