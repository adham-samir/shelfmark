"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { Locale } from "@/lib/types";
import { attributeLabel, categoryLabel, facetValueLabel, translator } from "@/lib/i18n";
import { formatMoney } from "@/lib/format";
import { COMPARE_LIMIT, compareHref, useCompare } from "@/lib/compare-client";
import { AddSelectedButton } from "./add-selected";
import { IconArrowBack, IconClose, IconCompare } from "./icons";

const ROW_ORDER = ["brand", "screen", "storage", "memory", "connectivity", "battery", "feature"];

/**
 * Comparison lives in a dock at the foot of the catalog.
 *
 * The previous design reserved a permanent 344px column for it, which cost ~21%
 * of the desktop width whether or not anything was selected. The dock appears
 * only when there is something to compare, shows what is inside, and expands to
 * the full matrix on request.
 */
export function CompareDock({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const { entries, ready, remove, clear } = useCompare();
  const [open, setOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const toggleRef = useRef<HTMLButtonElement | null>(null);

  // Escape closes the drawer and returns focus to the control that opened it.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // Selecting nothing should not leave an empty expanded drawer behind.
  useEffect(() => {
    if (entries.length === 0) setOpen(false);
  }, [entries.length]);

  if (!ready || entries.length === 0) return null;

  const attributeKeys = Array.from(
    new Set(entries.flatMap((entry) => Object.keys(entry.attributes))),
  )
    .sort((a, b) => {
      const ai = ROW_ORDER.indexOf(a);
      const bi = ROW_ORDER.indexOf(b);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    })
    .slice(0, 8);

  const basicKeys = attributeKeys.filter((key) => key === "brand");
  const specKeys = attributeKeys.filter((key) => key !== "brand");
  const categoriesDiffer = new Set(entries.flatMap((entry) => entry.categories)).size > 1;
  const inStockIds = entries
    .filter((entry) => entry.availability === "in_stock")
    .map((entry) => entry.id);

  return (
    <>
      <div className="dock" role="region" aria-labelledby="dock-heading">
        <div className="dock-inner">
          <p className="dock-summary" id="dock-heading">
            <IconCompare size={16} aria-hidden="true" />
            {t("compare.selectedCount", {
              count: entries.length,
              limit: COMPARE_LIMIT,
            })}
          </p>

          <ul className="dock-thumbs">
            {entries.map((entry) => (
              <li className="dock-thumb" key={entry.id}>
                {entry.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={entry.image} alt="" />
                ) : (
                  <span className="dock-thumb-fallback" aria-hidden="true" />
                )}
                <span className="dock-thumb-name">{entry.name}</span>
                <button
                  type="button"
                  className="dock-thumb-remove"
                  onClick={() => remove(entry.id)}
                  aria-label={`${t("compare.remove")} — ${entry.name}`}
                >
                  <IconClose size={11} />
                </button>
              </li>
            ))}
          </ul>

          <div className="dock-actions">
            <button type="button" className="btn btn-sm btn-quiet" onClick={clear}>
              {t("compare.clear")}
            </button>
            <button
              ref={toggleRef}
              type="button"
              className="btn btn-sm"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              aria-controls="compare-drawer"
            >
              {open ? t("compare.hide") : t("compare.compare")}
            </button>
            <Link className="btn btn-sm btn-primary" href={compareHref(entries)}>
              {t("compare.open")}
            </Link>
          </div>
        </div>
      </div>

      {open ? (
        <div
          className="dock-drawer"
          id="compare-drawer"
          ref={drawerRef}
          role="dialog"
          aria-modal="false"
          aria-labelledby="compare-drawer-heading"
        >
          <div className="dock-drawer-inner">
            <div className="dock-drawer-head">
              <h2 id="compare-drawer-heading">{t("compare.title")}</h2>
              <button
                type="button"
                className="btn btn-sm btn-quiet"
                onClick={() => {
                  setOpen(false);
                  toggleRef.current?.focus();
                }}
              >
                <IconClose size={13} />
                {t("compare.hide")}
              </button>
            </div>

            <div className="dock-table-scroll">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th scope="col">{t("compare.product")}</th>
                    {entries.map((entry) => (
                      <th scope="col" key={entry.id}>
                        {entry.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="band">
                    <th scope="colgroup" colSpan={entries.length + 1}>
                      {t("compare.basic")}
                    </th>
                  </tr>
                  <tr>
                    <th scope="row">{t("compare.category")}</th>
                    {entries.map((entry) => (
                      <td key={entry.id}>
                        {entry.categories
                          .map((category) => categoryLabel(t, category))
                          .join(t("common.listSep"))}
                      </td>
                    ))}
                  </tr>
                  {basicKeys.map((key) => (
                    <tr key={key}>
                      <th scope="row">{attributeLabel(t, key)}</th>
                      {entries.map((entry) => (
                        <td key={entry.id} dir="ltr">
                          {entry.attributes[key]
                            ? facetValueLabel(t, entry.attributes[key])
                            : t("compare.missing")}
                        </td>
                      ))}
                    </tr>
                  ))}

                  {specKeys.length ? (
                    <>
                      <tr className="band">
                        <th scope="colgroup" colSpan={entries.length + 1}>
                          {t("compare.bandSpecs")}
                        </th>
                      </tr>
                      {specKeys.map((key) => (
                        <tr key={key}>
                          <th scope="row">{attributeLabel(t, key)}</th>
                          {entries.map((entry) => (
                            <td key={entry.id} dir="ltr">
                              {entry.attributes[key]
                                ? facetValueLabel(t, entry.attributes[key])
                                : t("compare.missing")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  ) : null}

                  <tr className="band">
                    <th scope="colgroup" colSpan={entries.length + 1}>
                      {t("compare.bandPrice")}
                    </th>
                  </tr>
                  <tr>
                    <th scope="row">{t("compare.price")}</th>
                    {entries.map((entry) => (
                      <td className="num" key={entry.id}>
                        {formatMoney(entry.price, locale)} {entry.currency}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row">{t("compare.availability")}</th>
                    {entries.map((entry) => (
                      <td key={entry.id}>
                        <span
                          className="chip"
                          data-tone={
                            entry.availability === "in_stock" ? "success" : "neutral"
                          }
                        >
                          {entry.availability === "in_stock"
                            ? t("card.inStock")
                            : t("card.outOfStock")}
                        </span>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            {categoriesDiffer ? (
              <p className="notice" data-tone="warn">
                {t("compare.incompatible")}
              </p>
            ) : null}

            <div className="dock-drawer-actions">
              <p className="field-hint">{t("compare.addSelectedHint")}</p>
              <AddSelectedButton
                productIds={inStockIds}
                locale={locale}
                label={`${t("compare.addSelected")} (${inStockIds.length})`}
                disabled={inStockIds.length === 0}
              />
              <Link className="btn btn-primary" href={compareHref(entries)}>
                {t("compare.open")}
                <IconArrowBack size={14} style={{ transform: "rotate(180deg)" }} />
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
