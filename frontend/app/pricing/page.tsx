"use client";

import Link from "next/link";
import { useState } from "react";
import CheckoutButton from "../../components/CheckoutButton";

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  return (
    <main className="mx-auto max-w-6xl px-6 py-14 text-slate-100">
      <h1 className="text-4xl font-bold">Simple pricing for growing quant teams</h1>
      <p className="mt-3 text-slate-300">Choose monthly or annual billing. Annual saves ~17%.</p>

      <div className="mt-8 inline-flex rounded-md border border-slate-700 bg-slate-900 p-1 text-sm">
        <button onClick={() => setAnnual(false)} className={`rounded px-3 py-1 ${!annual ? "bg-cyan-500 text-slate-950" : "text-slate-300"}`}>Monthly</button>
        <button onClick={() => setAnnual(true)} className={`rounded px-3 py-1 ${annual ? "bg-cyan-500 text-slate-950" : "text-slate-300"}`}>Annual</button>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-xl font-semibold">Free</h2>
          <p className="mt-2 text-3xl font-bold">₹0</p>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            <li>✓ 3 backtests/day</li>
            <li>✓ 1 ticker</li>
            <li>✓ 2 simulations/day</li>
            <li>✓ Basic options + risk</li>
          </ul>
          <Link href="/register" className="mt-6 block rounded-md bg-cyan-500 px-4 py-2 text-center font-semibold text-slate-950">Start Free</Link>
        </article>

        <article className="relative rounded-xl border border-indigo-500 bg-slate-900/70 p-6">
          <span className="absolute right-4 top-4 rounded bg-indigo-500 px-2 py-1 text-xs font-semibold">Most Popular</span>
          <h2 className="text-xl font-semibold">Pro</h2>
          <p className="mt-2 text-3xl font-bold">{annual ? "₹7,999/yr" : "₹799/mo"}</p>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            <li>✓ Unlimited backtests/simulations</li>
            <li>✓ 10 tickers</li>
            <li>✓ Full Greeks + IV</li>
            <li>✓ Full risk + ML signals</li>
          </ul>
          <div className="mt-6">
            <CheckoutButton plan={annual ? "pro_annual" : "pro_monthly"} label="Upgrade to Pro" />
          </div>
        </article>

        <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-xl font-semibold">Team</h2>
          <p className="mt-2 text-3xl font-bold">₹2,499/mo</p>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            <li>✓ Everything in Pro</li>
            <li>✓ 5 seats</li>
            <li>✓ API access</li>
            <li>✓ 10 years data history</li>
          </ul>
          <div className="mt-6">
            <CheckoutButton plan="team_monthly" label="Upgrade to Team" />
          </div>
        </article>
      </div>

      <section className="mt-14">
        <h3 className="text-2xl font-semibold">FAQ</h3>
        <div className="mt-4 space-y-3 text-sm text-slate-300">
          <p><strong>Can I cancel anytime?</strong> Yes, you can cancel from billing settings.</p>
          <p><strong>Is my data secure?</strong> Yes, data is encrypted in transit and protected by auth controls.</p>
          <p><strong>Do you support Indian stocks?</strong> Yes, NSE/BSE tickers are supported in workflows.</p>
        </div>
      </section>
    </main>
  );
}
