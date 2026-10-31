import Link from "next/link";
import type { Metadata } from "next";
import type { Locale, Product } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { translator } from "@/lib/i18n";
import { formatMoney, multiplyMoney } from "@/lib/format";
import { plateFor, monogram } from "@/lib/plates";
import { EmptyState, ErrorState, Notice } from "@/components/states";
import { QuantityControl } from "@/components/quantity-control";
import { requireCustomer } from "@/lib/session";

export const metadata: Metadata = { title: "السلة — Smart-eCommerce" };

export default async function CartPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  await requireCustomer("/cart");

  try {
    const [cart, catalog] = await Promise.all([api.cart(), api.products({ limit: 100 })]);
    const byId = new Map<string, Product>(catalog.items.map((item) => [item.product_id, item]));

    if (!cart.items.length) {
      return (
        <main className="page page-narrow" id="main">
          <div className="page-head">
            <div>
              <p className="eyebrow">{t("nav.cart")}</p>
              <h1>{t("cart.title")}</h1>
              <p>{t("cart.intro")}</p>
            </div>
          </div>
          <div className="stack-4">
            <EmptyState title={t("cart.emptyTitle")} hint={t("cart.emptyHint")}>
              <Link className="btn btn-primary" href="/">
                {t("cart.browse")}
              </Link>
            </EmptyState>
          </div>
        </main>
      );
    }

    return (
      <main className="page" id="main">
        <div className="page-head">
          <div>
            <p className="eyebrow">{t("nav.cart")}</p>
            <h1>{t("cart.title")}</h1>
            <p>{t("cart.intro")}</p>
          </div>
          <span className="chip" data-tone="info">
            {t("cart.priceRecheck")}
          </span>
        </div>

        <div className="page-split stack-5">
          <ul className="cart-lines">
            {cart.items.map((item) => {
              const product = byId.get(item.product_id);
              const plate = product ? plateFor(product) : null;
              const name = product?.name ?? item.product_id;
              return (
                <li className="cart-line" key={item.product_id}>
                  <span className="plate">
                    {plate ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={plate.src} alt="" />
                    ) : (
                      <span className="placeholder">
                        <strong>{product ? monogram(product) : "—"}</strong>
                      </span>
                    )}
                  </span>

                  <div className="line-body">
                    <h2 className="line-title">
                      <Link href={`/products/${item.product_id}`}>{name}</Link>
                    </h2>
                    <p className="field-hint">
                      {t("cart.unitPrice")}: {formatMoney(item.unit_price, locale)}{" "}
                      {cart.currency}
                      {" · "}
                      {item.available > 0
                        ? t("cart.available", { count: item.available })
                        : t("cart.unavailable")}
                    </p>
                    <QuantityControl
                      productId={item.product_id}
                      quantity={item.quantity}
                      available={Math.max(1, item.available)}
                      locale={locale}
                    />
                  </div>

                  <div className="line-total">
                    <p className="price-amount">
                      {formatMoney(multiplyMoney(item.unit_price, item.quantity), locale)}{" "}
                      {cart.currency}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>

          <aside className="summary-aside">
            <div className="panel">
              <h2>{t("cart.summary")}</h2>
              <div className="totals">
                <div>
                  <span>{t("cart.subtotal")}</span>
                  <span>
                    {formatMoney(cart.subtotal, locale)} {cart.currency}
                  </span>
                </div>
                <div className="grand">
                  <span>{t("checkout.total")}</span>
                  <span>
                    {formatMoney(cart.subtotal, locale)} {cart.currency}
                  </span>
                </div>
              </div>
              <Link
                className="btn btn-primary btn-block stack-4"
                href="/checkout"
              >
                {t("cart.checkout")}
              </Link>
              <p className="field-hint stack-3">
                {t("cart.priceRecheck")}
              </p>
            </div>
          </aside>
        </div>
      </main>
    );
  } catch (error) {
    return (
      <main className="page page-narrow" id="main">
        <ErrorState
          locale={locale}
          title={t("cart.updateError")}
          hint={t("listing.loadErrorHint")}
          onRetryHref="/cart"
        />
        {error instanceof ApiError && error.requestId ? (
          <Notice tone="info">request_id: {error.requestId}</Notice>
        ) : null}
      </main>
    );
  }
}