import Link from "next/link";

const features = [
  { title: "Backtesting", desc: "Run momentum, mean-reversion, and crossover strategies with trade cost modeling." },
  { title: "Monte Carlo Simulation", desc: "Generate GBM and Brownian scenarios for stress and probability analysis." },
  { title: "Options Pricing", desc: "Price contracts with Black-Scholes plus full Greeks and implied volatility tools." },
  { title: "Risk Analytics", desc: "Track VaR, Expected Shortfall, volatility, drawdown, and portfolio risk metrics." },
  { title: "ML Signals", desc: "Build directional signals with time-series feature engineering and walk-forward validation." },
  { title: "Live Data", desc: "Monitor market feeds and pipeline updates in one workspace." },
];

const plans = [
  { name: "Free", price: "$0", users: "1 user", features: ["Core analytics", "Community support", "Basic data usage"] },
  { name: "Pro", price: "$29/mo", users: "1 user", features: ["Advanced backtests", "Priority compute", "ML signal tools"] },
  { name: "Team", price: "$99/mo", users: "Up to 5 users", features: ["Shared workspaces", "Usage controls", "Priority support"] },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <div className="text-lg font-semibold">Rautrex</div>
          <div className="hidden items-center gap-6 text-sm text-slate-300 md:flex">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <Link href="/login">Login</Link>
            <Link href="/register" className="rounded-md bg-cyan-500 px-3 py-2 font-medium text-slate-950">Get Started</Link>
          </div>
        </nav>
      </header>

      <section className="mx-auto w-full max-w-6xl px-6 py-20 text-center">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Institutional-grade quant tools. Built for independent traders.</h1>
        <p className="mx-auto mt-4 max-w-3xl text-slate-300">
          Backtesting, options pricing, risk analytics, and ML signals in one platform built for retail traders, students, and independent analysts.
        </p>
        <Link href="/register" className="mt-8 inline-block rounded-md bg-cyan-500 px-6 py-3 font-semibold text-slate-950">
          Start Free — No Credit Card Required
        </Link>
      </section>

      <section id="features" className="mx-auto grid w-full max-w-6xl gap-4 px-6 pb-16 md:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => (
          <article key={feature.title} className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <h3 className="text-lg font-semibold">{feature.title}</h3>
            <p className="mt-2 text-sm text-slate-300">{feature.desc}</p>
          </article>
        ))}
      </section>

      <section id="pricing" className="mx-auto w-full max-w-6xl px-6 pb-16">
        <h2 className="text-2xl font-semibold">Pricing</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <article key={plan.name} className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">{plan.name}</h3>
              <p className="mt-2 text-2xl font-bold">{plan.price}</p>
              <p className="mt-1 text-sm text-slate-300">{plan.users}</p>
              <ul className="mt-4 space-y-2 text-sm text-slate-300">
                {plan.features.map((item) => <li key={item}>• {item}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-6 pb-20">
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
          <p className="text-sm text-slate-300">Trusted by 1,500+ independent analysts</p>
          <p className="mt-3 text-slate-400">Testimonials coming soon.</p>
        </div>
      </section>
    </main>
  );
}
