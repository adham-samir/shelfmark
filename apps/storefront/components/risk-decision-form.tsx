"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialReviewDecisionState } from "@/lib/action-states";
import { decideReview } from "@/lib/risk-actions";

export function RiskDecisionForm({
  locale,
  assessmentId,
}: {
  locale: Locale;
  assessmentId: string;
}) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    decideReview,
    initialReviewDecisionState,
  );
  const failure =
    state.code === "conflict"
      ? t("risk.decisionConflict")
      : state.code === "not_found"
        ? t("risk.decisionMissing")
        : state.code === "forbidden" || state.code === "unauthorized"
          ? t("risk.decisionForbidden")
          : t("risk.decisionFailed");

  return (
    <form action={action} className="risk-decisions">
      <input type="hidden" name="assessment_id" value={assessmentId} />
      <button
        className="btn risk-allow"
        name="decision"
        value="allow"
        type="submit"
        disabled={pending}
      >
        {t("risk.allow")}
      </button>
      <button
        className="btn risk-decline"
        name="decision"
        value="decline"
        type="submit"
        disabled={pending}
      >
        {t("risk.decline")}
      </button>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? state.status === "confirmed"
            ? t("risk.allowed")
            : t("risk.declined")
          : state.kind === "error"
            ? `${failure}${state.requestId ? ` · ${state.requestId}` : ""}`
            : null}
      </p>
    </form>
  );
}