import { cookies } from "next/headers";

/**
 * Cookie plumbing shared by the API client and the session helpers.
 *
 * Kept in its own module so `lib/api.ts` can read a token without importing the
 * account helpers (which import the API client).
 */
export const CUSTOMER_COOKIE = "smart_customer_session";
export const OPERATOR_COOKIE = "smart_operator_session";
export type Surface = "customer" | "operator";

const MAX_AGE = 60 * 60 * 24 * 7;

function cookieName(surface: Surface): string {
  return surface === "customer" ? CUSTOMER_COOKIE : OPERATOR_COOKIE;
}

function secure(): boolean {
  return process.env.SMART_ECOMMERCE_COOKIE_SECURE === "1";
}

export async function readSessionToken(surface: Surface): Promise<string | null> {
  const store = await cookies();
  return store.get(cookieName(surface))?.value ?? null;
}

export async function writeSession(
  surface: Surface,
  token: string,
  expiresAt: string,
): Promise<void> {
  const store = await cookies();
  const expires = new Date(expiresAt);
  const maxAge = Number.isNaN(expires.getTime())
    ? MAX_AGE
    : Math.max(60, Math.floor((expires.getTime() - Date.now()) / 1000));
  store.set(cookieName(surface), token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
    secure: secure(),
  });
}

export async function clearSession(surface: Surface): Promise<void> {
  const store = await cookies();
  store.set(cookieName(surface), "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
    secure: secure(),
  });
}

/** Only relative paths are accepted as a post-login destination. */
export function safeNext(value: FormDataEntryValue | string | null | undefined): string {
  if (typeof value !== "string") return "";
  if (!value.startsWith("/") || value.startsWith("//")) return "";
  if (value.startsWith("/backoffice/login") || value.startsWith("/login")) return "";
  return value;
}
