"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { useSession } from "./session-provider";

export function AddToCartButton({
  productId,
  locale,
  label,
  disabled = false,
  className = "btn btn-block",
}: {
  productId: string;
  locale: Locale;
  label?: string;
  disabled?: boolean;
  className?: string;
}) {
  const t = translator(locale);
  const router = useRouter();
  const pathname = usePathname();
  const { signedIn } = useSession();
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  if (!signedIn) {
    return (
      <span className="add-to-cart">
        <Link
          className={className}
          href={`/login?next=${encodeURIComponent(pathname)}`}
        >
          {t("cart.signInToAdd")}
        </Link>
      </span>
    );
  }

  const add = async () => {
    setState("busy");
    setMessage("");
    try {
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
      setState("done");
      setMessage(t("card.added"));
      void fetch("/api/events", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          product_id: productId,
          event_type: "add_to_cart",
          context: { surface: "catalog" },
        }),
      }).catch(() => undefined);
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
        className={className}
        onClick={add}
        disabled={disabled || state === "busy"}
        aria-busy={state === "busy"}
        data-state={state}
      >
        {state === "busy"
          ? t("card.adding")
          : state === "done"
            ? t("card.added")
            : (label ?? t("card.addToCart"))}
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
