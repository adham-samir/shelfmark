"use client";

import Link from "next/link";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { compareHref, useCompare } from "@/lib/compare-client";

/**
 * Proximate comparison affordance for viewports where the tray sits below the
 * product field. Appears as soon as one product is selected and links to the
 * comparison page, keeping the tray's count visible while browsing.
 */
export function CompareBar({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const { entries, ready } = useCompare();

  if (!ready || entries.length === 0) return null;

  return (
    <div className="compare-bar" role="region" aria-label={t("compare.title")}>
      <p className="compare-bar-count">
        {t("compare.title")} <span>({entries.length})</span>
      </p>
      <Link className="btn btn-amber" href={compareHref(entries)}>
        {t("compare.open")}
      </Link>
    </div>
  );
}
