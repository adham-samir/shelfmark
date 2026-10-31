import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, sumMoney } from "@/lib/format";
import { shipmentStatusLabel, statusLabel, translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { Locale, OperatorOrderDetail } from "@/lib/types";
import { ErrorState } from "@/components/states";
import {
  OrderCancelControl,
  OrderRefundControl,
  ShipmentTransitionControl,
} from "@/components/order-lifecycle-controls";

export const metadata: Metadata = {
  title: "Order detail — Smart-eCommerce",
  description: "Operator view of a customer order, shipping, and shipment.",
};

export default async function BackofficeOrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const locale: Locale = await getLocale();
  const t = translator(locale);

  let order: OperatorOrderDetail;
  try {
    order = await api.operatorOrder(id);
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_found") notFound();
    return (
      <main className="page page-narrow" id="main">
        <ErrorState
          locale={locale}
          title={t("adminOrders.loadFailed")}
          hint={
            error instanceof ApiError
              ? `${t("adminOrders.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
              : t("adminOrders.loadFailedHint")
          }
          onRetryHref={`/backoffice/orders/${id}`}
        />
      </main>
    );
  }

  const net =
    order.refund_total === "0"
      ? order.subtotal
      : sumMoney([order.subtotal, `-${order.refund_total}`]);
  const shippedEvents = order.shipment ? [...order.shipment.events].reverse() : [];
  const cancellable =
    order.status === "review" ||
    order.status === "pending_payment" ||
    order.status === "pending_risk" ||
    order.status === "confirmed";
  const refundable =
    order.status === "confirmed" ||
    order.status === "shipped" ||
    order.status === "delivered";

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("adminOrders.detailEyebrow")}</p>
          <h1>{t("adminOrders.detailTitle")}</h1>
          <p>{t("adminOrders.detailIntro")}</p>
          <p className="field-hint" style={{ marginBlockStart: 6 }} dir="ltr">
            {order.order_id}
          </p>
        </div>
        <span className="pill" data-status={order.status}>
          {statusLabel(t, order.status)}
        </span>
      </div>

      <div className="row-actions" style={{ marginBlock: 14 }}>
        <Link className="btn btn-quiet" href="/backoffice/orders">
          {t("adminOrders.back")}
        </Link>
        {order.status === "review" ? (
          <Link className="btn" href="/backoffice/risk">
            {t("adminOrders.openRisk")}
          </Link>
        ) : null}
      </div>

      <div className="split">
        <section className="panel" aria-labelledby="operator-customer">
          <h2 id="operator-customer">{t("adminOrders.contact")}</h2>
          <dl className="detail-specs">
            <div>
              <dt>{t("adminOrders.name")}</dt>
              <dd>{order.customer.display_name}</dd>
            </div>
            <div>
              <dt>{t("adminOrders.email")}</dt>
              <dd dir="ltr">{order.customer.email}</dd>
            </div>
            <div>
              <dt>{t("adminOrders.created")}</dt>
              <dd>{formatDateTime(order.created_at, locale)}</dd>
            </div>
            <div>
              <dt>{t("adminOrders.completed")}</dt>
              <dd>
                {order.completed_at
                  ? formatDateTime(order.completed_at, locale)
                  : t("adminOrders.notCompleted")}
              </dd>
            </div>
          </dl>

          <h2 style={{ marginBlockStart: 22 }}>{t("adminOrders.shipping")}</h2>
          {order.shipping ? (
            <dl className="detail-specs">
              <div>
                <dt>{t("adminOrders.name")}</dt>
                <dd>{order.shipping.recipient_name ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("adminOrders.phone")}</dt>
                <dd dir="ltr">{order.shipping.phone ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("adminOrders.city")}</dt>
                <dd>{order.shipping.city ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("adminOrders.address")}</dt>
                <dd>{order.shipping.address_line ?? "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="field-hint">{t("adminOrders.noShipping")}</p>
          )}
        </section>

        <section className="panel" aria-labelledby="operator-items">
          <h2 id="operator-items">{t("order.items")}</h2>
          <ul className="summary-lines">
            {order.items.map((item) => (
              <li key={item.product_id}>
                <span>
                  <Link href={`/products/${item.product_id}`}>{item.product_name}</Link> ×{" "}
                  {item.quantity}
                </span>
                <span className="price-amount">
                  {formatMoney(item.line_total, locale)} {order.currency}
                </span>
              </li>
            ))}
          </ul>
          <div className="totals" style={{ marginBlockStart: 12 }}>
            <div className="grand">
              <span>{t("adminOrders.subtotal")}</span>
              <span>
                {formatMoney(order.subtotal, locale)} {order.currency}
              </span>
            </div>
            {order.refund_total !== "0" ? (
              <>
                <div>
                  <span>{t("adminOrders.refund")}</span>
                  <span>
                    {formatMoney(order.refund_total, locale)} {order.currency}
                  </span>
                </div>
                <div className="grand">
                  <span>{t("adminOrders.net")}</span>
                  <span>
                    {formatMoney(net, locale)} {order.currency}
                  </span>
                </div>
              </>
            ) : null}
          </div>
        </section>
      </div>

      <section className="panel" aria-labelledby="operator-shipment" style={{ marginBlockStart: 18 }}>
        <h2 id="operator-shipment">{t("adminOrders.shipment")}</h2>
        {order.shipment ? (
          <>
            <p className="pill" data-status={order.shipment.status}>
              {shipmentStatusLabel(t, order.shipment.status)}
            </p>
            <ol className="timeline">
              {shippedEvents.map((event, index) => (
                <li
                  key={`${event.status}-${event.occurred_at}-${index}`}
                  data-status={event.status}
                >
                  <span className="dot" aria-hidden="true" />
                  <div>
                    <h3>{locale === "ar" ? event.description_ar : event.description_en}</h3>
                    <p>{shipmentStatusLabel(t, event.status)}</p>
                    <time dateTime={event.occurred_at}>
                      {formatDateTime(event.occurred_at, locale)}
                    </time>
                  </div>
                </li>
              ))}
            </ol>
          </>
        ) : (
          <p className="field-hint">{t("adminOrders.noShipment")}</p>
        )}
      </section>

      <section
        className="panel"
        aria-labelledby="operator-adjustments"
        style={{ marginBlockStart: 18 }}
      >
        <h2 id="operator-adjustments">{t("adminOrders.adjustments")}</h2>
        {order.adjustments.length === 0 ? (
          <p className="field-hint">{t("adminOrders.noAdjustments")}</p>
        ) : (
          <div
            className="inventory-table-wrap"
            // A scrollable region needs to be reachable by keyboard, or its
            // overflow is invisible to anyone not using a mouse.
            tabIndex={0}
            role="region"
            aria-label={t("adminOrders.adjustments")}
          >
            <table className="inventory-table adjustments-table">
              <thead>
                <tr>
                  <th scope="col">{t("adminOrders.adjustmentKind")}</th>
                  <th scope="col">{t("adminOrders.adjustmentAmount")}</th>
                  <th scope="col">{t("adminOrders.adjustmentReason")}</th>
                  <th scope="col">{t("adminOrders.adjustmentActor")}</th>
                  <th scope="col">{t("adminOrders.adjustmentTime")}</th>
                </tr>
              </thead>
              <tbody>
                {order.adjustments.map((adjustment) => (
                  <tr key={adjustment.adjustment_id}>
                    <th scope="row">
                      {adjustment.kind === "refund"
                        ? t("orderLifecycle.refund")
                        : t("orderLifecycle.cancel")}
                    </th>
                    <td data-label={t("adminOrders.adjustmentAmount")}>
                      <span className="metric-value" dir="ltr">
                        {formatMoney(adjustment.amount, locale)} {order.currency}
                      </span>
                    </td>
                    <td data-label={t("adminOrders.adjustmentReason")}>
                      {adjustment.reason}
                    </td>
                    <td data-label={t("adminOrders.adjustmentActor")}>
                      <span>
                        {adjustment.actor_kind === "customer"
                          ? t("adminOrders.actorCustomer")
                          : t("adminOrders.actorOperator")}
                      </span>
                      <small>{adjustment.actor_name}</small>
                    </td>
                    <td data-label={t("adminOrders.adjustmentTime")}>
                      {formatDateTime(adjustment.created_at, locale)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        className="panel"
        aria-labelledby="operator-lifecycle"
        style={{ marginBlockStart: 18 }}
      >
        <h2 id="operator-lifecycle">{t("orderLifecycle.section")}</h2>
        <p className="field-hint">{t("orderLifecycle.hint")}</p>

        {order.shipment ? (
          <ShipmentTransitionControl
            locale={locale}
            orderId={order.order_id}
            status={order.shipment.status}
          />
        ) : null}

        <div className="row-actions" style={{ marginBlockStart: 12 }}>
          {cancellable ? (
            <OrderCancelControl locale={locale} orderId={order.order_id} />
          ) : null}
          {refundable ? (
            <OrderRefundControl
              locale={locale}
              orderId={order.order_id}
              remaining={net}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
