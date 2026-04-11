"use client";

import { useState } from "react";
import Link from "next/link";
import { registerUser } from "../lib/auth";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const res = await registerUser(fullName, email, password);
      setMessage(res.message || "Check your inbox to verify your email.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-6 py-16 text-slate-100">
      <h1 className="text-3xl font-bold">Create your Rautrex account</h1>
      <p className="mt-2 text-sm text-slate-400">Start your 60-day Pro trial. No card required.</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <input className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <input className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <input className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" type="password" placeholder="Confirm password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
        {error && <p className="text-sm text-red-300">{error}</p>}
        {message && <p className="text-sm text-emerald-300">{message}</p>}
        <button disabled={loading} className="w-full rounded-md bg-cyan-500 px-4 py-2 font-semibold text-slate-950 disabled:opacity-60">
          {loading ? "Creating..." : "Start Free Trial"}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate-400">
        Already have an account? <Link href="/login" className="text-cyan-300">Login</Link>
      </p>
    </div>
  );
}
