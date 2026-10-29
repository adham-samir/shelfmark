import { randomUUID } from "node:crypto";
import { api } from "@/lib/api";
import { badRequest, errorResponse, isUuid, readJson } from "@/lib/http";

export const dynamic = "force-dynamic";

const EVENT_TYPES = ["view", "search_click", "compare", "add_to_cart"] as const;

export async function POST(request: Request) {
  const payload = await readJson(request);
  if (!payload) return badRequest("invalid_input", "A JSON body is required.");

  const productId = payload.product_id;
  const eventType = payload.event_type;
  const sessionId = payload.session_id;

  if (!isUuid(productId)) return badRequest("invalid_input", "product_id must be a UUID.");
  if (!EVENT_TYPES.includes(eventType as (typeof EVENT_TYPES)[number])) {
    return badRequest("invalid_input", "event_type is not supported.");
  }
  if (sessionId !== undefined && !isUuid(sessionId)) {
    return badRequest("invalid_input", "session_id must be a UUID.");
  }

  try {
    await api.recordEvent({
      event_id: randomUUID(),
      session_id: isUuid(sessionId) ? sessionId : randomUUID(),
      product_id: productId,
      event_type: eventType as (typeof EVENT_TYPES)[number],
      occurred_at: new Date().toISOString(),
      context: { surface: "storefront" },
    });
    return new Response(null, { status: 204 });
  } catch (error) {
    return errorResponse(error);
  }
}