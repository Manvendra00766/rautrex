"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "../app/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/live", label: "🔴 Live" },
  { href: "/data", label: "Market Data" },
  { href: "/simulate", label: "Simulate" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/risk", label: "Risk" },
  { href: "/strategy", label: "Strategy" },
  { href: "/predict", label: "Predict" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-900 text-slate-200 flex flex-col">
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white">Rautrex</h1>
        <p className="text-xs text-slate-400 mt-1">Quant Platform</p>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block px-6 py-2.5 text-sm hover:bg-slate-800 transition-colors ${
              pathname === item.href
                ? "bg-slate-800 text-white border-r-2 border-blue-500"
                : ""
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-700">
        <button
          onClick={logout}
          className="w-full text-sm px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
