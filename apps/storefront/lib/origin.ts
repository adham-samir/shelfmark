/**
 * Origin check for state-changing requests.
 *
 * Kept free of imports so it can be unit-tested without the Next.js runtime and
 * without pulling the API client into the module graph.
 *
 * The session cookies are `SameSite=Lax`, so a cross-site POST already arrives
 * without them. This check makes that posture explicit and testable, and covers
 * any future handler that accepts a form body. A request with no `Origin` header
 * is allowed: curl and server-to-server callers never send one, while a browser
 * always does for POST.
 */

export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  let parsed: URL;
  try {
    parsed = new URL(origin);
  } catch {
    return false;
  }
  // `URL.host` is host plus port, so a different port is rejected while the
  // scheme is not compared. Next.js compares Origin against Host the same way for
  // Server Actions, and a cross-scheme POST is already stopped by the schemeful
  // `SameSite=Lax` cookie. A proxy terminates TLS, so the forwarded host is the
  // one the browser saw.
  const forwarded = request.headers.get("x-forwarded-host");
  const host = forwarded ?? request.headers.get("host");
  if (!host) return false;
  return parsed.host === host;
}

export function forbiddenOrigin(): Response {
  return Response.json(
    {
      error: {
        code: "forbidden_origin",
        message: "The request origin does not match this host.",
      },
    },
    { status: 403 },
  );
}
