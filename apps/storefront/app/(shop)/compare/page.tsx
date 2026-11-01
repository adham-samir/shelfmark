import { Fragment } from "react";
import Link from "next/link";
import type { Metadata } from "next";
import type { Locale, Product } from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import {
  attributeLabel,
  categoryLabel,
  facetValueLabel,
  translator,
} from "@/lib/i18n";
import { formatMoney } from "@/lib/format";
import { plateFor, monogram } from "@/lib/plates";
import { EmptyState, Notice } from "@/components/states";
import { CompareSync } from "@/components/compare-sync";
import { AddToCartButton } from "@/components/add-to-cart";

export const metadata: Metadata = { title: "المقارنة" };

const ROW_ORDER = ["brand", "screen", "storage", "memory", "connectivity", "battery", "feature"];

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const raw = params.ids;
  const ids = (Array.isArray(raw) ? raw[0] : raw ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 4);

  const results = await Promise.all(
    ids.map((id) => api.product(id).catch(() => null)),
  );
  const products = results.filter((item): item is Product => item !== null);
  const stale = results.some((item) => item === null);

  const attributeKeys = Array.from(
    new Set(products.flatMap((product) => Object.keys(product.attributes))),
  ).sort((a, b) => {
    const ai = ROW_ORDER.indexOf(a);
    const bi = ROW_ORDER.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const categories = new Set(products.flatMap((product) => product.categories));

  // Rows are grouped so a wide comparison reads as three short lists instead of
  // one long undifferentiated table.
  const groups: Array<{ key: string; label: string; keys: string[] }> = [
    {
      key: "basic",
      label: t("compare.basic"),
      keys: attributeKeys.filter((key) => key === "brand"),
    },
    {
      key: "specs",
      label: t("compare.bandSpecs"),
      keys: attributeKeys.filter((key) =>
        ["screen", "storage", "memory"].includes(key),
      ),
    },
    {
      key: "other",
      label: t("product.specsOther"),
      keys: attributeKeys.filter(
        (key) => !["brand", "screen", "storage", "memory"].includes(key),
      ),
    },
  ].filter((group) => group.keys.length > 0);

  return (
    <main className="page" id="main">
      <CompareSync ids={products.map((product) => product.product_id)} />
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.compare")}</p>
          <h1>{t("compare.pageTitle")}</h1>
          <p>{t("compare.pageIntro")}</p>
        </div>
        <Link className="btn" href="/">
          {t("product.back")}
        </Link>
      </div>

      {stale ? <Notice tone="warn">{t("compare.stale")}</Notice> : null}

      {products.length === 0 ? (
        <div className="stack-4">
          <EmptyState title={t("compare.emptyPage")} hint={t("compare.emptyHint")}>
            <Link className="btn" href="/">
              {t("product.back")}
            </Link>
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="compare-scroll stack-5" tabIndex={0}>
            <table className="compare-full">
              <caption className="visually-hidden">{t("compare.pageTitle")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("compare.product")}</th>
                  {products.map((product) => {
                    const plate = plateFor(product);
                    return (
                      <th scope="col" key={product.product_id}>
                        <div className="compare-head">
                          <span className="plate">
                            {plate ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img src={plate.src} alt="" />
                            ) : (
                              <span className="placeholder">
                                <strong>{monogram(product)}</strong>
                              </span>
                            )}
                          </span>
                          <Link href={`/products/${product.product_id}`}>{product.name}</Link>
                          <span className="field-hint">
                            {categoryLabel(t, product.categories[0] ?? "")}
                          </span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                <tr className="band">
                  <th scope="colgroup" colSpan={products.length + 1}>
                    {t("compare.category")}
                  </th>
                </tr>
                <tr>
                  <th scope="row">{t("compare.category")}</th>
                  {products.map((product) => (
                    <td key={product.product_id}>
                      {product.categories
                        .map((category) => categoryLabel(t, category))
                        .join(t("common.listSep"))}
                    </td>
                  ))}
                </tr>
                {groups.map((group) => (
                  <Fragment key={group.key}>
                    <tr className="band">
                      <th scope="colgroup" colSpan={products.length + 1}>
                        {group.label}
                      </th>
                    </tr>
                    {group.keys.map((key) => (
                      <tr key={key}>
                        <th scope="row">{attributeLabel(t, key)}</th>
                        {products.map((product) => (
                          <td key={product.product_id} dir="ltr">
                            {product.attributes[key]
                              ? facetValueLabel(t, product.attributes[key])
                              : t("compare.missing")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </Fragment>
                ))}
                <tr className="band">
                  <th scope="colgroup" colSpan={products.length + 1}>
                    {t("compare.bandPrice")}
                  </th>
                </tr>
                <tr>
                  <th scope="row">{t("compare.price")}</th>
                  {products.map((product) => (
                    <td className="num" key={product.product_id}>
                      {formatMoney(product.price.amount, locale)} {product.price.currency}
                    </td>
                  ))}
                </tr>
                <tr>
                  <th scope="row">{t("compare.availability")}</th>
                  {products.map((product) => (
                    <td key={product.product_id}>
                      <span
                        className="chip"
                        data-tone={
                          product.availability.status === "in_stock"
                            ? "success"
                            : "neutral"
                        }
                      >
                        {product.availability.status === "in_stock"
                          ? t("card.inStock")
                          : t("card.outOfStock")}
                      </span>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          {categories.size > 1 ? <Notice tone="warn">{t("compare.incompatible")}</Notice> : null}

          <div className="compare-actions">
            {products.map((product) => (
              <div key={product.product_id} className="compare-action">
                <p>{product.name}</p>
                <AddToCartButton
                  productId={product.product_id}
                  locale={locale}
                  disabled={product.availability.status !== "in_stock"}
                  className="btn btn-primary"
                />
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}