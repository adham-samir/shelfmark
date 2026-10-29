"use client";

import { useEffect } from "react";
import { useCompare } from "@/lib/compare-client";

/**
 * Keeps the local comparison tray aligned with a server-rendered comparison
 * page: ids that no longer resolve to active products leave the tray.
 */
export function CompareSync({ ids }: { ids: string[] }) {
  const { keepOnly, ready } = useCompare();
  useEffect(() => {
    if (ready) keepOnly(ids);
  }, [ids, keepOnly, ready]);
  return null;
}
