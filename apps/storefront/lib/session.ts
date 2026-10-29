import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { readSessionToken, type Surface } from "@/lib/session-cookie";
import type { AccountView } from "@/lib/types";

export {
  CUSTOMER_COOKIE,
  OPERATOR_COOKIE,
  clearSession,
  readSessionToken,
  safeNext,
  writeSession,
} from "@/lib/session-cookie";
export type { Surface } from "@/lib/session-cookie";

/**
 * Resolve the signed-in account for one surface, or null when the cookie is
 * missing or no longer valid. Two surfaces keep customer and operator sessions
 * independent: signing in to the back office never replaces a shop session.
 */
export async function currentAccount(
  surface: Surface = "customer",
): Promise<AccountView | null> {
  const token = await readSessionToken(surface);
  if (!token) return null;
  try {
    return await api.me(surface);
  } catch {
    return null;
  }
}

export async function requireCustomer(next: string): Promise<AccountView> {
  const account = await currentAccount("customer");
  if (!account) {
    redirect(`/login?next=${encodeURIComponent(next)}`);
  }
  return account;
}

export async function requireOperator(next: string): Promise<AccountView> {
  const account = await currentAccount("operator");
  if (!account) {
    redirect(`/backoffice/login?next=${encodeURIComponent(next)}`);
  }
  return account;
}
