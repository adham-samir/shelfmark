"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Locale, Product } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { ProductCard } from "./product-card";
import { IconMic } from "./icons";

type Phase =
  | "checking"
  | "idle"
  | "recording"
  | "processing"
  | "transcript"
  | "unsupported"
  | "denied"
  | "empty"
  | "provider_missing"
  | "rejected"
  | "failed";

/** Filename extensions that match the media type the browser actually produced. */
const AUDIO_EXTENSIONS: Record<string, string> = {
  "audio/webm": "webm",
  "audio/ogg": "ogg",
  "audio/mp4": "m4a",
  "audio/x-m4a": "m4a",
  "audio/m4a": "m4a",
  "audio/mpeg": "mp3",
  "audio/wav": "wav",
  "audio/x-wav": "wav",
  "audio/flac": "flac",
};

export function VoiceSearchPanel({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [phase, setPhase] = useState<Phase>("checking");
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [items, setItems] = useState<Product[]>([]);
  const [detail, setDetail] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    const supported =
      typeof window !== "undefined" &&
      typeof window.MediaRecorder !== "undefined" &&
      typeof navigator.mediaDevices?.getUserMedia === "function";
    setPhase(supported ? "idle" : "unsupported");
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const stopTracks = () => {
    recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const upload = async (blob: Blob) => {
    setPhase("processing");
    // Browsers report a codec alongside the type ("audio/webm;codecs=opus").
    // Send the bare type, and name the file after it, so Safari's mp4 recording
    // is not mislabelled as a webm one.
    const type = (blob.type || "audio/webm").split(";")[0].trim() || "audio/webm";
    const extension = AUDIO_EXTENSIONS[type] ?? "webm";
    const form = new FormData();
    form.append("audio", new File([blob], `recording.${extension}`, { type }));
    form.append("locale", locale);
    try {
      const response = await fetch("/api/search/voice", { method: "POST", body: form });
      const payload = (await response.json().catch(() => null)) as
        | {
            transcript?: string;
            items?: Product[];
            error?: { code?: string; message?: string };
          }
        | null;
      if (!response.ok || !payload) {
        const message = payload?.error?.message ?? "";
        setDetail(message);
        if (/api key is not configured/i.test(message)) setPhase("provider_missing");
        else if (payload?.error?.code === "empty_transcript") setPhase("empty");
        else if (payload?.error?.code === "unsupported_media") setPhase("rejected");
        else setPhase("failed");
        return;
      }
      const text = payload.transcript ?? "";
      setTranscript(text);
      setItems(payload.items ?? []);
      setPhase(text.trim() ? "transcript" : "empty");
    } catch {
      setPhase("failed");
    }
  };

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stopTracks();
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (!blob.size) {
          setPhase("empty");
          return;
        }
        void upload(blob);
      };
      recorder.start();
      setSeconds(0);
      setPhase("recording");
      timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch (error) {
      const name = error instanceof Error ? error.name : "";
      setPhase(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "failed");
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
  };

  const reset = () => {
    stopTracks();
    setTranscript("");
    setItems([]);
    setDetail("");
    setPhase("idle");
  };

  return (
    <div>
      <div className="panel">
        <div className="mic">
          <button
            type="button"
            className="mic-button"
            data-recording={phase === "recording"}
            onClick={phase === "recording" ? stop : start}
            disabled={phase === "processing" || phase === "checking"}
            aria-label={phase === "recording" ? t("voice.stop") : t("voice.start")}
          >
            <IconMic size={30} />
          </button>
          <p className="voice-status" aria-live="polite">
            {phase === "recording"
              ? `${t("voice.recording")} ${t("voice.seconds", { seconds })}`
              : phase === "processing"
                ? t("voice.processing")
                : t("voice.start")}
          </p>
          <p className="field-hint">{t("voice.intro")}</p>
          {phase === "recording" ? (
            <button type="button" className="btn btn-danger" onClick={stop}>
              {t("voice.stop")}
            </button>
          ) : null}
        </div>

        {phase === "unsupported" ? (
          <div className="state stack-4" data-tone="warn">
            <h2>{t("voice.unsupported")}</h2>
            <p>{t("voice.unsupportedHint")}</p>
            <div className="actions">
              <Link className="btn" href="/">
                {t("voice.textFallback")}
              </Link>
            </div>
          </div>
        ) : null}

        {phase === "rejected" ? (
          <div className="state stack-4" data-tone="error" role="alert">
            <h2>{t("voice.rejected")}</h2>
            <p>{t("voice.rejectedHint")}</p>
            <div className="actions">
              <button type="button" className="btn" onClick={reset}>
                {t("common.retry")}
              </button>
              <Link className="btn btn-quiet" href="/">
                {t("voice.textFallback")}
              </Link>
            </div>
          </div>
        ) : null}

        {phase === "denied" ? (
          <div className="state stack-4" data-tone="error" role="alert">
            <h2>{t("voice.denied")}</h2>
            <p>{t("voice.deniedHint")}</p>
            <div className="actions">
              <button type="button" className="btn" onClick={reset}>
                {t("common.retry")}
              </button>
              <Link className="btn btn-quiet" href="/">
                {t("voice.textFallback")}
              </Link>
            </div>
          </div>
        ) : null}

        {phase === "empty" ? (
          <div className="state stack-4" data-tone="warn" role="alert">
            <h2>{t("voice.empty")}</h2>
            <p>{t("voice.emptyHint")}</p>
            <div className="actions">
              <button type="button" className="btn" onClick={reset}>
                {t("voice.rerecord")}
              </button>
              <Link className="btn btn-quiet" href="/">
                {t("voice.textFallback")}
              </Link>
            </div>
          </div>
        ) : null}

        {phase === "provider_missing" ? (
          <div className="state stack-4" data-tone="warn" role="alert">
            <h2>{t("voice.providerMissing")}</h2>
            <p>{t("voice.providerMissingHint")}</p>
            {detail ? <p className="field-hint">{detail}</p> : null}
            <div className="actions">
              <Link className="btn" href="/">
                {t("voice.textFallback")}
              </Link>
              <button type="button" className="btn btn-quiet" onClick={reset}>
                {t("common.retry")}
              </button>
            </div>
          </div>
        ) : null}

        {phase === "failed" ? (
          <div className="state stack-4" data-tone="error" role="alert">
            <h2>{t("voice.failed")}</h2>
            <p>{detail || t("voice.failed")}</p>
            <div className="actions">
              <button type="button" className="btn" onClick={reset}>
                {t("common.retry")}
              </button>
              <Link className="btn btn-quiet" href="/">
                {t("voice.textFallback")}
              </Link>
            </div>
          </div>
        ) : null}

        {phase === "transcript" ? (
          <div className="stack-4">
            <div className="form-row">
              <label className="field-label" htmlFor="voice-transcript">
                {t("voice.transcript")}
              </label>
              <div className="row" style={{ display: "flex", gap: 8 }}>
                <input
                  id="voice-transcript"
                  className="input"
                  value={transcript}
                  onChange={(event) => setTranscript(event.target.value)}
                />
                <Link
                  className="btn btn-primary"
                  href={`/?q=${encodeURIComponent(transcript)}`}
                  aria-disabled={!transcript.trim()}
                >
                  {t("voice.searchTranscript")}
                </Link>
                <button type="button" className="btn btn-quiet" onClick={reset}>
                  {t("voice.rerecord")}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {phase === "transcript" ? (
        <section className="stack-4" aria-labelledby="voice-results">
          <div className="page-head">
            <h2 className="section-title" id="voice-results">
              {t("image.results")}
            </h2>
          </div>
          {items.length ? (
            <div className="product-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
              {items.map((product) => (
                <ProductCard key={product.product_id} product={product} locale={locale} />
              ))}
            </div>
          ) : (
            <div className="state" data-tone="warn">
              <h2>{t("voice.noResults")}</h2>
              <p>{t("image.noMatchHint")}</p>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}