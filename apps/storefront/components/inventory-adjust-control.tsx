"use client";

import { useActionState, useState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialInventoryAdjustmentState } from "@/lib/action-states";
import { adjustInventory } from "@/lib/order-actions";

export function InventoryAdjustControl({
  locale,
  productId,
  productName,
}: {
  locale: Locale;
  productId: string;
  productName: string;
}) {
  const t = translator(locale);
  const [open, setOpen] = useState(false);
  const [state, action, pending] = useActionState(
    adjustInventory,
    initialInventoryAdjustmentState,
  );

  if (!open) {
    return (
      <button
        className="btn btn-quiet"
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("inventoryAdjust.openLabel", { name: productName })}
      >
        {t("inventoryAdjust.open")}
      </button>
    );
  }

  return (
    <form action={action} className="lifecycle-control">
      <input type="hidden" name="product_id" value={productId} />
      <label className="field-label" htmlFor={`adjust-delta-${productId}`}>
        {t("inventoryAdjust.delta")}
      </label>
      <input
        className="input"
        id={`adjust-delta-${productId}`}
        name="quantity_delta"
        inputMode="numeric"
        required
        placeholder="+10 / -5"
        dir="ltr"
      />
      <label className="field-label" htmlFor={`adjust-reason-${productId}`}>
        {t("inventoryAdjust.reason")}
      </label>
      <input
        className="input"
        id={`adjust-reason-${productId}`}
        name="reason"
        required
        minLength={3}
        maxLength={300}
      />
      <div className="row-actions">
        <button className="btn btn-primary" type="submit" disabled={pending}>
          {t("inventoryAdjust.submit")}
        </button>
        <button className="btn btn-quiet" type="button" onClick={() => setOpen(false)}>
          {t("common.back")}
        </button>
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("inventoryAdjust.success", {
              onHand: state.onHand ?? 0,
              available: state.available ?? 0,
            })
          : state.kind === "error"
            ? `${
                state.code === "conflict"
                  ? t("inventoryAdjust.conflict")
                  : state.code === "forbidden" || state.code === "unauthorized"
                    ? t("inventoryAdjust.forbidden")
                    : t("inventoryAdjust.failed")
              }${state.requestId ? ` · ${state.requestId}` : ""}`
            : t("inventoryAdjust.hint")}
      </p>
    </form>
  );
}
