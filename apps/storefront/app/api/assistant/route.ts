import { api } from "@/lib/api";
import { asLocale, badRequest, errorResponse, isUuid, readJson } from "@/lib/http";
import { forbiddenOrigin, sameOrigin } from "@/lib/origin";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!sameOrigin(request)) return forbiddenOrigin();
  const payload = await readJson(request);
  if (!payload) return badRequest("invalid_input", "A JSON body is required.");
  const message = typeof payload.message === "string" ? payload.message.trim() : "";
  if (!message) return badRequest("invalid_input", "message is required.");
  if (message.length > 1000) return badRequest("invalid_input", "message is too long.");
  const orderId = payload.order_id;
  if (orderId !== undefined && orderId !== null && orderId !== "" && !isUuid(orderId)) {
    return badRequest("invalid_input", "order_id must be a UUID.");
  }

  try {
    const answer = await api.assistant({
      message,
      locale: asLocale(payload.locale),
      ...(isUuid(orderId) ? { order_id: orderId } : {}),
    });
    return Response.json(answer);
  } catch (error) {
    return errorResponse(error);
  }
}