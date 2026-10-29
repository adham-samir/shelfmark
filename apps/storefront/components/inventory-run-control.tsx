"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import {
  initialInventoryRunState,
} from "@/lib/action-states";
import { runInventoryPlanning } from "@/lib/inventory-actions";

export function InventoryRunControl({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    runInventoryPlanning,
    initialInventoryRunState,
  );
  const failureMessage =
    state.code === "unauthorized"
      ? t("inventory.runUnauthorized")
      : state.code === "forbidden"
        ? t("inventory.runForbidden")
        : t("inventory.runFailed");

  return (
    <form action={action} className="inventory-run">
      <button className="btn inventory-run-button" type="submit" disabled={pending}>
        {pending ? t("inventory.running") : t("inventory.run")}
      </button>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("inventory.runSuccess", {
              created: state.created ?? 0,
              reused: state.reused ?? 0,
            })
          : state.kind === "error"
            ? `${failureMessage}${state.message ? ` · ${state.message}` : ""}`
            : t("inventory.runHint")}
      </p>
    </form>
  );
}
