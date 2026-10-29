"use client";

import Link from "next/link";
import type { Locale } from "@/lib/types";
import { attributeLabel, categoryLabel, translator } from "@/lib/i18n";
import { formatMoney } from "@/lib/format";
import { compareHref, useCompare } from "@/lib/compare-client";
import { AddSelectedButton } from "./add-selected";
import { IconClose, IconArrowBack } from "./icons";

const ROW_ORDER = ["brand", "screen", "storage", "memory", "connectivity", "battery", "feature"];

export function CompareTray({ locale }: { locale: Locale }) {
  const t = translator(locale);
  const { entries, ready, remove, clear } = useCompare();

  const attributeKeys = Array.from(
    new Set(entries.flatMap((entry) => Object.keys(entry.attributes))),
  )
    .sort((a, b) => {
      const ai = ROW_ORDER.indexOf(a);
      const bi = ROW_ORDER.indexOf(b);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    })
    .slice(0, 6);

  const categoriesDiffer = new Set(entries.flatMap((entry) => entry.categories)).size > 1;
  const basicKeys = attributeKeys.filter((key) => key === "brand");
  const specKeys = attributeKeys.filter((key) => key !== "brand");
  const inStockIds = entries
    .filter((entry) => entry.availability === "in_stock")
    .map((entry) => entry.id);

  return (
    <aside className="tray" aria-labelledby="compare-heading">
      <div className="tray-head">
        <h2 id="compare-heading">
          {t("compare.title")}{" "}
          <span className="count">({ready ? entries.length : 0})</span>
        </h2>
        {entries.length ? (
          <button type="button" className="btn btn-quiet" onClick={clear} style={{ minHeight: 28 }}>
            <IconClose size={13} />
            <span className="visually-hidden">{t("compare.clear")}</span>
          </button>
        ) : null}
      </div>

      {!ready || entries.length === 0 ? (
        <div className="tray-empty">
          <strong>{t("compare.emptyTitle")}</strong>
          <p>{t("compare.emptyHint")}</p>
          <div className="tray-plinth" aria-hidden="true">
            <span className="tray-slot">+</span>
            <span className="tray-slot">+</span>
          </div>
          <div className="tray-actions">
            <button type="button" className="btn btn-amber btn-block" disabled>
              {t("compare.addSelected")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="tray-products" data-count={entries.length}>
            {entries.map((entry) => (
              <div className="tray-product" key={entry.id}>
                <div style={{ display: "flex", justifyContent: "flex-start" }}>
                  <button
                    type="button"
                    className="remove"
                    onClick={() => remove(entry.id)}
                    aria-label={`${t("compare.remove")} — ${entry.name}`}
                  >
                    <IconClose size={12} />
                  </button>
                </div>
                <div className="plate">
                  {entry.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={entry.image} alt="" />
                  ) : null}
                </div>
                <h3>{entry.name}</h3>
                <p className="price-amount">
                  {formatMoney(entry.price, locale)} <span className="currency">{entry.currency}</span>
                </p>
                <p className="avail" data-status={entry.availability}>
                  {entry.availability === "in_stock" ? t("card.inStock") : t("card.outOfStock")}
                </p>
              </div>
            ))}
          </div>

          <div className="tray-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("compare.product")}</th>
                  {entries.map((entry) => (
                    <th scope="col" key={entry.id}>
                      {entry.name.split(" ")[0]}
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
                      {entry.categories.map((category) => categoryLabel(t, category)).join("، ")}
                    </td>
                  ))}
                </tr>
                {basicKeys.map((key) => (
                  <tr key={key}>
                    <th scope="row">{attributeLabel(t, key)}</th>
                    {entries.map((entry) => (
                      <td key={entry.id}>{entry.attributes[key] ?? t("compare.missing")}</td>
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
                          <td key={entry.id}>{entry.attributes[key] ?? t("compare.missing")}</td>
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
                      {entry.availability === "in_stock" ? t("card.inStock") : t("card.outOfStock")}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
            {categoriesDiffer ? (
              <p className="tray-note">{t("compare.incompatible")}</p>
            ) : null}
          </div>

          <div className="tray-actions">
            <AddSelectedButton
              productIds={inStockIds}
              locale={locale}
              label={`${t("compare.addSelected")} (${entries.length})`}
              disabled={inStockIds.length === 0}
            />
            <Link className="btn btn-block" href={compareHref(entries)}>
              {t("compare.open")}
              <IconArrowBack size={14} style={{ transform: "rotate(180deg)" }} />
            </Link>
            <button type="button" className="btn btn-quiet btn-block" onClick={clear}>
              {t("compare.clear")}
            </button>
          </div>
          <p className="tray-note">{t("compare.addSelectedHint")}</p>
        </>
      )}
    </aside>
  );
}