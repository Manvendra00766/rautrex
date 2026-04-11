const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type HttpMethod = "GET" | "PATCH" | "POST";

function getToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const cookie = document.cookie.split("; ").find((c) => c.startsWith("access_token="));
  return cookie?.split("=")[1];
}

async function request<T>(path: string, method: HttpMethod, body?: unknown): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export interface ProfilePreferences {
  default_currency: "USD" | "EUR";
  risk_free_rate: number;
  var_confidence: number;
}

export interface ProfileAPIKey {
  id: number;
  name: string;
  masked_key: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

export interface UserProfileResponse {
  id: number;
  full_name: string;
  email: string;
  role: string;
  subscription_tier: string;
  tier: "trial" | "free" | "pro" | "team";
  persona?: "Trader" | "Student" | "Analyst" | "Developer" | null;
  onboarding_completed: boolean;
  trial_started_at?: string | null;
  trial_expires_at?: string | null;
  trial_expired?: boolean;
  renewal_date: string;
  backtest_hours_used: number;
  backtest_hours_limit: number;
  preferences: ProfilePreferences;
  api_keys: ProfileAPIKey[];
}

export interface CreateAPIKeyResponse {
  id: number;
  name: string;
  key: string;
  masked_key: string;
  created_at: string;
}

export async function getMyProfile() {
  return request<UserProfileResponse>("/users/me", "GET");
}

export async function updateMyPreferences(payload: ProfilePreferences) {
  return request<ProfilePreferences>("/users/me/preferences", "PATCH", payload);
}

export async function createMyAPIKey(name: string) {
  return request<CreateAPIKeyResponse>("/users/me/api-keys", "POST", { name });
}

export async function updateOnboarding(payload: {
  persona: "Trader" | "Student" | "Analyst" | "Developer";
  onboarding_completed: boolean;
}) {
  return request<UserProfileResponse>("/users/me/onboarding", "PATCH", payload);
}

export async function getTrialStatus() {
  return request<{
    on_trial: boolean;
    is_expired?: boolean;
    days_left?: number;
    warning_level?: "normal" | "warning" | "urgent";
    tier?: string;
  }>("/users/me/trial-status", "GET");
}
