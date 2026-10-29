import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { Locale, Order, Shipment } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { getOrder } from "@/lib/data";
import { getLocale } from "@/lib/locale";
import { statusLabel, translator } from "@/lib/i18n";
import { formatDateTime, formatMoney } from "@/lib/format";
import { ErrorState, Notice } from "@/components/states";
import { requireCustomer } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  try {
    await getOrder(id);
    return { title: "الطلب — Smart-eCommerce" };
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") notFound();
    return { title: "الطلب — Smart-eCommerce" };
  }
}

export default async function OrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const locale: Locale = await getLocale();
  const t = translator(locale);
  await requireCustomer(`/orders/${id}`);

  let order: Order;
  try {
    order = await getOrder(id);
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") notFound();
    return (
      <main className="page page-narrow" id="main">
        <ErrorState
          locale={locale}
          title={t("order.unavailable")}
          hint={t("listing.loadErrorHint")}
          onRetryHref={`/orders/${id}`}
        />
      </main>
    );
  }

  let shipment: Shipment | null = null;
  try {
    shipment = await api.shipment(order.order_id);
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== "not_found") {
      shipment = null;
    }
  }

  const events = shipment ? [...shipment.events].reverse() : [];

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("order.title")}</p>
          <h1>{t("order.title")}</h1>
          <p>{t("order.intro")}</p>
          <p className="field-hint" style={{ marginBlockStart: 6 }}>
            <span dir="ltr">{order.order_id}</span>
          </p>
        </div>
        <span className="pill" data-status={order.status}>
          {statusLabel(t, order.status)}
        </span>
      </div>

      {order.status === "review" ? <Notice tone="warn">{t("checkout.orderReview")}</Notice> : null}
      {order.status === "pending_risk" ? <Notice tone="info">{t("checkout.orderPending")}</Notice> : null}
      {order.status === "payment_failed" ? <Notice tone="error">{t("checkout.orderFailed")}</Notice> : null}
      {order.status === "cancelled" ? <Notice tone="error">{t("checkout.orderCancelled")}</Notice> : null}

      <div className="split" style={{ marginBlockStart: 18 }}>
        <section className="panel" aria-labelledby="order-items">
          <h2 id="order-items">{t("order.items")}</h2>
          <ul className="summary-lines">
            {order.items.map((item) => (
              <li key={item.product_id}>
                <span>
                  <Link href={`/products/${item.product_id}`}>{item.product_name}</Link> × {item.quantity}
                </span>
                <span className="price-amount">
                  {formatMoney(item.line_total, locale)} {order.currency}
                </span>
              </li>
            ))}
          </ul>
          <div className="totals" style={{ marginBlockStart: 12 }}>
            <div>
              <span>{t("order.created")}</span>
              <span>{formatDateTime(order.created_at, locale)}</span>
            </div>
            <div className="grand">
              <span>{t("order.subtotal")}</span>
              <span>
                {formatMoney(order.subtotal, locale)} {order.currency}
              </span>
            </div>
          </div>
        </section>

        <section className="panel" aria-labelledby="order-shipment">
          <h2 id="order-shipment">{t("order.shipment")}</h2>
          {shipment ? (
            <>
              <p className="pill" data-status={order.status}>
                {shipment.status}
              </p>
              <ol className="timeline">
                {events.map((event, index) => (
                  <li key={`${event.status}-${index}`} data-status={event.status}>
                    <span className="dot" aria-hidden="true" />
                    <div>
                      <h3>{locale === "ar" ? event.description_ar : event.description_en}</h3>
                      <p>{event.status}</p>
                      <time dateTime={event.occurred_at}>
                        {formatDateTime(event.occurred_at, locale)}
                      </time>
                    </div>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <div>
              <p style={{ fontWeight: 500 }}>{t("order.shipmentUnavailable")}</p>
              <p className="field-hint">{t("order.shipmentUnavailableHint")}</p>
            </div>
          )}
        </section>
      </div>

      <div style={{ marginBlockStart: 18, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link className="btn" href="/">
          {t("cart.browse")}
        </Link>
        <Link className="btn btn-quiet" href="/cart">
          {t("order.backToCart")}
        </Link>
      </div>
    </main>
  );
}