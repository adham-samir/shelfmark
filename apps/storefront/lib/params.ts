import type { CatalogQuery } from "./api";
import type { Locale } from "./types";

export interface CatalogState {
  q: string;
  category: string;
  filters: Record<string, string>;
  availability: "in_stock" | "out_of_stock" | "";
  sort: "relevance" | "price_asc" | "price_desc" | "name_asc";
  priceMin: string;
  priceMax: string;
  page: number;
  size: number;
  view: "grid" | "list";
}

export const PAGE_SIZES = [12, 24, 48] as const;

type RawParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export function parseCatalogState(params: RawParams): CatalogState {
  const filters: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (!key.startsWith("f.")) continue;
    const chosen = first(value);
    if (chosen) filters[key.slice(2)] = chosen;
  }
  const sizeRaw = Number.parseInt(first(params.size), 10);
  const pageRaw = Number.parseInt(first(params.page), 10);
  const sortRaw = first(params.sort);
  const availabilityRaw = first(params.availability);
  return {
    q: first(params.q),
    category: first(params.category),
    filters,
    availability:
      availabilityRaw === "in_stock" || availabilityRaw === "out_of_stock"
        ? availabilityRaw
        : "",
    sort:
      sortRaw === "price_asc" || sortRaw === "price_desc" || sortRaw === "name_asc"
        ? sortRaw
        : "relevance",
    priceMin: first(params.price_min),
    priceMax: first(params.price_max),
    page: Number.isFinite(pageRaw) && pageRaw > 0 ? pageRaw : 1,
    size: (PAGE_SIZES as readonly number[]).includes(sizeRaw) ? sizeRaw : 12,
    view: first(params.view) === "list" ? "list" : "grid",
  };
}

export function catalogQuery(state: CatalogState): CatalogQuery {
  return {
    q: state.q || undefined,
    category: state.category || undefined,
    filters: state.filters,
    availability: state.availability || undefined,
    sort: state.sort,
    priceMin: state.priceMin || undefined,
    priceMax: state.priceMax || undefined,
    limit: state.size,
    offset: (state.page - 1) * state.size,
  };
}

export function catalogHref(
  state: Partial<CatalogState>,
  base: CatalogState,
  path = "/",
): string {
  const merged: CatalogState = { ...base, ...state };
  const params = new URLSearchParams();
  if (merged.q) params.set("q", merged.q);
  if (merged.category) params.set("category", merged.category);
  if (merged.availability) params.set("availability", merged.availability);
  if (merged.sort && merged.sort !== "relevance") params.set("sort", merged.sort);
  if (merged.priceMin) params.set("price_min", merged.priceMin);
  if (merged.priceMax) params.set("price_max", merged.priceMax);
  for (const [key, value] of Object.entries(merged.filters)) {
    if (value) params.set(`f.${key}`, value);
  }
  if (merged.size !== 12) params.set("size", String(merged.size));
  if (merged.page > 1) params.set("page", String(merged.page));
  if (merged.view === "list") params.set("view", "list");
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function withLocale(path: string, _locale: Locale): string {
  return path;
}