import { api } from "@/lib/api";
import { asLocale, badRequest, errorResponse } from "@/lib/http";

export const dynamic = "force-dynamic";

const MAX_BYTES = 5 * 1024 * 1024;

export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return badRequest("invalid_input", "A multipart form is required.");
  }
  const audio = form.get("audio");
  if (!(audio instanceof File) || audio.size === 0) {
    return badRequest("invalid_input", "An audio recording is required.");
  }
  if (audio.size > MAX_BYTES) {
    return badRequest("invalid_input", "The recording is larger than 5 MB.");
  }

  try {
    const result = await api.voiceSearch(form, asLocale(form.get("locale")));
    if (!result.transcript.trim()) {
      return badRequest("empty_transcript", "No speech was recognised in the recording.");
    }
    return Response.json(result);
  } catch (error) {
    return errorResponse(error);
  }
}