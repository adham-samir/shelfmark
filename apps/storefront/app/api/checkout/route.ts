import { api } from "@/lib/api";
import { badRequest, errorResponse, readJson } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const payload = await readJson(request);
  if (!payload) return badRequest("invalid_input", "A JSON body is required.");

  const paymentToken = payload.payment_token;
  const idempotencyKey = payload.idempotency_key;
  const shipping = payload.shipping;

  if (typeof paymentToken !== "string" || !/^tok_sandbox_[A-Za-z0-9_-]{4,100}$/.test(paymentToken)) {
    return badRequest("invalid_input", "payment_token must start with tok_sandbox_.");
  }
  if (typeof idempotencyKey !== "string" || idempotencyKey.length < 16) {
    return badRequest("invalid_input", "idempotency_key must have at least 16 characters.");
  }
  if (typeof shipping !== "object" || shipping === null) {
    return badRequest("invalid_input", "shipping details are required.");
  }
  const address = shipping as Record<string, unknown>;
  for (const field of ["recipient_name", "phone", "city", "address_line"]) {
    if (typeof address[field] !== "string" || !(address[field] as string).trim()) {
      return badRequest("invalid_input", `shipping.${field} is required.`);
    }
  }

  try {
    const result = await api.checkout({
      payment_token: paymentToken,
      idempotency_key: idempotencyKey,
      shipping: {
        recipient_name: String(address.recipient_name),
        phone: String(address.phone),
        city: String(address.city),
        address_line: String(address.address_line),
      },
    });
    return Response.json(result, { status: 202 });
  } catch (error) {
    return errorResponse(error);
  }
}