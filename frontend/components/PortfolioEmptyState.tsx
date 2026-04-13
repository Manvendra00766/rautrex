"use client";

import React from "react";

interface PortfolioEmptyStateProps {
  onCreatePortfolio?: () => void;
}

export default function PortfolioEmptyState({ onCreatePortfolio }: PortfolioEmptyStateProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4">
      <div className="w-full max-w-md">
        {/* Card Container */}
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/80 to-slate-800/50 p-8 backdrop-blur-sm shadow-2xl">
          {/* Icon/Illustration */}
          <div className="mb-6 flex justify-center">
            <div className="rounded-full bg-gradient-to-br from-cyan-500/20 to-blue-500/20 p-4 border border-cyan-500/30">
              <svg
                className="w-8 h-8 text-cyan-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7H6v10h7V7zM13 7V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h6a2 2 0 002-2v-2M13 7l4-4m0 0l4 4m-4-4v10"
                />
              </svg>
            </div>
          </div>

          {/* Content */}
          <h1 className="mb-3 text-center text-2xl font-bold text-slate-100">
            No Portfolio Yet
          </h1>
          <p className="mb-8 text-center text-sm text-slate-400">
            Create your first portfolio to start tracking performance, analyzing risk, and executing strategies.
          </p>

          {/* Stats Placeholder */}
          <div className="mb-8 grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-500 uppercase">Total Value</p>
              <p className="mt-1 text-lg font-semibold text-slate-400">--</p>
            </div>
            <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-500 uppercase">Daily P&L</p>
              <p className="mt-1 text-lg font-semibold text-slate-400">--</p>
            </div>
            <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-500 uppercase">Return</p>
              <p className="mt-1 text-lg font-semibold text-slate-400">--</p>
            </div>
            <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-500 uppercase">VaR (95%)</p>
              <p className="mt-1 text-lg font-semibold text-slate-400">--</p>
            </div>
          </div>

          {/* CTA Button */}
          <button
            onClick={onCreatePortfolio}
            className="w-full rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 px-4 py-3 text-sm font-semibold text-slate-950 transition-all duration-200 hover:from-cyan-400 hover:to-blue-400 hover:shadow-lg hover:shadow-cyan-500/20 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
          >
            Create Portfolio
          </button>

          {/* Info Text */}
          <p className="mt-6 text-center text-xs text-slate-500">
            Add your holdings, track metrics, and monitor risk in real-time.
          </p>
        </div>
      </div>
    </div>
  );
}
