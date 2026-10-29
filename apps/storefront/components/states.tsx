import Link from "next/link";
import type { ReactNode } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";

export function EmptyState({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="state">
      <h2>{title}</h2>
      {hint ? <p>{hint}</p> : null}
      {children ? <div className="actions">{children}</div> : null}
    </div>
  );
}

export function ErrorState({
  locale,
  title,
  hint,
  onRetryHref = "/",
}: {
  locale: Locale;
  title?: string;
  hint?: string;
  onRetryHref?: string;
}) {
  const t = translator(locale);
  return (
    <div className="state" data-tone="error" role="alert">
      <h2>{title ?? t("common.unexpected")}</h2>
      <p>{hint ?? t("common.unexpectedHint")}</p>
      <div className="actions">
        <Link className="btn" href={onRetryHref}>
          {t("common.retry")}
        </Link>
      </div>
    </div>
  );
}

export function Notice({
  tone = "info",
  children,
}: {
  tone?: "info" | "warn" | "error";
  children: ReactNode;
}) {
  return (
    <div className="notice" data-tone={tone} role={tone === "error" ? "alert" : undefined}>
      <div>{children}</div>
    </div>
  );
}

export function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="product-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <div className="card" key={index}>
          <div className="skeleton" style={{ height: 18, width: "55%", marginBlockEnd: 10 }} />
          <div className="skeleton" style={{ aspectRatio: "4 / 3", marginBlockEnd: 10 }} />
          <div className="skeleton" style={{ height: 14, width: "70%", marginBlockEnd: 8 }} />
          <div className="skeleton" style={{ height: 12, width: "90%", marginBlockEnd: 6 }} />
          <div className="skeleton" style={{ height: 12, width: "80%", marginBlockEnd: 12 }} />
          <div className="skeleton" style={{ height: 32 }} />
        </div>
      ))}
    </div>
  );
}