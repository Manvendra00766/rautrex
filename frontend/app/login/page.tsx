"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginUser, signupUser } from "../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSignup, setIsSignup] = useState(false);

  const handleLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await loginUser(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async () => {
    setError(null);
    setLoading(true);
    try {
      await signupUser(email, password, phoneNumber);
      router.push("/dashboard");
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
        </section>

        <section className="w-full rounded-2xl border border-slate-800 bg-slate-900 p-8">
          <h2 className="text-2xl font-bold">{isSignup ? "Sign up" : "Sign in"}</h2>
          <p className="mb-6 mt-1 text-sm text-slate-400">Enter your credentials to {isSignup ? "create an account" : "login"}.</p>

          {error && <div className="mb-4 rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}

          <div className="space-y-4">
            {isSignup && (
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-300">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 focus:ring-2"
                  placeholder="John Doe"
                />
              </div>
            )}
            {isSignup && (
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
            )}
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
                onClick={isSignup ? handleSignup : handleLogin}
                disabled={loading || !email || !password || (isSignup && (!fullName || !phoneNumber))}
                className="flex-1 rounded-md bg-cyan-500 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
              >
                {loading ? (isSignup ? "Signing up..." : "Logging in...") : (isSignup ? "Sign Up" : "Login")}
              </button>
              <button
                onClick={() => setIsSignup(!isSignup)}
                className="flex-1 rounded-md border border-slate-600 bg-slate-800 py-2 text-sm font-medium hover:bg-slate-700"
              >
                {isSignup ? "Back to Login" : "Create Account"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
