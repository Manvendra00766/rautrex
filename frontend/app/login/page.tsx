"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { beginLoginOtp, beginSignupOtp, completeLoginOtp, completeSignupOtp } from "../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [otpMode, setOtpMode] = useState<"login" | "signup" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (mode: "login" | "signup", stage: "request" | "verify") => {
    setError(null);
    setLoading(true);
    try {
      if (!email.toLowerCase().endsWith("@gmail.com")) {
        throw new Error("Email must be a valid @gmail.com address.");
      }
      if (stage === "request") {
        if (mode === "login") {
          const res = await beginLoginOtp(email, password);
          setChallengeId(res.challenge_id);
          setOtpMode("login");
        } else {
          const res = await beginSignupOtp(email, password, phoneNumber);
          setChallengeId(res.challenge_id);
          setOtpMode("signup");
        }
      } else {
        if (!challengeId || !otpCode) {
          throw new Error("Enter OTP code first.");
        }
        if (mode === "login") {
          await completeLoginOtp(email, password, challengeId, otpCode);
        } else {
          await completeSignupOtp(email, password, phoneNumber, challengeId, otpCode);
        }
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
      <div className="mx-auto grid w-full max-w-5xl gap-8 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
          <h1 className="text-3xl font-semibold tracking-tight">Rautrex Terminal</h1>
          <p className="mt-2 text-sm text-slate-400">Secure JWT access to quant research, risk, and execution tools.</p>
          <div className="mt-8 grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase text-slate-500">Portfolio NAV</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">$125,430.52</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase text-slate-500">Today P&L</p>
              <p className="mt-1 text-xl font-semibold text-emerald-300 tabular-nums">+$2,481.37</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase text-slate-500">Sharpe (30D)</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">1.85</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase text-slate-500">95% VaR (1D)</p>
              <p className="mt-1 text-xl font-semibold text-amber-300 tabular-nums">$2,847.33</p>
            </div>
          </div>
        </section>

        <section className="w-full rounded-2xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-bold">Sign in</h2>
          <p className="mb-6 mt-1 text-sm text-slate-400">Use your @gmail.com credentials. OTP will be sent to email and mobile.</p>

          {error && <div className="mb-4 rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Phone Number</label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                placeholder="+1 415 555 0198"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                placeholder="yourname@gmail.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                placeholder="••••••••••••"
              />
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => handleSubmit("login", "request")}
                disabled={loading || !email || !password}
                className="flex-1 rounded-md bg-cyan-500 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
              >
                {loading && otpMode !== "signup" ? "Sending OTP..." : "Login (Send OTP)"}
              </button>
              <button
                onClick={() => handleSubmit("signup", "request")}
                disabled={loading || !email || !password || !phoneNumber}
                className="flex-1 rounded-md border border-slate-600 bg-slate-800 py-2 text-sm font-medium hover:bg-slate-700 disabled:opacity-50"
              >
                {loading && otpMode !== "login" ? "Sending OTP..." : "Sign Up (Send OTP)"}
              </button>
            </div>
            {challengeId && (
              <div className="rounded-md border border-cyan-800 bg-cyan-950/20 p-3">
                <label className="mb-1 block text-sm font-medium text-slate-300">Enter OTP</label>
                <input
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  maxLength={6}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                  placeholder="6-digit OTP"
                />
                <button
                  onClick={() => handleSubmit(otpMode || "login", "verify")}
                  disabled={loading || otpCode.length !== 6}
                  className="mt-3 w-full rounded-md bg-emerald-500 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                >
                  {loading ? "Verifying..." : "Verify OTP"}
                </button>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
