"use client";

import { useCallback, useEffect, useState } from "react";
import { plateFor } from "./plates";

export interface CompareEntry {
  id: string;
  name: string;
  price: string;
  currency: string;
  availability: "in_stock" | "out_of_stock";
  categories: string[];
  attributes: Record<string, string>;
  image: string | null;
}

const STORAGE_KEY = "smart_ecommerce_compare_v1";
const EVENT = "smart-ecommerce:compare";

function read(): CompareEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((entry): entry is CompareEntry => {
      if (typeof entry !== "object" || entry === null) return false;
      const candidate = entry as Record<string, unknown>;
      return typeof candidate.id === "string" && typeof candidate.name === "string";
    });
  } catch {
    return [];
  }
}

function write(entries: CompareEntry[]): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  window.dispatchEvent(new CustomEvent(EVENT));
}

export const COMPARE_LIMIT = 2;

export function useCompare() {
  const [entries, setEntries] = useState<CompareEntry[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const sync = () => {
      setEntries(read());
      setReady(true);
    };
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const toggle = useCallback((entry: CompareEntry) => {
    const current = read();
    const exists = current.some((item) => item.id === entry.id);
    const next = exists
      ? current.filter((item) => item.id !== entry.id)
      : [...current, entry].slice(0, COMPARE_LIMIT);
    write(next);
  }, []);

  const remove = useCallback((id: string) => {
    write(read().filter((item) => item.id !== id));
  }, []);

  const clear = useCallback(() => {
    write([]);
  }, []);

  const keepOnly = useCallback((ids: string[]) => {
    const kept = read().filter((item) => ids.includes(item.id));
    if (kept.length !== read().length) write(kept);
  }, []);

  return { entries, ready, toggle, remove, clear, keepOnly };
}

export function compareHref(entries: CompareEntry[]): string {
  const ids = entries.map((entry) => entry.id);
  return ids.length ? `/compare?ids=${ids.join(",")}` : "/compare";
}

export function compareEntryFromProduct(product: {
  product_id: string;
  name: string;
  price: { amount: string; currency: string };
  availability: { status: "in_stock" | "out_of_stock" };
  categories: string[];
  attributes: Record<string, string>;
}): CompareEntry {
  return {
    id: product.product_id,
    name: product.name,
    price: product.price.amount,
    currency: product.price.currency,
    availability: product.availability.status,
    categories: product.categories,
    attributes: product.attributes,
    image: plateFor({ product_id: product.product_id, name: product.name })?.src ?? null,
  };
}