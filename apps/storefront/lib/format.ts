import type { Locale } from "./types";

/**
 * API money values are exact decimal strings. Formatting never changes the
 * stored value: it only groups digits for display.
 */
export function formatMoney(amount: string, locale: Locale): string {
  const [whole, fraction] = amount.split(".");
  const sign = whole.startsWith("-") ? "-" : "";
  const digits = sign ? whole.slice(1) : whole;
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const trimmed = fraction ? `.${fraction.replace(/0+$/, "")}` : "";
  const numeric = `${sign}${grouped}${trimmed === "." ? "" : trimmed}`;
  return locale === "ar" ? numeric : numeric;
}

export function currencyLabel(locale: Locale): string {
  return locale === "ar" ? "ج.م" : "EGP";
}

const CAIRO = "Africa/Cairo";

export function formatDateTime(value: string, _locale: Locale): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  // Technical timestamps stay in a fixed LTR order. Locale-shaped Arabic date
  // patterns reorder segments under `dir="ltr"` and render as "2819:37 2026/10/".
  const parts = new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: CAIRO,
    numberingSystem: "latn",
  }).formatToParts(date);
  const part = (type: string) =>
    parts.find((item) => item.type === type)?.value ?? "";
  const stamp = `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}`;
  // Isolate the stamp so RTL copy cannot reorder the date and time segments.
  return `\u2066${stamp}\u2069`;
}

export function formatDate(value: string, locale: Locale): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const formatted = new Intl.DateTimeFormat(locale === "ar" ? "ar-EG" : "en-GB", {
    dateStyle: "medium",
    timeZone: CAIRO,
    numberingSystem: "latn",
  }).format(date);
  // Arabic numeric dates carry RLM marks between their segments, which flip the
  // day and year when the surrounding paragraph is RTL. Strip the marks and
  // isolate the result so the date always reads in logical order.
  return `\u2066${formatted.replace(/[\u200e\u200f\u061c]/g, "")}\u2069`;
}

export function formatNumber(value: number, _locale: Locale): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}
const SCALE = 6;

function toScaled(amount: string): bigint {
  const [whole, fraction = ""] = amount.split(".");
  const digits = `${whole}${fraction.padEnd(SCALE, "0").slice(0, SCALE)}`;
  return BigInt(digits);
}

function fromScaled(value: bigint): string {
  const negative = value < 0n;
  const digits = (negative ? -value : value).toString().padStart(SCALE + 1, "0");
  const whole = digits.slice(0, -SCALE);
  const fraction = digits.slice(-SCALE).replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

/** Exact decimal multiplication for line totals (no floating-point drift). */
export function multiplyMoney(amount: string, quantity: number): string {
  return fromScaled(toScaled(amount) * BigInt(quantity));
}

/** Exact decimal sum for subtotals. */
export function sumMoney(amounts: string[]): string {
  return fromScaled(amounts.reduce((total, amount) => total + toScaled(amount), 0n));
}
