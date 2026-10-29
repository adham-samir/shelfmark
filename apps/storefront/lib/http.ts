import { ApiError } from "./api";
import type { Locale } from "./types";

export function errorResponse(error: unknown): Response {
  if (error instanceof ApiError) {
    return Response.json(
      {
        error: {
          code: error.code,
          message: error.message,
          request_id: error.requestId,
        },
      },
      { status: error.status && error.status >= 400 ? error.status : 503 },
    );
  }
  return Response.json(
    { error: { code: "unknown", message: "Unexpected server error." } },
    { status: 500 },
  );
}

export function badRequest(code: string, message: string): Response {
  return Response.json({ error: { code, message } }, { status: 422 });
}

export async function readJson(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const payload: unknown = await request.json();
    if (typeof payload !== "object" || payload === null) return null;
    return payload as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function asLocale(value: unknown): Locale {
  return value === "ar" ? "ar" : "en";
}

export function isUuid(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
  );
}