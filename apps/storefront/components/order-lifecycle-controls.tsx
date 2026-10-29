"use client";

import { useActionState, useState } from "react";
import type { Locale, ShipmentStatus } from "@/lib/types";
import { translator, type MessageKey } from "@/lib/i18n";
import { initialOrderActionState } from "@/lib/action-states";
import { cancelOrder, refundOrder, transitionShipment } from "@/lib/order-actions";

const NEXT_STEPS: Record<
  ShipmentStatus,
  { target: "ready" | "in_transit" | "delivered" | "exception"; key: MessageKey }[]
> = {
  pending: [
    { target: "ready", key: "orderLifecycle.markReady" },
    { target: "exception", key: "orderLifecycle.markException" },
  ],
  ready: [
    { target: "in_transit", key: "orderLifecycle.markInTransit" },
    { target: "exception", key: "orderLifecycle.markException" },
  ],
  in_transit: [
    { target: "delivered", key: "orderLifecycle.markDelivered" },
    { target: "exception", key: "orderLifecycle.markException" },
  ],
  exception: [{ target: "ready", key: "orderLifecycle.resumeReady" }],
  delivered: [],
};

export function ShipmentTransitionControl({
  locale,
  orderId,
  status,
}: {
  locale: Locale;
  orderId: string;
  status: ShipmentStatus;
}) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    transitionShipment,
    initialOrderActionState,
  );
  const steps = NEXT_STEPS[status];

  return (
    <form action={action} className="lifecycle-control">
      <input type="hidden" name="order_id" value={orderId} />
      <div className="row-actions">
        {steps.map((step) => (
          <button
            className={step.target === "exception" ? "btn btn-quiet" : "btn"}
            name="status"
            value={step.target}
            type="submit"
            key={step.target}
            disabled={pending}
          >
            {t(step.key)}
          </button>
        ))}
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("orderLifecycle.transitioned")
          : state.kind === "error"
            ? `${actionFailure(t, state.code)}${state.requestId ? ` · ${state.requestId}` : ""}`
            : steps.length === 0
              ? t("orderLifecycle.deliveredFinal")
              : null}
      </p>
    </form>
  );
}

function actionFailure(
  t: ReturnType<typeof translator>,
  code: string | undefined,
): string {
  switch (code) {
    case "conflict":
      return t("orderLifecycle.conflict");
    case "not_found":
      return t("orderLifecycle.missing");
    case "invalid_input":
      return t("orderLifecycle.invalid");
    case "forbidden":
    case "unauthorized":
      return t("orderLifecycle.forbidden");
    default:
      return t("orderLifecycle.failed");
  }
}

export function OrderCancelControl({
  locale,
  orderId,
}: {
  locale: Locale;
  orderId: string;
}) {
  const t = translator(locale);
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState(cancelOrder, initialOrderActionState);

  if (!open) {
    return (
      <button className="btn btn-quiet" type="button" onClick={() => setOpen(true)}>
        {t("orderLifecycle.cancel")}
      </button>
    );
  }

  return (
    <form action={action} className="lifecycle-control">
      <input type="hidden" name="order_id" value={orderId} />
      <label className="field-label" htmlFor={`cancel-reason-${orderId}`}>
        {t("orderLifecycle.reason")}
      </label>
      <input
        className="input"
        id={`cancel-reason-${orderId}`}
        name="reason"
        required
        minLength={3}
        maxLength={300}
      />
      <div className="row-actions">
        <button className="btn btn-dark" type="submit" disabled={pending}>
          {t("orderLifecycle.confirmCancel")}
        </button>
        <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
          {t("common.back")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("orderLifecycle.cancelled")
          : state.kind === "error"
            ? `${actionFailure(t, state.code)}${state.requestId ? ` · ${state.requestId}` : ""}`
            : t("orderLifecycle.cancelHint")}
      </p>
    </form>
  );
}

export function OrderRefundControl({
  locale,
  orderId,
  remaining,
}: {
  locale: Locale;
  orderId: string;
  remaining: string;
}) {
  const t = translator(locale);
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState(refundOrder, initialOrderActionState);

  if (!open) {
    return (
      <button className="btn btn-quiet" type="button" onClick={() => setOpen(true)}>
        {t("orderLifecycle.refund")}
      </button>
    );
  }

  return (
    <form action={action} className="lifecycle-control">
      <input type="hidden" name="order_id" value={orderId} />
      <label className="field-label" htmlFor={`refund-amount-${orderId}`}>
        {t("orderLifecycle.amount")}
      </label>
      <input
        className="input"
        id={`refund-amount-${orderId}`}
        name="amount"
        inputMode="decimal"
        required
        defaultValue={remaining}
        dir="ltr"
      />
      <label className="field-label" htmlFor={`refund-reason-${orderId}`}>
        {t("orderLifecycle.reason")}
      </label>
      <input
        className="input"
        id={`refund-reason-${orderId}`}
        name="reason"
        required
        minLength={3}
        maxLength={300}
      />
      <div className="row-actions">
        <button className="btn btn-dark" type="submit" disabled={pending}>
          {t("orderLifecycle.confirmRefund")}
        </button>
        <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
          {t("common.back")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("orderLifecycle.refunded", {
              amount: state.amount ?? "0",
              total: state.refundTotal ?? "0",
            })
          : state.kind === "error"
            ? `${actionFailure(t, state.code)}${state.requestId ? ` · ${state.requestId}` : ""}`
            : t("orderLifecycle.refundHint", { remaining })}
      </p>
    </form>
  );
}
