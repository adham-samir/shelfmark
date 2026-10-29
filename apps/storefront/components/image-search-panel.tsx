"use client";

import { useRef, useState } from "react";
import type { ImageSearchItem, Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { ProductCard } from "./product-card";
import { IconCamera, IconClose } from "./icons";

const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp"];

type Phase =
  | { kind: "idle" }
  | { kind: "preview"; file: File; url: string }
  | { kind: "working"; file: File; url: string }
  | {
      kind: "results";
      file: File;
      url: string;
      items: ImageSearchItem[];
      model: string;
    }
  | { kind: "error"; file: File | null; url: string | null; title: string; hint: string; detail?: string };

export function ImageSearchPanel({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [category, setCategory] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const choose = (file: File) => {
    if (!ALLOWED.includes(file.type)) {
      setPhase({ kind: "error", file: null, url: null, title: t("image.invalidType"), hint: t("image.formats") });
      return;
    }
    if (file.size > MAX_BYTES) {
      setPhase({ kind: "error", file: null, url: null, title: t("image.invalidSize"), hint: t("image.formats") });
      return;
    }
    const url = URL.createObjectURL(file);
    setPhase({ kind: "preview", file, url });
  };

  const reset = () => {
    if (phase.kind !== "idle" && "url" in phase && phase.url) URL.revokeObjectURL(phase.url);
    setPhase({ kind: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  };

  const search = async (file: File, url: string) => {
    setPhase({ kind: "working", file, url });
    const form = new FormData();
    form.append("image", file);
    if (category) form.append("category", category);
    try {
      const response = await fetch("/api/search/image", { method: "POST", body: form });
      const payload = (await response.json().catch(() => null)) as
        | {
            items?: ImageSearchItem[];
            model_version?: string;
            error?: { code?: string; message?: string };
          }
        | null;
      if (!response.ok || !payload) {
        setPhase({
          kind: "error",
          file,
          url,
          title: t("image.failed"),
          hint: t("image.failedHint"),
          detail: payload?.error?.message,
        });
        return;
      }
      setPhase({
        kind: "results",
        file,
        url,
        items: payload.items ?? [],
        model: payload.model_version ?? "",
      });
    } catch {
      setPhase({ kind: "error", file, url, title: t("image.failed"), hint: t("image.failedHint") });
    }
  };

  return (
    <div>
      <div className="panel">
        <div className="form-row" style={{ maxWidth: 320 }}>
          <label className="field-label" htmlFor="image-category">
            {t("filters.categories")}
          </label>
          <select
            id="image-category"
            className="input"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">{t("filters.allCategories")}</option>
            <option value="phones">{t("category.phones")}</option>
            <option value="headphones">{t("category.headphones")}</option>
            <option value="laptops">{t("category.laptops")}</option>
          </select>
        </div>

        <div
          className="dropzone"
          style={{ marginBlockStart: 14 }}
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const file = event.dataTransfer.files?.[0];
            if (file) choose(file);
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
          }}
        >
          <IconCamera size={26} />
          <strong>{t("image.drop")}</strong>
          <p>{t("image.formats")}</p>
        </div>
        <label className="visually-hidden" htmlFor="image-file">
          {t("image.drop")}
        </label>
        <input
          id="image-file"
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="visually-hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) choose(file);
          }}
        />

        {phase.kind === "preview" ? (
          <div className="preview" style={{ marginBlockStart: 14 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={phase.url} alt={t("image.preview")} />
            <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
              <button
                type="button"
                className="btn btn-dark"
                onClick={() => void search(phase.file, phase.url)}
              >
                {t("image.search")}
              </button>
              <button type="button" className="btn btn-quiet" onClick={reset}>
                <IconClose size={13} />
                {t("image.clear")}
              </button>
            </div>
          </div>
        ) : null}

        {phase.kind === "working" ? (
          <div className="preview" style={{ marginBlockStart: 14 }} aria-busy="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={phase.url} alt={t("image.preview")} />
            <p role="status" style={{ textAlign: "center" }}>
              {t("image.searching")}
            </p>
          </div>
        ) : null}

        {phase.kind === "error" ? (
          <div className="state" data-tone="error" role="alert" style={{ marginBlockStart: 14 }}>
            <h2>{phase.title}</h2>
            <p>{phase.hint}</p>
            {phase.detail ? <p className="field-hint">{phase.detail}</p> : null}
            <div className="actions">
              <button type="button" className="btn" onClick={reset}>
                {t("common.retry")}
              </button>
              <a className="btn btn-quiet" href="/">
                {t("image.fallback")}
              </a>
            </div>
          </div>
        ) : null}
      </div>

      {phase.kind === "results" ? (
        <section style={{ marginBlockStart: 18 }} aria-labelledby="image-results">
          <div className="page-head">
            <div>
              <h2 id="image-results" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
                {t("image.results")}
              </h2>
              <p>{t("image.model", { model: phase.model })}</p>
            </div>
            <span className="pill">{t("image.syntheticNote")}</span>
          </div>

          {phase.items.length ? (
            <div className="product-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
              {phase.items.map((entry) => (
                <div key={entry.product.product_id} style={{ position: "relative" }}>
                  <ProductCard product={entry.product} locale={locale} />
                  <p className="pill" style={{ marginBlockStart: 6 }}>
                    {t("image.score")}: {entry.score.toFixed(3)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="state" data-tone="warn">
              <h2>{t("image.noMatch")}</h2>
              <p>{t("image.noMatchHint")}</p>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}