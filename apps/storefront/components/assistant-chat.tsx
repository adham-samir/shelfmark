"use client";

import { useRef, useState } from "react";
import type { AssistantSource, Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  model?: string;
  sources?: AssistantSource[];
  errorCode?: string;
  errorHint?: string;
}

export function AssistantChat({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [orderId, setOrderId] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    setBusy(true);
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: message },
    ]);
    try {
      const response = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          locale,
          ...(orderId.trim() ? { order_id: orderId.trim() } : {}),
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
      requestAnimationFrame(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
      });
    }
  };

  return (
    <div className="chat">
      <div className="chat-log" ref={logRef} aria-live="polite" aria-relevant="additions">
        {messages.length === 0 ? (
          <div className="state" data-tone="info" style={{ textAlign: "start" }}>
            <h2>{t("assistant.suggestions")}</h2>
            <div className="chat-suggestions" style={{ marginBlockStart: 10 }}>
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
            <strong style={{ display: "block", fontSize: "var(--text-2xs)", color: "var(--muted)" }}>
              {message.role === "user" ? t("assistant.you") : t("assistant.assistant")}
            </strong>
            {message.errorHint ? (
              <p style={{ fontWeight: 600, marginBlockEnd: 4 }}>{message.errorHint}</p>
            ) : null}
            <p style={{ margin: 0 }}>{message.text}</p>
            {message.sources?.length ? (
              <span className="sources">
                <span className="visually-hidden">{t("assistant.sources")}: </span>
                {message.sources.map((source) => (
                  <span className="source-chip" key={`${source.kind}:${source.reference}`}>
                    {source.kind === "faq"
                      ? t("assistant.sourceFaq")
                      : source.kind === "product"
                        ? t("assistant.sourceProduct")
                        : t("assistant.sourceShipment")}
                    : {source.label}
                  </span>
                ))}
              </span>
            ) : null}
            {message.model ? <span className="meta">{message.model}</span> : null}
          </div>
        ))}
      </div>

      <div className="chat-compose">
        <div className="form-row">
          <label className="field-label" htmlFor="assistant-order">
            {t("assistant.orderId")}
          </label>
          <input
            id="assistant-order"
            className="input"
            value={orderId}
            onChange={(event) => setOrderId(event.target.value)}
            placeholder="00000000-0000-4000-8000-000000000000"
            dir="ltr"
            aria-describedby="assistant-order-hint"
          />
          <p className="field-hint" id="assistant-order-hint">
            {t("assistant.orderIdHint")}
          </p>
        </div>
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
            className="btn btn-dark"
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