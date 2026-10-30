"use client";

import Link from "next/link";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { IconCart } from "./icons";
import { useSession } from "./session-provider";

/**
 * The cart action in the storefront header.
 *
 * It reads the count from the session context rather than from a server prop so
 * adding a product updates the badge immediately; the server value is still the
 * initial render, so there is no flash of "0" on first paint.
 */
export function HeaderCart({
  locale,
  initialCount,
}: {
  locale: Locale;
  initialCount: number;
}) {
  const t = translator(locale);
  const { cartCount } = useSession();
  // Before hydration the context carries the same value the server rendered, so
  // this is stable in both phases.
  const count = cartCount ?? initialCount;

  return (
    <Link className="header-action header-cart" href="/cart">
      <IconCart size={17} />
      <span className="label">{t("nav.cart")}</span>
      <span className="cart-count" data-empty={count === 0} aria-hidden="true">
        {count}
      </span>
      {/* The visible label plus this sentence form the accessible name, so the
          link announces both its purpose and the current quantity. */}
      <span className="visually-hidden">{t("nav.cartLabel", { count })}</span>
    </Link>
  );
}
