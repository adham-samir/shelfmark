import Link from "next/link";
import type { Locale, Product } from "@/lib/types";
import { attributeLabel, categoryLabel, translator } from "@/lib/i18n";
import { formatMoney } from "@/lib/format";
import { plateFor, monogram } from "@/lib/plates";
import { ATTRIBUTE_ICONS } from "./icons";
import { CompareToggle } from "./compare-toggle";
import { AddToCartButton } from "./add-to-cart";

const ATTRIBUTE_ORDER = ["screen", "storage", "memory", "connectivity", "battery", "feature", "brand"];

function orderedAttributes(product: Product): Array<[string, string]> {
  const entries = Object.entries(product.attributes);
  const rank = (key: string) => {
    const index = ATTRIBUTE_ORDER.indexOf(key);
    return index === -1 ? ATTRIBUTE_ORDER.length : index;
  };
  return entries.sort(([a], [b]) => rank(a) - rank(b)).slice(0, 3);
}

export function ProductCard({ product, locale }: { product: Product; locale: Locale }) {
  const t = translator(locale);
  const plate = plateFor(product);
  const inStock = product.availability.status === "in_stock";
  const category = product.categories[0] ?? "";

  return (
    <article className="card" data-product={product.product_id}>
      <div className="card-top">
        <CompareToggle product={product} locale={locale} />
      </div>

      <div className="card-plate">
        {plate ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={plate.src} alt={plate.alt} loading="lazy" />
        ) : (
          <span className="placeholder">
            <strong>{monogram(product)}</strong>
            {t("card.noImage")}
          </span>
        )}
      </div>

      <span className="badge" title={t("card.synthetic")}>
        {t("card.synthetic")}
      </span>

      <h3 className="card-title">
        <Link href={`/products/${product.product_id}`} title={t("card.view", { name: product.name })}>
          {product.name}
        </Link>
      </h3>

      <dl className="attrs">
        {orderedAttributes(product).map(([key, value]) => {
          const Icon = ATTRIBUTE_ICONS[key];
          return (
            <div className="attr" key={key}>
              {Icon ? <Icon size={13} /> : null}
              <dt className="key">{attributeLabel(t, key)}:</dt>
              <dd className="value" dir="ltr">{value}</dd>
            </div>
          );
        })}
      </dl>

      <p className="avail" data-status={product.availability.status}>
        {inStock ? t("card.inStock") : t("card.outOfStock")}
        {category ? <span className="visually-hidden"> — {categoryLabel(t, category)}</span> : null}
      </p>

      <p className="card-price">
        <span className="price-amount">
          {formatMoney(product.price.amount, locale)}
        </span>
        <span className="currency">{product.price.currency}</span>
      </p>

      <AddToCartButton
        productId={product.product_id}
        locale={locale}
        disabled={!inStock}
        className="btn btn-block"
      />
    </article>
  );
}