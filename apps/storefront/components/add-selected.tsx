"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { useSession } from "./session-provider";

/**
 * Adds every selected comparison product to the cart in one action. Each item
 * is a separate idempotent cart mutation; a failure stops the batch and names
 * the message returned by the cart adapter.
 */
export function AddSelectedButton({
  productIds,
  locale,
  label,
  disabled = false,
}: {
  productIds: string[];
  locale: Locale;
  label: string;
  disabled?: boolean;
}) {
  const t = translator(locale);
  const router = useRouter();
  const pathname = usePathname();
  const { signedIn } = useSession();
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!signedIn) {
    return (
      <span className="add-to-cart">
        <Link
          className="btn btn-primary btn-block"
          href={`/login?next=${encodeURIComponent(pathname)}`}
        >
          {t("cart.signInToCompare")}
        </Link>
      </span>
    );
  }

  const add = async () => {
    if (productIds.length === 0) return;
    setState("busy");
    setMessage("");
    try {
      for (const productId of productIds) {
        const response = await fetch("/api/cart", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ product_id: productId, quantity: 1 }),
        });
        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as
            | { error?: { message?: string } }
            | null;
          throw new Error(payload?.error?.message ?? t("cart.updateError"));
        }
      }
      setState("done");
      setMessage(t("card.added"));
      router.refresh();
      window.setTimeout(() => setState("idle"), 2200);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : t("cart.updateError"));
    }
  };

  return (
    <span className="add-to-cart">
      <button
        type="button"
        className="btn btn-primary btn-block"
        onClick={add}
        disabled={disabled || state === "busy"}
        aria-busy={state === "busy"}
        data-state={state}
      >
        {state === "busy"
          ? t("card.adding")
          : state === "done"
            ? t("card.added")
            : label}
      </button>
      <span className="visually-hidden" role="status" aria-live="polite">
        {state === "error" ? message : state === "done" ? message : ""}
      </span>
      {state === "error" ? (
        <span className="field-error" role="alert">
          {message}
        </span>
      ) : null}
    </span>
  );
}
