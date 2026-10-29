"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialPricingRunState } from "@/lib/action-states";
import { runPricing } from "@/lib/pricing-actions";

export function PricingRunControl({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    runPricing,
    initialPricingRunState,
  );
  const failureMessage =
    state.code === "unauthorized"
      ? t("pricing.runUnauthorized")
      : state.code === "forbidden"
        ? t("pricing.runForbidden")
        : t("pricing.runFailed");

  return (
    <form action={action} className="inventory-run">
      <button className="btn inventory-run-button" type="submit" disabled={pending}>
        {pending ? t("pricing.running") : t("pricing.run")}
      </button>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("pricing.runSuccess", {
              updated: state.updated ?? 0,
              unchanged: state.unchanged ?? 0,
              missing: state.missing ?? 0,
              stale: state.stale ?? 0,
              blocked: state.blocked ?? 0,
            })
          : state.kind === "error"
            ? `${failureMessage}${state.requestId ? ` · ${state.requestId}` : ""}`
            : t("pricing.runHint")}
      </p>
    </form>
  );
}