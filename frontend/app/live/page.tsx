"use client";

import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getIntraday, getLiveQuote, getMarketStatus } from "../lib/quant";

export default function LivePage() {
  const [ticker, setTicker] = useState("AAPL");
  const [tape, setTape] = useState([
    { t: "15:10:00", px: 222.31 },
    { t: "15:12:00", px: 222.46 },
    { t: "15:14:00", px: 222.58 },
    { t: "15:16:00", px: 222.79 },
    { t: "15:18:00", px: 222.72 },
    { t: "15:20:00", px: 222.84 },
    { t: "15:22:00", px: 222.93 },
    { t: "15:24:00", px: 223.01 },
  ]);
  const [quote, setQuote] = useState<any>(null);
  const [status, setStatus] = useState<{ is_open: boolean; market_state: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [quoteRes, intradayRes, statusRes] = await Promise.all([
        getLiveQuote(ticker),
        getIntraday(ticker, "15m", "1d"),
        getMarketStatus(),
      ]);
      setQuote(quoteRes);
      setStatus(statusRes);
      const points = (intradayRes.records || [])
        .slice(-24)
        .map((r) => ({ t: String(r.datetime).slice(11, 19), px: Number(r.close) }));
      if (points.length > 0) setTape(points);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const cards = useMemo(
    () => [
      ["Last Price", quote?.current_price ? `$${Number(quote.current_price).toFixed(2)}` : "$222.84"],
      [
        "Session Change",
        quote?.change != null && quote?.change_percent != null
          ? `${Number(quote.change) >= 0 ? "+" : ""}$${Math.abs(Number(quote.change)).toFixed(2)} (${Number(quote.change_percent).toFixed(2)}%)`
          : "+$1.12 (+0.51%)",
      ],
      ["Bid/Ask Spread", "$0.03"],
      ["Session Volume", quote?.volume ? Number(quote.volume).toLocaleString() : "59,320,118"],
    ],
    [quote]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm text-slate-300">WebSocket-Ready Live Monitoring</h2>
        <div className={`rounded px-2 py-1 text-xs ${status?.is_open ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"}`}>
          {status ? `${status.market_state} • Stream Connected` : "Stream Connected • 15:24:12 ET"}
        </div>
      </div>

      <div className="flex gap-3">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          className="w-36 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          placeholder="Ticker"
        />
        <button onClick={refresh} disabled={loading} className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50">{loading ? "Loading..." : "Subscribe"}</button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {cards.map(([k, v]) => (
          <article key={k} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs uppercase text-slate-500">{k}</p>
            <p className="mt-2 text-xl font-semibold text-slate-100 tabular-nums">{v}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 lg:col-span-2">
          <h3 className="mb-3 text-sm text-slate-300">{ticker} Intraday Microtrend</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={tape}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="px" stroke="#22d3ee" fill="#0e7490" fillOpacity={0.35} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <h3 className="mb-3 text-sm text-slate-300">Price Alerts</h3>
          <ul className="space-y-2 text-sm text-slate-200 tabular-nums">
            <li className="rounded border border-slate-800 bg-slate-950/70 p-2">AAPL &gt; $223.50 • Not triggered</li>
            <li className="rounded border border-slate-800 bg-slate-950/70 p-2">AAPL &lt; $220.00 • Not triggered</li>
            <li className="rounded border border-slate-800 bg-slate-950/70 p-2">SPY 5m move &gt; 0.65% • Triggered 14:42</li>
          </ul>
        </section>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/70">
        <h3 className="border-b border-slate-800 px-4 py-3 text-sm text-slate-300">Live Order Book ({ticker})</h3>
        <div className="grid grid-cols-2 gap-0">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-800 text-slate-300">
              <tr><th className="px-4 py-2 text-left">Bid Size</th><th className="px-4 py-2 text-right">Bid Price</th></tr>
            </thead>
            <tbody className="text-emerald-300">
              {[
                ["12,300", "222.83"],
                ["9,850", "222.82"],
                ["8,100", "222.81"],
                ["6,940", "222.80"],
                ["5,210", "222.79"],
              ].map((r) => (
                <tr key={r[1]} className="border-t border-slate-800">
                  <td className="px-4 py-2 tabular-nums">{r[0]}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{r[1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="min-w-full text-sm">
            <thead className="bg-slate-800 text-slate-300">
              <tr><th className="px-4 py-2 text-left">Ask Price</th><th className="px-4 py-2 text-right">Ask Size</th></tr>
            </thead>
            <tbody className="text-rose-300">
              {[
                ["222.86", "10,470"],
                ["222.87", "9,230"],
                ["222.88", "8,020"],
                ["222.89", "6,880"],
                ["222.90", "5,910"],
              ].map((r) => (
                <tr key={r[0]} className="border-t border-slate-800">
                  <td className="px-4 py-2 tabular-nums">{r[0]}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{r[1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
