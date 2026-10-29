"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";

export function QuantityControl({
  productId,
  quantity,
  available,
  locale,
}: {
  productId: string;
  quantity: number;
  available: number;
  locale: Locale;
}) {
  const t = translator(locale);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const update = async (next: number) => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/cart", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ product_id: productId, quantity: next }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { error?: { message?: string } }
          | null;
        throw new Error(payload?.error?.message ?? t("cart.updateError"));
      }
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("cart.updateError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="qty-block">
      <div className="qty" aria-label={`${t("cart.quantity")}: ${quantity}`}>
        <button
          type="button"
          onClick={() => update(Math.max(1, quantity - 1))}
          disabled={busy || quantity <= 1}
          aria-label={`${t("cart.quantity")} −`}
        >
          −
        </button>
        <span aria-live="polite">{quantity}</span>
        <button
          type="button"
          onClick={() => update(Math.min(available, quantity + 1))}
          disabled={busy || quantity >= available}
          aria-label={`${t("cart.quantity")} +`}
        >
          +
        </button>
      </div>
      <button
        type="button"
        className="btn btn-quiet"
        style={{ minHeight: 28, paddingInline: 0, marginBlockStart: 4 }}
        onClick={() => update(0)}
        disabled={busy}
      >
        {t("cart.remove")}
      </button>
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}