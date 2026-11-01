"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import type { AssistantSource, Locale, OrderSummary } from "@/lib/types";
import { statusLabel, translator } from "@/lib/i18n";
import { formatDateTime, formatMoney } from "@/lib/format";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  model?: string;
  sources?: AssistantSource[];
  errorCode?: string;
  errorHint?: string;
}

/** One-tap questions offered while an order is attached. */
const ORDER_QUESTIONS = [
  "assistant.orderAskStatus",
  "assistant.orderAskItems",
  "assistant.orderAskCancel",
] as const;

export function AssistantChat({
  locale,
  orders,
}: {
  locale: Locale;
  orders: OrderSummary[];
}) {
  const t = translator(locale);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [attached, setAttached] = useState<OrderSummary | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    const orderId = attached?.order_id;
    setBusy(true);
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: message },
    ]);
    // Prior turns give the reply its thread; error bubbles are not real answers
    // and are left out so they never become context.
    const history = messages
      .filter((item) => !item.errorCode)
      .slice(-6)
      .map((item) => ({ role: item.role, content: item.text.slice(0, 2_000) }));

    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          locale,
          ...(orderId ? { order_id: orderId } : {}),
          ...(history.length ? { history } : {}),
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | {
            answer?: string;
            model?: string;
            sources?: AssistantSource[];
            error?: { code?: string; message?: string };
          }
        | null;

      if (!response.ok || !payload?.answer) {
        const code = payload?.error?.code ?? "unknown";
        const detail = payload?.error?.message ?? t("assistant.failed");
        const keyMissing = /api key is not configured/i.test(detail);
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: keyMissing ? t("assistant.providerMissingHint") : `${t("assistant.failedHint")} ${detail}`,
            errorCode: keyMissing ? "provider_missing" : code,
            errorHint: keyMissing ? t("assistant.providerMissing") : t("assistant.failed"),
          },
        ]);
        return;
      }

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: payload.answer ?? "",
          model: payload.model,
          sources: payload.sources ?? [],
        },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: t("assistant.failedHint"),
          errorCode: "network_error",
          errorHint: t("assistant.failed"),
        },
      ]);
    } finally {
      setBusy(false);
      // An attachment belongs to the message it was sent with.
      setAttached(null);
      requestAnimationFrame(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
      });
    }
  };

  return (
    <div className="chat">
      <div className="chat-log" ref={logRef} aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <h2>{t("assistant.suggestions")}</h2>
            <p className="field-hint">{t("assistant.emptyHint")}</p>
            <div className="chat-suggestions">
              <button type="button" onClick={() => send(t("assistant.suggestionOne"))}>
                {t("assistant.suggestionOne")}
              </button>
              <button type="button" onClick={() => send(t("assistant.suggestionTwo"))}>
                {t("assistant.suggestionTwo")}
              </button>
              <button type="button" onClick={() => send(t("assistant.suggestionThree"))}>
                {t("assistant.suggestionThree")}
              </button>
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <div className="bubble" data-role={message.role} key={message.id}>
            <strong className="meta">
              {message.role === "user" ? t("assistant.you") : t("assistant.assistant")}
            </strong>
            {message.errorHint ? (
              <p className="hint">{message.errorHint}</p>
            ) : null}
            <p style={{ margin: 0 }}>{message.text}</p>
            {message.sources?.length ? (
              <div className="sources">
                <span className="visually-hidden">{t("assistant.sources")}: </span>
                {message.sources.map((source) => {
                  const kind =
                    source.kind === "faq"
                      ? t("assistant.sourceFaq")
                      : source.kind === "product"
                        ? t("assistant.sourceProduct")
                        : t("assistant.sourceShipment");
                  const text = `${kind}: ${source.label}`;
                  const key = `${source.kind}:${source.reference}`;

                  if (source.kind === "product") {
                    return (
                      <Link
                        className="source-chip"
                        href={`/products/${source.reference}`}
                        key={key}
                      >
                        {text}
                      </Link>
                    );
                  }
                  if (source.kind === "shipment") {
                    return (
                      <Link
                        className="source-chip"
                        href={`/orders/${source.reference}`}
                        key={key}
                      >
                        {text}
                      </Link>
                    );
                  }
                  return (
                    <button
                      type="button"
                      className="source-chip"
                      key={key}
                      onClick={() => void send(source.label)}
                      disabled={busy}
                    >
                      {text}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {orders.length ? (
        <div className="order-attach">
          <button
            type="button"
            className="order-attach-head"
            aria-expanded={panelOpen}
            onClick={() => setPanelOpen((open) => !open)}
          >
            {t("assistant.orderPanel")}
          </button>
          {panelOpen ? (
            <ul className="order-list order-list-compact">
              {orders.map((order) => (
                <li className="order-row" key={order.order_id}>
                  <div className="order-row-id">
                    <code dir="ltr" title={order.order_id}>
                      {order.order_id.slice(-8)}
                    </code>
                    <p>
                      {t("orders.itemCount", { count: order.item_count })}
                      {" · "}
                      <time dateTime={order.created_at}>
                        {formatDateTime(order.created_at, locale)}
                      </time>
                    </p>
                  </div>
                  <div className="order-row-meta">
                    <span className="pill" data-status={order.status}>
                      {statusLabel(t, order.status)}
                    </span>
                    <span className="price-amount">
                      {formatMoney(order.subtotal, locale)} {order.currency}
                    </span>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => {
                        setAttached(order);
                        setPanelOpen(false);
                      }}
                    >
                      {t("assistant.orderAttach")}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          <Link className="order-attach-all" href="/account/orders">
            {t("assistant.orderViewAll")}
          </Link>
        </div>
      ) : (
        <p className="field-hint order-attach-all">{t("assistant.orderEmpty")}</p>
      )}

      <div className="chat-compose">
        {attached ? (
          <div className="chat-attachments">
            <span className="attachment-chip">
              {t("assistant.orderAttached", { id: attached.order_id.slice(-8) })}
              <button
                type="button"
                onClick={() => setAttached(null)}
                aria-label={t("assistant.orderDetach")}
                title={t("assistant.orderDetach")}
              >
                ×
              </button>
            </span>
            <div className="chat-suggestions">
              {ORDER_QUESTIONS.map((key) => (
                <button
                  type="button"
                  key={key}
                  onClick={() => void send(t(key))}
                  disabled={busy}
                >
                  {t(key)}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="row">
          <label className="visually-hidden" htmlFor="assistant-message">
            {t("assistant.placeholder")}
          </label>
          <textarea
            id="assistant-message"
            className="input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send(draft);
              }
            }}
            placeholder={t("assistant.placeholder")}
            rows={2}
            maxLength={1000}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void send(draft)}
            disabled={busy || !draft.trim()}
            aria-busy={busy}
          >
            {busy ? t("assistant.sending") : t("assistant.send")}
          </button>
        </div>
      </div>
    </div>
  );
}
