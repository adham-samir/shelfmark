import { api } from "@/lib/api";
import { badRequest, errorResponse, isUuid, readJson } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return Response.json(await api.cart());
  } catch (error) {
    return errorResponse(error);
  }
}

export async function POST(request: Request) {
  const payload = await readJson(request);
  if (!payload) return badRequest("invalid_input", "A JSON body is required.");
  const productId = payload.product_id;
  const quantity = payload.quantity ?? 1;
  if (!isUuid(productId)) {
    return badRequest("invalid_input", "product_id must be a UUID.");
  }
  if (typeof quantity !== "number" || !Number.isInteger(quantity) || quantity < 0 || quantity > 99) {
    return badRequest("invalid_input", "quantity must be an integer between 0 and 99.");
  }
  try {
    const cart = await api.setCartItem(productId, quantity);
    return Response.json(cart);
  } catch (error) {
    return errorResponse(error);
  }
}