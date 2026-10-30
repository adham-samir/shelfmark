/**
 * Origin check for the cookie-authenticated route handlers.
 *
 * Server Actions already get this from Next.js; the Route Handlers do not, and
 * these four are the ones that carry a session. Node 26 runs TypeScript
 * directly, so this needs no build step.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

import { sameOrigin } from "../lib/origin.ts";

function request(headers: Record<string, string>): Request {
  return new Request("http://shop.example/api/checkout", {
    method: "POST",
    headers,
  });
}

test("a same-origin request is allowed", () => {
  assert.equal(
    sameOrigin(request({ origin: "http://shop.example", host: "shop.example" })),
    true,
  );
});

test("a different origin is rejected", () => {
  assert.equal(
    sameOrigin(request({ origin: "https://evil.example", host: "shop.example" })),
    false,
  );
});

test("a different port on the same host is rejected", () => {
  assert.equal(
    sameOrigin(request({ origin: "http://shop.example:8080", host: "shop.example" })),
    false,
  );
});

test("scheme alone is not compared, matching the Next.js Server Action rule", () => {
  // `URL.host` excludes the scheme, and Next.js compares Origin against Host the
  // same way. A cross-scheme POST is still stopped by the `SameSite=Lax` cookie,
  // which is schemeful; comparing scheme here would reject a legitimate
  // TLS-terminating proxy without adding protection.
  assert.equal(
    sameOrigin(request({ origin: "https://shop.example", host: "shop.example" })),
    true,
  );
});

test("a request with no Origin is allowed, for curl and server-to-server", () => {
  assert.equal(sameOrigin(request({ host: "shop.example" })), true);
});

test("a proxied request is compared against the forwarded host", () => {
  assert.equal(
    sameOrigin(
      request({
        origin: "https://shop.example",
        host: "internal:3000",
        "x-forwarded-host": "shop.example",
      }),
    ),
    true,
  );
  assert.equal(
    sameOrigin(
      request({
        origin: "https://evil.example",
        host: "internal:3000",
        "x-forwarded-host": "shop.example",
      }),
    ),
    false,
  );
});

test("a malformed Origin is rejected rather than treated as absent", () => {
  assert.equal(sameOrigin(request({ origin: "not a url", host: "shop.example" })), false);
});

test("a request with no Host at all is rejected", () => {
  assert.equal(sameOrigin(request({ origin: "http://shop.example" })), false);
});
