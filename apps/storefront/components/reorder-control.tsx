"use client";

import { useActionState } from "react";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { translator, type MessageKey } from "@/lib/i18n";
import { initialReorderState } from "@/lib/action-states";
import { reorderOwnOrder } from "@/lib/order-actions";

const REASONS: Record<string, MessageKey> = {
  product_inactive: "reorder.inactive",
  price_unavailable: "reorder.noPrice",
  out_of_stock: "reorder.outOfStock",
  quantity_capped: "reorder.capped",
};

export function ReorderControl({
  locale,
  orderId,
}: {
  locale: Locale;
  orderId: string;
}) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(reorderOwnOrder, initialReorderState);

  return (
    <form action={action} className="lifecycle-control" style={{ marginBlockStart: 0 }}>
      <input type="hidden" name="order_id" value={orderId} />
      <div className="row-actions">
        <button className="btn" type="submit" disabled={pending}>
          {pending ? t("reorder.adding") : t("reorder.action")}
        </button>
        {state.kind === "success" && (state.added ?? 0) > 0 ? (
          <Link className="btn btn-quiet" href="/cart">
            {t("reorder.viewCart")}
          </Link>
        ) : null}
      </div>
      <p aria-live="polite" data-tone={state.kind}>
        {state.kind === "success"
          ? t("reorder.added", { count: state.added ?? 0 })
          : state.kind === "error"
            ? state.code === "not_found"
              ? t("reorder.missing")
              : state.code === "unauthorized"
                ? t("reorder.unauthorized")
                : t("reorder.failed")
            : t("reorder.hint")}
      </p>
      {state.kind === "success" && (state.skipped?.length ?? 0) > 0 ? (
        <div>
          <p className="field-hint">{t("reorder.skippedTitle")}</p>
          <ul className="summary-lines">
            {state.skipped?.map((item, index) => (
              <li key={`${item.name}-${index}`}>
                <span>{item.name}</span>
                <span className="field-hint">
                  {REASONS[item.reason] ? t(REASONS[item.reason]) : item.reason}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </form>
  );
}
