import { api, ApiError } from "@/lib/api";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const segment = url.searchParams.get("segment") ?? undefined;
  const referenceDate = url.searchParams.get("reference_date") ?? undefined;
  try {
    const { csv, filename } = await api.segmentsExport({ segment, referenceDate });
    return new Response(csv, {
      status: 200,
      headers: {
        "content-type": "text/csv; charset=utf-8",
        "content-disposition": `attachment; filename="${filename}"`,
        "cache-control": "no-store",
      },
    });
  } catch (error) {
    const status = error instanceof ApiError && error.status ? error.status : 502;
    return new Response("The segment export is unavailable.", {
      status,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "no-store",
      },
    });
  }
}