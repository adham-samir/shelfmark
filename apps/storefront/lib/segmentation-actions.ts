"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type { SegmentationRunState } from "./action-states";

export async function runSegmentation(
  _previous: SegmentationRunState,
  _formData: FormData,
): Promise<SegmentationRunState> {
  try {
    const result = await api.runSegmentation();
    revalidatePath("/backoffice/segments");
    return {
      kind: "success",
      classified: result.classified,
      insufficient: result.insufficient_history,
      eligible: result.eligible_orders,
      excluded: result.excluded_orders,
    };
  } catch (error) {
    return {
      kind: "error",
      code:
        error instanceof ApiError &&
        ["unauthorized", "forbidden", "dependency_unavailable"].includes(error.code)
          ? (error.code as SegmentationRunState["code"])
          : "unknown",
      requestId: error instanceof ApiError ? error.requestId : undefined,
    };
  }
}