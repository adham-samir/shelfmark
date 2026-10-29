/**
 * Initial states for the back-office server actions.
 *
 * These live outside the `"use server"` modules because Next.js only permits
 * async function exports from action files; exporting a state object there
 * fails the production build with "A 'use server' file can only export async
 * functions, found object".
 */

export interface InventoryRunState {
  kind: "idle" | "success" | "error";
  created?: number;
  reused?: number;
  code?: "unauthorized" | "forbidden" | "dependency_unavailable" | "unknown";
  message?: string;
}

export const initialInventoryRunState: InventoryRunState = { kind: "idle" };

export interface PricingRunState {
  kind: "idle" | "success" | "error";
  updated?: number;
  unchanged?: number;
  missing?: number;
  stale?: number;
  blocked?: number;
  alreadyApplied?: number;
  code?: "unauthorized" | "forbidden" | "dependency_unavailable" | "unknown";
  requestId?: string;
}

export const initialPricingRunState: PricingRunState = { kind: "idle" };

export interface ObservationState {
  kind: "idle" | "success" | "error";
  productId?: string;
  code?:
    | "invalid_input"
    | "unauthorized"
    | "forbidden"
    | "dependency_unavailable"
    | "unknown";
  requestId?: string;
}

export const initialObservationState: ObservationState = { kind: "idle" };

export interface SegmentationRunState {
  kind: "idle" | "success" | "error";
  classified?: number;
  insufficient?: number;
  eligible?: number;
  excluded?: number;
  code?: "unauthorized" | "forbidden" | "dependency_unavailable" | "unknown";
  requestId?: string;
}

export const initialSegmentationRunState: SegmentationRunState = { kind: "idle" };

export interface ReviewDecisionState {
  kind: "idle" | "success" | "error";
  status?: string;
  code?:
    | "conflict"
    | "not_found"
    | "invalid_input"
    | "unauthorized"
    | "forbidden"
    | "dependency_unavailable"
    | "unknown";
  requestId?: string;
}

export const initialReviewDecisionState: ReviewDecisionState = { kind: "idle" };

export interface OrderActionState {
  kind: "idle" | "success" | "error";
  status?: string;
  refundTotal?: string;
  amount?: string;
  code?:
    | "conflict"
    | "not_found"
    | "invalid_input"
    | "unauthorized"
    | "forbidden"
    | "dependency_unavailable"
    | "unknown";
  requestId?: string;
}

export const initialOrderActionState: OrderActionState = { kind: "idle" };

export interface InventoryAdjustmentState {
  kind: "idle" | "success" | "error";
  onHand?: number;
  available?: number;
  code?:
    | "conflict"
    | "not_found"
    | "invalid_input"
    | "unauthorized"
    | "forbidden"
    | "dependency_unavailable"
    | "unknown";
  requestId?: string;
}

export const initialInventoryAdjustmentState: InventoryAdjustmentState = {
  kind: "idle",
};
export interface AuthFormState {
  kind: "idle" | "error";
  code?:
    | "invalid_credentials"
    | "rate_limited"
    | "conflict"
    | "invalid_input"
    | "dependency_unavailable"
    | "unknown";
}

export const initialAuthFormState: AuthFormState = { kind: "idle" };

export interface AccountFormState {
  kind: "idle" | "success" | "error";
  code?: "invalid_input" | "unauthorized" | "dependency_unavailable" | "unknown";
}

export const initialAccountFormState: AccountFormState = { kind: "idle" };

export interface PasswordFormState {
  kind: "idle" | "success" | "error";
  revoked?: number;
  code?:
    | "invalid_input"
    | "wrong_password"
    | "unauthorized"
    | "dependency_unavailable"
    | "unknown";
}

export const initialPasswordFormState: PasswordFormState = { kind: "idle" };

export interface AddressFormState {
  kind: "idle" | "success" | "error";
  action?: "created" | "updated" | "deleted";
  code?:
    | "conflict"
    | "not_found"
    | "invalid_input"
    | "unauthorized"
    | "forbidden"
    | "dependency_unavailable"
    | "unknown";
  requestId?: string;
}

export const initialAddressFormState: AddressFormState = { kind: "idle" };
