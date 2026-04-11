"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createMyAPIKey,
  getMyProfile,
  updateMyPreferences,
  UserProfileResponse,
} from "../../lib/api/profile";

const seededProfile: UserProfileResponse = {
  id: 11,
  full_name: "Dr. Elena Rostova",
  email: "elena.rostova@gmail.com",
  role: "Senior Quant",
  subscription_tier: "Institutional Pro",
  tier: "pro",
  persona: "Analyst",
  onboarding_completed: true,
  trial_started_at: "2026-01-01T00:00:00Z",
  trial_expires_at: "2026-03-01T00:00:00Z",
  trial_expired: false,
  renewal_date: "2026-11-30T00:00:00Z",
  backtest_hours_used: 45,
  backtest_hours_limit: 100,
  preferences: {
    default_currency: "USD",
    risk_free_rate: 0.0525,
    var_confidence: 0.95,
  },
  api_keys: [
    {
      id: 1,
      name: "Alpha Execution Engine",
      masked_key: "rtx_live_••••••••8f9a",
      created_at: "2026-03-12T10:32:00Z",
      last_used_at: "2026-04-08T17:04:00Z",
      revoked: false,
    },
    {
      id: 2,
      name: "Risk Surveillance Bot",
      masked_key: "rtx_live_••••••••31c4",
      created_at: "2026-02-20T08:11:00Z",
      last_used_at: "2026-04-08T16:57:00Z",
      revoked: false,
    },
  ],
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfileResponse>(seededProfile);
  const [newKeyName, setNewKeyName] = useState("Execution Gateway");
  const [latestRawKey, setLatestRawKey] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await getMyProfile();
        setProfile(response);
      } catch (err: any) {
        setError(err.message || "Failed to load profile.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const usagePct = useMemo(
    () => Math.min(100, (profile.backtest_hours_used / profile.backtest_hours_limit) * 100),
    [profile.backtest_hours_limit, profile.backtest_hours_used]
  );

  const onSavePreferences = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await updateMyPreferences(profile.preferences);
      setProfile((prev) => ({ ...prev, preferences: updated }));
    } catch (err: any) {
      setError(err.message || "Failed to update preferences.");
    } finally {
      setSaving(false);
    }
  };

  const onCreateApiKey = async () => {
    setSaving(true);
    setError(null);
    try {
      const created = await createMyAPIKey(newKeyName);
      setLatestRawKey(created.key);
      setProfile((prev) => ({
        ...prev,
        api_keys: [
          {
            id: created.id,
            name: created.name,
            masked_key: created.masked_key,
            created_at: created.created_at,
            last_used_at: created.created_at,
            revoked: false,
          },
          ...prev.api_keys,
        ],
      }));
      setNewKeyName("Execution Gateway");
    } catch (err: any) {
      setError(err.message || "Failed to create API key.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 bg-slate-950 text-slate-100">
      {error && <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</div>}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 xl:col-span-1">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-cyan-500/20 text-xl font-semibold text-cyan-300">
              ER
            </div>
            <div>
              <h1 className="text-xl font-semibold">{profile.full_name}</h1>
              <p className="text-sm text-slate-400">{profile.email}</p>
              <p className="mt-1 text-xs uppercase tracking-wide text-cyan-300">{profile.role}</p>
            </div>
          </div>
          {loading && <p className="mt-4 text-xs text-slate-500">Syncing profile...</p>}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 xl:col-span-2">
          <h2 className="text-sm font-medium text-slate-300">Subscription & Billing</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <p className="text-xs uppercase text-slate-500">Current Tier</p>
              <p className="mt-1 text-lg font-semibold">{profile.subscription_tier}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <p className="text-xs uppercase text-slate-500">Renewal Date</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">
                {new Date(profile.renewal_date).toLocaleDateString("en-US")}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <p className="text-xs uppercase text-slate-500">Backtest Usage</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">
                {profile.backtest_hours_used}/{profile.backtest_hours_limit} hrs
              </p>
            </div>
          </div>
          <div className="mt-4 h-2 w-full overflow-hidden rounded bg-slate-800">
            <div className="h-full bg-cyan-400" style={{ width: `${usagePct}%` }} />
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-slate-300">API Keys Management</h2>
          <div className="flex items-center gap-2">
            <input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
              placeholder="Key name"
            />
            <button
              onClick={onCreateApiKey}
              disabled={saving || !newKeyName.trim()}
              className="rounded-md bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
            >
              Generate Key
            </button>
          </div>
        </div>
        {latestRawKey && (
          <p className="mt-3 rounded border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300 tabular-nums">
            New key (copy now): {latestRawKey}
          </p>
        )}
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-950 text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left">Name</th>
                <th className="px-3 py-2 text-left">Creation Date</th>
                <th className="px-3 py-2 text-left">Last Used</th>
                <th className="px-3 py-2 text-left">Masked Key</th>
              </tr>
            </thead>
            <tbody>
              {profile.api_keys.map((key) => (
                <tr key={key.id} className="border-t border-slate-800">
                  <td className="px-3 py-2">{key.name}</td>
                  <td className="px-3 py-2 tabular-nums">{new Date(key.created_at).toLocaleString("en-US")}</td>
                  <td className="px-3 py-2 tabular-nums">
                    {key.last_used_at ? new Date(key.last_used_at).toLocaleString("en-US") : "Never"}
                  </td>
                  <td className="px-3 py-2 font-mono text-cyan-300">{key.masked_key}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="text-sm font-medium text-slate-300">Trading Preferences</h2>
        <form onSubmit={onSavePreferences} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block text-slate-400">Default Currency</span>
            <select
              value={profile.preferences.default_currency}
              onChange={(e) =>
                setProfile((prev) => ({
                  ...prev,
                  preferences: { ...prev.preferences, default_currency: e.target.value as "USD" | "EUR" },
                }))
              }
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-slate-400">Default Risk Free Rate (%)</span>
            <input
              type="number"
              step="0.01"
              value={(profile.preferences.risk_free_rate * 100).toFixed(2)}
              onChange={(e) =>
                setProfile((prev) => ({
                  ...prev,
                  preferences: {
                    ...prev.preferences,
                    risk_free_rate: Number(e.target.value) / 100,
                  },
                }))
              }
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 tabular-nums"
            />
          </label>

          <label className="text-sm">
            <span className="mb-1 block text-slate-400">VaR Confidence Level</span>
            <select
              value={profile.preferences.var_confidence}
              onChange={(e) =>
                setProfile((prev) => ({
                  ...prev,
                  preferences: {
                    ...prev.preferences,
                    var_confidence: Number(e.target.value),
                  },
                }))
              }
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 tabular-nums"
            >
              <option value={0.95}>95%</option>
              <option value={0.99}>99%</option>
            </select>
          </label>

          <div className="md:col-span-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
