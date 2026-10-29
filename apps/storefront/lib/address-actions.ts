"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type { AddressFormState } from "./action-states";

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

const PHONE = /^\+?[0-9][0-9 -]{6,19}$/;

function read(formData: FormData) {
  return {
    label: String(formData.get("label") ?? "").trim(),
    recipient_name: String(formData.get("recipient_name") ?? "").trim(),
    phone: String(formData.get("phone") ?? "").trim(),
    city: String(formData.get("city") ?? "").trim(),
    address_line: String(formData.get("address_line") ?? "").trim(),
    is_default: formData.get("is_default") === "on",
  };
}

function valid(address: ReturnType<typeof read>): boolean {
  return (
    address.label.length >= 1 &&
    address.label.length <= 60 &&
    address.recipient_name.length >= 2 &&
    PHONE.test(address.phone) &&
    address.city.length >= 2 &&
    address.address_line.length >= 5 &&
    address.address_line.length <= 300
  );
}

export async function createAddress(
  _previous: AddressFormState,
  formData: FormData,
): Promise<AddressFormState> {
  const address = read(formData);
  if (!valid(address)) return { kind: "error", code: "invalid_input" };
  try {
    await api.createAddress(address);
    revalidatePath("/account/addresses");
    revalidatePath("/checkout");
    return { kind: "success", action: "created" };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function updateAddress(
  _previous: AddressFormState,
  formData: FormData,
): Promise<AddressFormState> {
  const addressId = String(formData.get("address_id") ?? "").trim();
  const address = read(formData);
  if (!addressId || !valid(address)) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    await api.updateAddress(addressId, address);
    revalidatePath("/account/addresses");
    revalidatePath("/checkout");
    return { kind: "success", action: "updated" };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}

export async function deleteAddress(
  _previous: AddressFormState,
  formData: FormData,
): Promise<AddressFormState> {
  const addressId = String(formData.get("address_id") ?? "").trim();
  if (!addressId) return { kind: "error", code: "invalid_input" };
  try {
    await api.deleteAddress(addressId);
    revalidatePath("/account/addresses");
    revalidatePath("/checkout");
    return { kind: "success", action: "deleted" };
  } catch (error) {
    return { kind: "error", ...failure(error) };
  }
}
