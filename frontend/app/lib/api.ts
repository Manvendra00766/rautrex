const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API_URL}/api/v1${path}`, opts);

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || res.statusText);
  }

  return res.json();
}

// ---- Auth helpers ----

export async function login(email: string, password: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Login failed");
  }

  return res.json();
}

export async function signup(email: string, password: string, phoneNumber: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, phone_number: phoneNumber }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Signup failed");
  }

  return res.json();
}

export async function register(fullName: string, email: string, password: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Registration failed");
  }

  return res.json();
}

export async function verifyEmail(token: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Email verification failed");
  }
  return res.json();
}

export async function signupChallenge(email: string, password: string, phoneNumber: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/signup/challenge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, phone_number: phoneNumber }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Signup OTP challenge failed");
  }
  return res.json();
}

export async function signupVerify(email: string, password: string, phoneNumber: string, challengeId: string, otpCode: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/signup/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      phone_number: phoneNumber,
      challenge_id: challengeId,
      otp_code: otpCode,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Signup OTP verification failed");
  }
  return res.json();
}

export async function loginChallenge(email: string, password: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/login/challenge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Login OTP challenge failed");
  }
  return res.json();
}

export async function loginVerify(email: string, password: string, challengeId: string, otpCode: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/login/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      challenge_id: challengeId,
      otp_code: otpCode,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "Login OTP verification failed");
  }
  return res.json();
}

export function storeToken(token: string) {
  document.cookie = `access_token=${token}; path=/; max-age=${30 * 60}; SameSite=Lax`;
}

export async function fetchWithAuth(path: string, opts: RequestInit = {}) {
  const cookie = document.cookie
    .split("; ")
    .find((c) => c.startsWith("access_token="));
  const token = cookie?.split("=")[1];

  return apiFetch(path, {
    ...opts,
    headers: {
      ...opts.headers,
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

export async function createOrder(plan: "pro_monthly" | "pro_annual" | "team_monthly") {
  return fetchWithAuth("/payment/create-order", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

export async function verifyPayment(payload: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  plan: "pro_monthly" | "pro_annual" | "team_monthly";
}) {
  return fetchWithAuth("/payment/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---- Portfolio helpers ----

export async function checkPortfolio() {
  return fetchWithAuth("/portfolio", {
    method: "GET",
  });
}

export async function getPortfolioMetrics() {
  return fetchWithAuth("/portfolio/metrics", {
    method: "GET",
  });
}

export async function createPortfolio(assets: Array<{ ticker: string; amount_invested: number }>) {
  return fetchWithAuth("/portfolio", {
    method: "POST",
    body: JSON.stringify({ assets }),
  });
}

export async function addAssetToPortfolio(ticker: string, amount_invested: number) {
  return fetchWithAuth("/portfolio/add-asset", {
    method: "POST",
    body: JSON.stringify({ ticker, amount_invested }),
  });
}

export async function removeAssetFromPortfolio(ticker: string) {
  return fetchWithAuth(`/portfolio/remove-asset/${ticker}`, {
    method: "DELETE",
  });
}

export async function optimizePortfolio() {
  return fetchWithAuth("/portfolio/optimize", {
    method: "POST",
  });
}
