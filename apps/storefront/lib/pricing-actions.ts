"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type { ObservationState } from "./action-states";
import type { PricingRunState } from "./action-states";

export async function runPricing(
  _previous: PricingRunState,
  _formData: FormData,
): Promise<PricingRunState> {
  try {
    const result = await api.runPricing();
    revalidatePath("/backoffice/pricing");
    return {
      kind: "success",
      updated: result.updated,
      unchanged: result.unchanged,
      missing: result.missing_input,
      stale: result.stale_input,
      blocked: result.constraint_blocked,
      alreadyApplied: result.already_applied,
    };
  } catch (error) {
    return {
      kind: "error",
      code:
        error instanceof ApiError &&
        ["unauthorized", "forbidden", "dependency_unavailable"].includes(error.code)
          ? (error.code as PricingRunState["code"])
          : "unknown",
      requestId: error instanceof ApiError ? error.requestId : undefined,
    };
  }
}

const CODES: ObservationState["code"][] = [
  "invalid_input",
  "unauthorized",
  "forbidden",
  "dependency_unavailable",
  "unknown",
];

export async function recordObservation(
  _previous: ObservationState,
  formData: FormData,
): Promise<ObservationState> {
  const value = (key: string) => String(formData.get(key) ?? "").trim();
  const productId = value("product_id");
  const payload = {
    product_id: productId,
    recorded_cost: value("recorded_cost"),
    supply: value("supply"),
    demand: value("demand"),
    competitor_cost: value("competitor_cost"),
  };

  if (Object.values(payload).some((field) => field === "")) {
    return { kind: "error", code: "invalid_input" };
  }

  try {
    await api.recordPricingObservation(payload);
    revalidatePath("/backoffice/pricing");
    return { kind: "success", productId };
  } catch (error) {
    const code =
      error instanceof ApiError && CODES.includes(error.code as ObservationState["code"])
        ? (error.code as ObservationState["code"])
        : "unknown";
    return {
      kind: "error",
      code,
      requestId: error instanceof ApiError ? error.requestId : undefined,
    };
  }
}