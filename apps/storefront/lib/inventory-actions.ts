"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type { InventoryRunState } from "./action-states";

export async function runInventoryPlanning(
  _previous: InventoryRunState,
  _formData: FormData,
): Promise<InventoryRunState> {
  try {
    const result = await api.runInventoryPlanning();
    revalidatePath("/backoffice/inventory");
    return {
      kind: "success",
      created: result.reorders_created,
      reused: result.reorders_reused,
    };
  } catch (error) {
    return {
      kind: "error",
      code:
        error instanceof ApiError &&
        ["unauthorized", "forbidden", "dependency_unavailable"].includes(error.code)
          ? (error.code as InventoryRunState["code"])
          : "unknown",
      message:
        error instanceof ApiError
          ? error.requestId
          : "unknown",
    };
  }
}
