import { cookies } from "next/headers";
import type { Locale } from "./types";

export const LOCALE_COOKIE = "smart_ecommerce_locale";

const SUPPORTED: Locale[] = ["ar", "en"];

export function normalizeLocale(value: string | undefined | null): Locale {
  return value === "en" ? "en" : "ar";
}

/** Read the locale cookie on the server. Arabic is the initial locale. */
export async function getLocale(): Promise<Locale> {
  const store = await cookies();
  return normalizeLocale(store.get(LOCALE_COOKIE)?.value);
}

export function direction(locale: Locale): "rtl" | "ltr" {
  return locale === "ar" ? "rtl" : "ltr";
}

export function isLocale(value: string): value is Locale {
  return (SUPPORTED as string[]).includes(value);
}