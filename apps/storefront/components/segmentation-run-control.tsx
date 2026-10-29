"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import {
  initialSegmentationRunState,
} from "@/lib/action-states";
import { runSegmentation } from "@/lib/segmentation-actions";

export function SegmentationRunControl({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    runSegmentation,
    initialSegmentationRunState,
  );
  const failureMessage =
    state.code === "unauthorized"
      ? t("segments.runUnauthorized")
      : state.code === "forbidden"
        ? t("segments.runForbidden")
        : t("segments.runFailed");

  return (
    <form action={action} className="inventory-run">
      <button className="btn inventory-run-button" type="submit" disabled={pending}>
        {pending ? t("segments.running") : t("segments.run")}
      </button>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("segments.runSuccess", {
              classified: state.classified ?? 0,
              insufficient: state.insufficient ?? 0,
              eligible: state.eligible ?? 0,
              excluded: state.excluded ?? 0,
            })
          : state.kind === "error"
            ? `${failureMessage}${state.requestId ? ` · ${state.requestId}` : ""}`
            : t("segments.runHint")}
      </p>
    </form>
  );
}