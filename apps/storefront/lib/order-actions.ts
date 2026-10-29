"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type {
  InventoryAdjustmentState,
  OrderActionState,
  ReorderState,
} from "./action-states";

const CODES = [
  "conflict",
  "not_found",
  "invalid_input",
  "unauthorized",
  "forbidden",
  "dependency_unavailable",
] as const;

type Code = (typeof CODES)[number];

function failure(error: unknown): { code: Code | "unknown"; requestId?: string } {
  if (error instanceof ApiError && (CODES as readonly string[]).includes(error.code)) {
    return { code: error.code as Code, requestId: error.requestId };
  }
  return { code: "unknown" };
}

const TRANSITIONS = ["ready", "in_transit", "delivered", "exception"] as const;

export async function transitionShipment(
  _previous: OrderActionState,
  formData: FormData,
): Promise<OrderActionState> {
  const orderId = String(formData.get("order_id") ?? "").trim();
  const status = String(formData.get("status") ?? "").trim();
  if (!orderId || !(TRANSITIONS as readonly string[]).includes(status)) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const shipment = await api.transitionShipment(
      orderId,
      status as (typeof TRANSITIONS)[number],
    );
    revalidatePath(`/backoffice/orders/${orderId}`);
    revalidatePath("/backoffice/orders");
    return { kind: "success", status: shipment.status };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function cancelOrder(
  _previous: OrderActionState,
  formData: FormData,
): Promise<OrderActionState> {
  const orderId = String(formData.get("order_id") ?? "").trim();
  const reason = String(formData.get("reason") ?? "").trim();
  if (!orderId || reason.length < 3 || reason.length > 300) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const result = await api.cancelOperatorOrder(orderId, reason);
    revalidatePath(`/backoffice/orders/${orderId}`);
    revalidatePath("/backoffice/orders");
    return {
      kind: "success",
      status: result.status,
      refundTotal: result.refund_total,
    };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function refundOrder(
  _previous: OrderActionState,
  formData: FormData,
): Promise<OrderActionState> {
  const orderId = String(formData.get("order_id") ?? "").trim();
  const amount = String(formData.get("amount") ?? "").trim();
  const reason = String(formData.get("reason") ?? "").trim();
  if (
    !orderId ||
    !/^(0|[1-9][0-9]{0,13})(\.[0-9]{1,6})?$/.test(amount) ||
    reason.length < 3 ||
    reason.length > 300
  ) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const result = await api.refundOperatorOrder(orderId, amount, reason);
    revalidatePath(`/backoffice/orders/${orderId}`);
    revalidatePath("/backoffice/orders");
    return {
      kind: "success",
      status: result.status,
      refundTotal: result.refund_total,
      amount: result.amount,
    };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function adjustInventory(
  _previous: InventoryAdjustmentState,
  formData: FormData,
): Promise<InventoryAdjustmentState> {
  const productId = String(formData.get("product_id") ?? "").trim();
  const rawDelta = String(formData.get("quantity_delta") ?? "").trim();
  const reason = String(formData.get("reason") ?? "").trim();
  const delta = Number.parseInt(rawDelta, 10);
  if (
    !productId ||
    !/^-?[0-9]{1,5}$/.test(rawDelta) ||
    Number.isNaN(delta) ||
    delta === 0 ||
    Math.abs(delta) > 10_000 ||
    reason.length < 3 ||
    reason.length > 300
  ) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const result = await api.adjustInventory(productId, delta, reason);
    revalidatePath("/backoffice/inventory");
    return {
      kind: "success",
      onHand: result.on_hand,
      available: result.available,
    };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function cancelOwnOrder(
  _previous: OrderActionState,
  formData: FormData,
): Promise<OrderActionState> {
  const orderId = String(formData.get("order_id") ?? "").trim();
  const reasonCode = String(formData.get("reason_code") ?? "").trim();
  const reason = String(formData.get("reason") ?? "").trim();
  const codes = [
    "changed_mind",
    "ordered_by_mistake",
    "wrong_item",
    "found_cheaper",
    "delivery_too_slow",
    "other",
  ];
  if (
    !orderId ||
    !codes.includes(reasonCode) ||
    (reasonCode === "other" && (reason.length < 3 || reason.length > 300))
  ) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const result = await api.cancelOwnOrder(orderId, {
      reason_code: reasonCode,
      ...(reasonCode === "other" ? { reason } : {}),
    });
    revalidatePath(`/orders/${orderId}`);
    revalidatePath("/account/orders");
    return { kind: "success", status: result.status };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function reorderOwnOrder(
  _previous: ReorderState,
  formData: FormData,
): Promise<ReorderState> {
  const orderId = String(formData.get("order_id") ?? "").trim();
  if (!orderId) return { kind: "error", code: "not_found" };
  try {
    const result = await api.reorder(orderId);
    revalidatePath("/cart");
    revalidatePath(`/orders/${orderId}`);
    return {
      kind: "success",
      added: result.added.length,
      skipped: result.skipped.map((item) => ({
        name: item.product_name,
        reason: item.reason,
      })),
    };
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") {
      return { kind: "error", code: "not_found" };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "error", code: "unauthorized" };
    }
    return { kind: "error", code: "unknown" };
  }
}
