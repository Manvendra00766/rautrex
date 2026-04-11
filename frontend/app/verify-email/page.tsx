"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { verifyUserEmail } from "../lib/auth";

function VerifyEmailContent() {
  const params = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Verifying your email...");

  useEffect(() => {
    const run = async () => {
      if (!token) {
        setStatus("error");
        setMessage("Verification token is missing.");
        return;
      }
      try {
        const res = await verifyUserEmail(token);
        setStatus("success");
        setMessage(res.message || "Email verified.");
      } catch (err: any) {
        setStatus("error");
        setMessage(err.message);
      }
    };
    run();
  }, [token]);

  return (
    <div className="mx-auto max-w-xl px-6 py-16 text-slate-100">
      <h1 className="text-3xl font-bold">Email Verification</h1>
      <p className={`mt-4 ${status === "error" ? "text-red-300" : status === "success" ? "text-emerald-300" : "text-slate-300"}`}>
        {message}
      </p>
      <div className="mt-8">
        <Link href="/onboarding" className="rounded-md bg-cyan-500 px-4 py-2 font-semibold text-slate-950">
          Go to Onboarding
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-xl px-6 py-16 text-slate-100">Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
