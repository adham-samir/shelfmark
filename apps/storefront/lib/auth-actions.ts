"use server";

import { redirect } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import type { AccountFormState, AuthFormState } from "@/lib/action-states";
import {
  clearSession,
  safeNext,
  writeSession,
  type Surface,
} from "@/lib/session-cookie";

/**
 * Demo identity actions. Passwords and session tokens never reach the browser:
 * the action exchanges them with the API server-side and stores the token in an
 * httpOnly cookie.
 */

function surfaceOf(formData: FormData): Surface {
  return formData.get("surface") === "operator" ? "operator" : "customer";
}

function codeOf(error: unknown): AuthFormState["code"] {
  if (error instanceof ApiError) {
    if (error.status === 401) return "invalid_credentials";
    if (error.status === 429) return "rate_limited";
    if (error.status === 409) return "conflict";
    if (error.code === "invalid_input") return "invalid_input";
    if (error.code === "dependency_unavailable") return "dependency_unavailable";
  }
  return "unknown";
}

export async function signIn(
  _previous: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const surface = surfaceOf(formData);
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  if (!email || !password) return { kind: "error", code: "invalid_credentials" };

  let session;
  try {
    session = await api.login({ email, password, surface });
  } catch (error) {
    return { kind: "error", code: codeOf(error) };
  }
  await writeSession(surface, session.token, session.expires_at);
  redirect(safeNext(formData.get("next")) || (surface === "operator" ? "/backoffice" : "/account"));
}

export async function registerAccount(
  _previous: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = String(formData.get("email") ?? "").trim();
  const displayName = String(formData.get("display_name") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("password_confirm") ?? "");
  const locale = formData.get("locale") === "en" ? "en" : "ar";
  if (!email || displayName.length < 2 || password.length < 8) {
    return { kind: "error", code: "invalid_input" };
  }
  if (password !== confirm) return { kind: "error", code: "invalid_input" };

  let session;
  try {
    session = await api.register({
      email,
      display_name: displayName,
      password,
      preferred_locale: locale,
    });
  } catch (error) {
    return { kind: "error", code: codeOf(error) };
  }
  await writeSession("customer", session.token, session.expires_at);
  redirect(safeNext(formData.get("next")) || "/account");
}

export async function signOut(formData: FormData): Promise<void> {
  const surface = surfaceOf(formData);
  try {
    await api.logout(surface);
  } catch {
    /* the cookie is cleared even when the API session already expired */
  }
  await clearSession(surface);
  redirect(surface === "operator" ? "/backoffice/login" : "/");
}

export async function saveAccount(
  _previous: AccountFormState,
  formData: FormData,
): Promise<AccountFormState> {
  const displayName = String(formData.get("display_name") ?? "").trim();
  const locale = formData.get("preferred_locale") === "en" ? "en" : "ar";
  if (displayName.length < 2) return { kind: "error", code: "invalid_input" };
  try {
    await api.updateAccount({
      display_name: displayName,
      preferred_locale: locale,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "error", code: "unauthorized" };
    }
    if (error instanceof ApiError && error.code === "invalid_input") {
      return { kind: "error", code: "invalid_input" };
    }
    return { kind: "error", code: "unknown" };
  }
  return { kind: "success" };
}
