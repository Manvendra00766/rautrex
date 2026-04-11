import {
  login as apiLogin,
  signup as apiSignup,
  register as apiRegister,
  verifyEmail as apiVerifyEmail,
  loginChallenge as apiLoginChallenge,
  loginVerify as apiLoginVerify,
  signupChallenge as apiSignupChallenge,
  signupVerify as apiSignupVerify,
  storeToken,
} from "./api";

export async function loginUser(email: string, password: string) {
  const data = await apiLogin(email, password);
  storeToken(data.access_token);
  return data;
}

export async function signupUser(email: string, password: string, phoneNumber: string) {
  const data = await apiSignup(email, password, phoneNumber);
  storeToken(data.access_token);
  return data;
}

export async function beginSignupOtp(email: string, password: string, phoneNumber: string) {
  return apiSignupChallenge(email, password, phoneNumber);
}

export async function completeSignupOtp(email: string, password: string, phoneNumber: string, challengeId: string, otpCode: string) {
  const data = await apiSignupVerify(email, password, phoneNumber, challengeId, otpCode);
  storeToken(data.access_token);
  return data;
}

export async function beginLoginOtp(email: string, password: string) {
  return apiLoginChallenge(email, password);
}

export async function completeLoginOtp(email: string, password: string, challengeId: string, otpCode: string) {
  const data = await apiLoginVerify(email, password, challengeId, otpCode);
  storeToken(data.access_token);
  return data;
}

export function logout() {
  document.cookie = "access_token=; path=/; max-age=0";
  window.location.href = "/login";
}

export function getToken(): string | undefined {
  const cookie = document.cookie
    .split("; ")
    .find((c) => c.startsWith("access_token="));
  return cookie?.split("=")[1];
}

export async function registerUser(fullName: string, email: string, password: string) {
  return apiRegister(fullName, email, password);
}

export async function verifyUserEmail(token: string) {
  return apiVerifyEmail(token);
}
