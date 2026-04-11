"use client";

import Link from "next/link";
import { useTrialStore } from "../store/trialStore";

export default function TrialBanner() {
  const { onTrial, daysLeft, warningLevel, isExpired } = useTrialStore();
  if (!onTrial || isExpired) return null;

  const tone =
    warningLevel === "urgent"
      ? "bg-red-900/40 border-red-500/30 text-red-200"
      : warningLevel === "warning"
      ? "bg-amber-900/40 border-amber-500/30 text-amber-200"
      : "bg-indigo-900/40 border-indigo-500/30 text-indigo-200";

  return (
    <div className={`mb-4 rounded-lg border px-4 py-3 text-sm ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <span>
          {warningLevel === "urgent"
            ? `🔴 Trial expires ${daysLeft === 1 ? "tomorrow" : `in ${daysLeft} days`}`
            : warningLevel === "warning"
            ? `⚠️ ${daysLeft} days left in your trial`
            : `🎯 Pro Trial — ${daysLeft} days remaining`}
        </span>
        <Link href="/pricing" className="rounded bg-slate-900/60 px-3 py-1 text-xs font-semibold">
          Upgrade early →
        </Link>
      </div>
    </div>
  );
}
