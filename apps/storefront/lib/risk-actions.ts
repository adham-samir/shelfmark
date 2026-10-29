"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError } from "@/lib/api";
import type { ReviewDecisionState } from "./action-states";

export async function decideReview(
  _previous: ReviewDecisionState,
  formData: FormData,
): Promise<ReviewDecisionState> {
  const assessmentId = String(formData.get("assessment_id") ?? "").trim();
  const decision = String(formData.get("decision") ?? "").trim();
  if (!assessmentId || (decision !== "allow" && decision !== "decline")) {
    return { kind: "error", code: "invalid_input" };
  }
  try {
    const result = await api.decideReview(assessmentId, decision);
    revalidatePath("/backoffice/risk");
    return { kind: "success", status: result.status };
  } catch (error) {
    return {
      kind: "error",
      code:
        error instanceof ApiError &&
        [
          "conflict",
          "not_found",
          "invalid_input",
          "unauthorized",
          "forbidden",
          "dependency_unavailable",
        ].includes(error.code)
          ? (error.code as ReviewDecisionState["code"])
          : "unknown",
      requestId: error instanceof ApiError ? error.requestId : undefined,
    };
  }
}