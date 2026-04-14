"use client";

import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function DataPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1d");
  const [priceData] = useState<Array<{ date: string; open: number; high: number; low: number; close: number; volume: number }>>([
    { date: "2026-04-08", open: 220.5, high: 225.3, low: 219.8, close: 224.2, volume: 45230000 },
    { date: "2026-04-09", open: 224.2, high: 228.7, low: 223.5, close: 227.1, volume: 52100000 },
    { date: "2026-04-10", open: 227.1, high: 232.4, low: 226.8, close: 230.5, volume: 48900000 },
    { date: "2026-04-11", open: 230.5, high: 231.2, low: 226.1, close: 228.3, volume: 41200000 },
    { date: "2026-04-14", open: 228.3, high: 234.1, low: 227.9, close: 232.8, volume: 55600000 },
  ]);
  const [stats] = useState({
    current: 232.8,
    open: 228.3,
    high52w: 288.95,
    low52w: 126.45,
    marketCap: "2.33T",
    pe: 28.4,
    div: 0.88,
  });

  return (
    <div className="space-y-6">
      <h2 className="text-sm text-slate-300">Market Data • Live Quotes & Historical Prices</h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Symbol</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="AAPL, MSFT, SPY"
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Timeframe</label>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          >
            <option value="1h">1 Hour</option>
            <option value="1d">1 Day</option>
            <option value="1w">1 Week</option>
            <option value="1mo">1 Month</option>
          </select>
        </div>
        <div className="col-span-2 flex items-end gap-2">
          <button className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400">
            Refresh
          </button>
          <button className="rounded-md border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800">
            Add to Watchlist
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Current Price", `$${stats.current.toFixed(2)}`],
          ["Open", `$${stats.open.toFixed(2)}`],
          ["52W High", `$${stats.high52w.toFixed(2)}`],
          ["52W Low", `$${stats.low52w.toFixed(2)}`],
          ["Market Cap", stats.marketCap],
          ["P/E Ratio", stats.pe.toFixed(1)],
          ["Dividend Yield", `${stats.div.toFixed(2)}%`],
          ["Volume", "52.1M"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
            <p className="text-xs uppercase text-slate-500">{label}</p>
            <p className="mt-2 text-lg font-semibold text-slate-100 tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <h3 className="mb-4 text-sm text-slate-300">Price Chart ({timeframe})</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={priceData}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis domain={["dataMin - 5", "dataMax + 5"]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                labelStyle={{ color: "#cbd5e1" }}
              />
              <Line
                dataKey="close"
                stroke="#22d3ee"
                dot={false}
                strokeWidth={2}
                name="Close Price"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <h3 className="mb-4 text-sm text-slate-300">OHLCV Data</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-700 bg-slate-800/50">
              <tr>
                <th className="px-4 py-2 text-left text-slate-400">Date</th>
                <th className="px-4 py-2 text-right text-slate-400">Open</th>
                <th className="px-4 py-2 text-right text-slate-400">High</th>
                <th className="px-4 py-2 text-right text-slate-400">Low</th>
                <th className="px-4 py-2 text-right text-slate-400">Close</th>
                <th className="px-4 py-2 text-right text-slate-400">Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {priceData.map((row) => (
                <tr key={row.date} className="hover:bg-slate-800/30">
                  <td className="px-4 py-2 text-slate-300">{row.date}</td>
                  <td className="px-4 py-2 text-right text-slate-200 tabular-nums">${row.open.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-emerald-300 tabular-nums">${row.high.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-rose-300 tabular-nums">${row.low.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-slate-200 tabular-nums font-medium">${row.close.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right text-slate-300 tabular-nums">{(row.volume / 1000000).toFixed(1)}M</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
