"use client";

import { useActionState } from "react";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { initialObservationState } from "@/lib/action-states";
import { recordObservation } from "@/lib/pricing-actions";

interface PricingObservationFormProps {
  locale: Locale;
  products: { id: string; name: string }[];
}

export function PricingObservationForm({
  locale,
  products,
}: PricingObservationFormProps) {
  const t = translator(locale);
  const [state, action, pending] = useActionState(
    recordObservation,
    initialObservationState,
  );

  const failureMessage =
    state.code === "invalid_input"
      ? t("pricing.importInvalid")
      : state.code === "forbidden"
        ? t("pricing.importForbidden")
        : state.code === "unauthorized"
          ? t("pricing.unauthorizedHint")
          : t("pricing.importFailed");

  return (
    <form action={action} className="pricing-form">
      <div className="pricing-form-head">
        <h2>{t("pricing.import")}</h2>
        <p>{t("pricing.importHint")}</p>
      </div>
      <div className="pricing-form-grid">
        <label className="pricing-field pricing-field-wide">
          <span>{t("pricing.importProduct")}</span>
          <select
            name="product_id"
            required
            defaultValue=""
            disabled={pending || products.length === 0}
          >
            <option value="" disabled>
              {t("pricing.importProduct")}
            </option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
        </label>
        <label className="pricing-field">
          <span>{t("pricing.importCost")}</span>
          <input
            name="recorded_cost"
            inputMode="decimal"
            required
            min="0.000001"
            step="0.01"
            disabled={pending}
          />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.importCompetitor")}</span>
          <input
            name="competitor_cost"
            inputMode="decimal"
            required
            min="0"
            step="0.01"
            disabled={pending}
          />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.importSupply")}</span>
          <input
            name="supply"
            type="number"
            inputMode="numeric"
            required
            min="0"
            step="1"
            disabled={pending}
          />
        </label>
        <label className="pricing-field">
          <span>{t("pricing.importDemand")}</span>
          <input
            name="demand"
            type="number"
            inputMode="numeric"
            required
            min="0"
            step="1"
            disabled={pending}
          />
        </label>
      </div>
      <div className="pricing-form-actions">
        <button className="btn" type="submit" disabled={pending || products.length === 0}>
          {pending ? t("pricing.importSubmitting") : t("pricing.importSubmit")}
        </button>
        <p aria-live="polite" data-tone={state.kind}>
          {state.kind === "success"
            ? t("pricing.importSuccess")
            : state.kind === "error"
              ? `${failureMessage}${state.requestId ? ` · ${state.requestId}` : ""}`
              : t("pricing.importHint")}
        </p>
      </div>
    </form>
  );
}