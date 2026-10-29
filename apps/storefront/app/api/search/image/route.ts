import { api, type CatalogQuery } from "@/lib/api";
import { badRequest, errorResponse } from "@/lib/http";

export const dynamic = "force-dynamic";

const MAX_BYTES = 5 * 1024 * 1024;

export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return badRequest("invalid_input", "A multipart form is required.");
  }
  const image = form.get("image");
  if (!(image instanceof File) || image.size === 0) {
    return badRequest("invalid_input", "An image file is required.");
  }
  if (image.size > MAX_BYTES) {
    return badRequest("invalid_input", "The image is larger than 5 MB.");
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(image.type)) {
    return badRequest("invalid_input", "Use a JPEG, PNG or WebP image.");
  }

  const category = form.get("category");
  const filter = form.get("filter");
  const query: CatalogQuery = {
    ...(typeof category === "string" && category ? { category } : {}),
    ...(typeof filter === "string" && filter.includes(":")
      ? { filters: { [filter.split(":", 1)[0]]: filter.split(":").slice(1).join(":") } }
      : {}),
  };

  try {
    const result = await api.imageSearch(form, query);
    return Response.json(result);
  } catch (error) {
    return errorResponse(error);
  }
}