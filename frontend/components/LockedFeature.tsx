"use client";

import Link from "next/link";
import { ReactNode } from "react";

export default function LockedFeature({
  locked,
  title = "Upgrade to Pro",
  message = "This feature requires a paid tier.",
  children,
}: {
  locked: boolean;
  title?: string;
  message?: string;
  children: ReactNode;
}) {
  if (!locked) return <>{children}</>;
  return (
    <div className="relative">
      <div className="pointer-events-none select-none blur-sm opacity-60">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="rounded-lg border border-cyan-500/40 bg-slate-950/90 p-4 text-center">
          <p className="text-sm font-semibold text-cyan-300">{title}</p>
          <p className="mt-1 text-xs text-slate-300">{message}</p>
          <Link href="/profile" className="mt-3 inline-block rounded bg-cyan-500 px-3 py-1 text-xs font-semibold text-slate-950">
            Upgrade
          </Link>
        </div>
      </div>
    </div>
  );
}
