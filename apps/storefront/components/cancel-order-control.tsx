"use client";

import { useActionState, useState } from "react";
import type { Locale } from "@/lib/types";
import { translator, type MessageKey } from "@/lib/i18n";
import { initialOrderActionState } from "@/lib/action-states";
import { cancelOwnOrder } from "@/lib/order-actions";

const REASONS: { code: string; key: MessageKey }[] = [
  { code: "changed_mind", key: "cancel.changedMind" },
  { code: "ordered_by_mistake", key: "cancel.orderedByMistake" },
  { code: "wrong_item", key: "cancel.wrongItem" },
  { code: "found_cheaper", key: "cancel.foundCheaper" },
  { code: "delivery_too_slow", key: "cancel.deliveryTooSlow" },
  { code: "other", key: "cancel.other" },
];

export function CancelOrderControl({
  locale,
  orderId,
}: {
  locale: Locale;
  orderId: string;
}) {
  const t = translator(locale);
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState(REASONS[0].code);
  const [state, action, pending] = useActionState(cancelOwnOrder, initialOrderActionState);

  if (!open) {
    return (
      <button className="btn btn-quiet" type="button" onClick={() => setOpen(true)}>
        {t("cancel.open")}
      </button>
    );
  }

  return (
    <form action={action} className="lifecycle-control stack-0">
      <input type="hidden" name="order_id" value={orderId} />
      <label className="field-label" htmlFor={`cancel-reason-${orderId}`}>
        {t("cancel.reason")}
      </label>
      <select
        className="input"
        id={`cancel-reason-${orderId}`}
        name="reason_code"
        value={code}
        onChange={(event) => setCode(event.target.value)}
      >
        {REASONS.map((reason) => (
          <option value={reason.code} key={reason.code}>
            {t(reason.key)}
          </option>
        ))}
      </select>
      {code === "other" ? (
        <>
          <label className="field-label" htmlFor={`cancel-text-${orderId}`}>
            {t("cancel.otherLabel")}
          </label>
          <input
            className="input"
            id={`cancel-text-${orderId}`}
            name="reason"
            required
            minLength={3}
            maxLength={300}
          />
        </>
      ) : null}
      <div className="row-actions">
        <button className="btn btn-primary" type="submit" disabled={pending}>
          {pending ? t("cancel.submitting") : t("cancel.confirm")}
        </button>
        <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
          {t("common.back")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "error"
          ? state.code === "conflict"
            ? t("cancel.conflict")
            : state.code === "invalid_input"
              ? t("cancel.invalid")
              : t("cancel.failed")
          : t("cancel.hint")}
      </p>
    </form>
  );
}
