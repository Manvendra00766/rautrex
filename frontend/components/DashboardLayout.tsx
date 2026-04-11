"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChartCandlestick,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  LayoutDashboard,
  RadioTower,
  ShieldAlert,
  Sparkles,
  Target,
  Wallet,
} from "lucide-react";
import { logout } from "../app/lib/auth";
import TrialBanner from "./TrialBanner";
import TrialExpiredModal from "./TrialExpiredModal";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { name: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
  { name: "Market Data", icon: ChartCandlestick, href: "/data" },
  { name: "Simulate", icon: FlaskConical, href: "/simulate" },
  { name: "Portfolio", icon: Wallet, href: "/portfolio" },
  { name: "Risk Analysis", icon: ShieldAlert, href: "/risk" },
  { name: "Strategy", icon: Target, href: "/strategy" },
  { name: "Prediction", icon: Sparkles, href: "/predict" },
  { name: "Live Data", icon: RadioTower, href: "/live" },
] as const;

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const currentTitle = useMemo(
    () => navItems.find((item) => pathname.startsWith(item.href))?.name ?? "Rautrex",
    [pathname]
  );

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <aside
        className={`${
          collapsed ? "w-20" : "w-72"
        } border-r border-slate-800 bg-slate-900 transition-all duration-200`}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
            {!collapsed && (
              <div>
                <p className="text-lg font-semibold tracking-tight">Rautrex</p>
                <p className="text-xs text-slate-400">Quant Platform</p>
              </div>
            )}
            <button
              onClick={() => setCollapsed((v) => !v)}
              className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
              aria-label="Toggle sidebar"
            >
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>

          <nav className="flex-1 space-y-1 px-2 py-4">
            {navItems.map(({ name, icon: Icon, href }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`group flex items-center rounded-md px-3 py-2.5 text-sm transition-colors ${
                    active
                      ? "bg-slate-800 text-slate-100"
                      : "text-slate-300 hover:bg-slate-800/70 hover:text-slate-100"
                  }`}
                >
                  <Icon size={18} className={active ? "text-cyan-300" : "text-slate-400"} />
                  {!collapsed && <span className="ml-3">{name}</span>}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-slate-800 p-3">
            <button
              onClick={logout}
              className="flex w-full items-center justify-center rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
            >
              {collapsed ? "↩" : "Logout"}
            </button>
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-900/70 px-6">
          <div>
            <h1 className="text-base font-semibold tracking-wide">{currentTitle}</h1>
            <p className="text-xs text-slate-400">Live Session • US Equities + Macro</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-300 tabular-nums">
            <span>Session P&L: +$2,481.37</span>
            <span className="rounded bg-emerald-500/20 px-2 py-1 text-emerald-300">API Healthy</span>
          </div>
        </header>
        <section className="flex-1 overflow-y-auto p-6">
          <TrialBanner />
          {children}
          <TrialExpiredModal />
        </section>
      </main>
    </div>
  );
}
