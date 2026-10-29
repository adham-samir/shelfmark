"use client";

import { useState } from "react";
import type { Locale, Product } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { compareEntryFromProduct, useCompare } from "@/lib/compare-client";
import { useSession } from "./session-provider";

export function CompareToggle({
  product,
  locale,
}: {
  product: Product;
  locale: Locale;
}) {
  const t = translator(locale);
  const { signedIn } = useSession();
  const { entries, toggle, ready } = useCompare();
  const [busy, setBusy] = useState(false);
  const checked = entries.some((entry) => entry.id === product.product_id);

  const onChange = () => {
    setBusy(true);
    toggle(compareEntryFromProduct(product));
    if (signedIn) {
      void fetch("/api/events", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          product_id: product.product_id,
          event_type: "compare",
          context: { surface: "catalog" },
        }),
      }).catch(() => undefined);
    }
    setBusy(false);
  };

  return (
    <label className="compare-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={!ready || busy}
        aria-label={`${t("card.compare")} — ${product.name}`}
      />
      <span>{t("card.compare")}</span>
    </label>
  );
}