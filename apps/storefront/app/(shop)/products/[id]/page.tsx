import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { Locale, Product } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { getProduct } from "@/lib/data";
import { getLocale } from "@/lib/locale";
import { attributeLabel, categoryLabel, translator } from "@/lib/i18n";
import { formatDateTime, formatMoney } from "@/lib/format";
import { plateFor, monogram } from "@/lib/plates";
import { ATTRIBUTE_ICONS, IconArrowBack } from "@/components/icons";
import { AddToCartButton } from "@/components/add-to-cart";
import { CompareToggle } from "@/components/compare-toggle";
import { RecordView } from "@/components/record-view";
import { ErrorState, Notice } from "@/components/states";
import { currentAccount } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    const product = await getProduct(id);
    return { title: `${product.name} — Smart-eCommerce` };
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") notFound();
    return { title: "المنتج — Smart-eCommerce" };
  }
}

async function recommendationProducts(productId: string): Promise<{
  items: Product[];
  strategy: string;
  basis: { browsing_events: number; purchased_items: number };
} | null> {
  try {
    const result = await api.recommendations(4);
    const ids = result.items.filter((id) => id !== productId).slice(0, 4);
    const products = await Promise.all(
      ids.map((id) => api.product(id).catch(() => null)),
    );
    return {
      items: products.filter((item): item is Product => item !== null),
      strategy: result.strategy,
      basis: result.basis,
    };
  } catch {
    return null;
  }
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const locale: Locale = await getLocale();
  const t = translator(locale);

  let product: Product;
  try {
    product = await getProduct(id);
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") notFound();
    return (
      <main className="page" id="main">
        <ErrorState
          locale={locale}
          title={t("product.unavailable")}
          hint={t("product.unavailableHint")}
          onRetryHref={`/products/${id}`}
        />
      </main>
    );
  }

  const account = await currentAccount("customer");
  const recommendations = account
    ? await recommendationProducts(product.product_id)
    : null;
  const plate = plateFor(product);
  const inStock = product.availability.status === "in_stock";
  const attributes = Object.entries(product.attributes);

  return (
    <main className="page" id="main">
      <RecordView productId={product.product_id} />

      <nav className="crumbs" aria-label="breadcrumb">
        <Link href="/">{t("nav.home")}</Link>
        <span aria-hidden="true">›</span>
        <Link href={`/?category=${product.categories[0] ?? ""}`}>
          {categoryLabel(t, product.categories[0] ?? "")}
        </Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail-grid">
        <section aria-labelledby="product-title">
          <div className="detail-plate">
            {plate ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={plate.src} alt={plate.alt} />
            ) : (
              <span className="placeholder">
                <strong>{monogram(product)}</strong>
                {t("card.noImage")}
              </span>
            )}
          </div>

        </section>

        <section aria-labelledby="product-title">
          <p className="eyebrow">{categoryLabel(t, product.categories[0] ?? "")}</p>
          <h1 id="product-title" className="product-title">
            {product.name}
          </h1>

          <div className="price-block">
            <span className="price-amount">{formatMoney(product.price.amount, locale)}</span>
            <span className="currency">{product.price.currency}</span>
          </div>
          <p className="field-hint">{t("product.priceNote")}</p>
          <p className="avail" data-status={product.availability.status}>
            {inStock ? t("card.inStock") : t("card.outOfStock")}
          </p>
          <p className="field-hint">
            {t("product.staleLabel")}{" "}
            <time dir="ltr" dateTime={product.price.updated_at}>
              {formatDateTime(product.price.updated_at, locale)}
            </time>
          </p>

          <div className="detail-actions">
            <AddToCartButton
              productId={product.product_id}
              locale={locale}
              disabled={!inStock}
              label={t("product.addToCart")}
              className="btn btn-dark btn-block"
            />
            <CompareToggle product={product} locale={locale} />
          </div>

          <div className="panel">
            <h2>{t("product.specs")}</h2>
            <dl className="detail-specs">
              {attributes.map(([key, value]) => {
                const Icon = ATTRIBUTE_ICONS[key];
                return (
                  <div key={key}>
                    <dt style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {Icon ? <Icon size={13} /> : null}
                      {attributeLabel(t, key)}
                    </dt>
                    <dd dir="ltr">{value}</dd>
                  </div>
                );
              })}
              <div>
                <dt>{t("compare.availability")}</dt>
                <dd>{inStock ? t("card.inStock") : t("card.outOfStock")}</dd>
              </div>
            </dl>
          </div>

          <div className="panel">
            <h2>{t("product.description")}</h2>
            <p dir="auto" style={{ color: "var(--graphite)", fontSize: "var(--text-base)" }}>
              {product.description}
            </p>
            <Notice tone="info">
              {t("card.synthetic")} · {t("common.demo")}
            </Notice>
          </div>
        </section>
      </div>

      <section style={{ marginBlockStart: 28 }} aria-labelledby="recommendations-heading">
        <div className="page-head">
          <div>
            <h2 id="recommendations-heading" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
              {t("product.recommendations")}
            </h2>
            <p>{t("product.recommendationsHint")}</p>
          </div>
          {recommendations ? (
            <span className="strategy">
              {t("product.strategy", { strategy: recommendations.strategy })}
              {" · "}
              {t("product.basis", {
                browsing: recommendations.basis.browsing_events,
                purchases: recommendations.basis.purchased_items,
              })}
            </span>
          ) : null}
        </div>

        {!account ? (
          <Notice tone="info">
            {t("product.recommendationsSignIn")}{" "}
            <Link href={`/login?next=${encodeURIComponent(`/products/${product.product_id}`)}`}>
              {t("auth.goLogin")}
            </Link>
          </Notice>
        ) : recommendations === null ? (
          <Notice tone="info">{t("product.recommendationsUnavailable")}</Notice>
        ) : recommendations.items.length ? (
          <div className="rail-list" style={{ marginBlockStart: 14 }}>
            {recommendations.items.map((item) => {
              const itemPlate = plateFor(item);
              return (
                <Link className="rail-card" key={item.product_id} href={`/products/${item.product_id}`}>
                  <span className="plate">
                    {itemPlate ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={itemPlate.src} alt="" />
                    ) : (
                      <span className="placeholder">
                        <strong>{monogram(item)}</strong>
                      </span>
                    )}
                  </span>
                  <span>
                    <h3>{item.name}</h3>
                    <span className="price-amount">
                      {formatMoney(item.price.amount, locale)} {item.price.currency}
                    </span>
                  </span>
                </Link>
              );
            })}
          </div>
        ) : (
          <Notice tone="info">{t("product.allSeen")}</Notice>
        )}
      </section>

      <div style={{ marginBlockStart: 22 }}>
        <Link className="btn btn-quiet" href="/">
          <IconArrowBack size={14} />
          {t("product.back")}
        </Link>
      </div>
    </main>
  );
}