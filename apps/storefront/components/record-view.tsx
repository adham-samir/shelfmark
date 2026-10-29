"use client";

import { useEffect } from "react";
import { useSession } from "./session-provider";

const SESSION_KEY = "smart_ecommerce_session";

function sessionId(): string {
  const stored = window.localStorage.getItem(SESSION_KEY);
  if (stored) return stored;
  const created = crypto.randomUUID();
  window.localStorage.setItem(SESSION_KEY, created);
  return created;
}

export function RecordView({
  productId,
  eventType = "view",
}: {
  productId: string;
  eventType?: "view" | "search_click";
}) {
  const { signedIn } = useSession();

  useEffect(() => {
    if (!signedIn) return;
    const controller = new AbortController();
    void fetch("/api/events", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        product_id: productId,
        event_type: eventType,
        session_id: sessionId(),
        context: { surface: "product-detail" },
      }),
      signal: controller.signal,
      keepalive: true,
    }).catch(() => undefined);
    return () => controller.abort();
  }, [productId, eventType, signedIn]);

  return null;
}
