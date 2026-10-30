import type { Metadata } from "next";
import Link from "next/link";
import type { Locale } from "@/lib/types";
import { api } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { statusLabel, translator } from "@/lib/i18n";
import { formatDateTime, formatMoney } from "@/lib/format";
import { requireCustomer } from "@/lib/session";
import { EmptyState, Notice } from "@/components/states";

export const metadata: Metadata = { title: "طلباتي — Smart-eCommerce" };

const PAGE_SIZE = 20;

export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const locale: Locale = await getLocale();
  const t = translator(locale);
  await requireCustomer("/account/orders");

  const params = await searchParams;
  const rawPage = Array.isArray(params.page) ? params.page[0] : params.page;
  const page = Math.max(1, Number.parseInt(rawPage ?? "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  let orders;
  try {
    orders = await api.orders({ limit: PAGE_SIZE, offset });
  } catch {
    return (
      <main className="page page-narrow" id="main">
        <div className="page-head">
          <div>
            <p className="eyebrow">{t("orders.title")}</p>
            <h1>{t("orders.title")}</h1>
            <p>{t("orders.intro")}</p>
          </div>
        </div>
        <div style={{ marginBlockStart: 18 }}>
          <Notice tone="error">{t("account.failed")}</Notice>
        </div>
      </main>
    );
  }

  const pages = Math.max(1, Math.ceil(orders.total / PAGE_SIZE));

  return (
    <main className="page page-narrow" id="main">
      <div className="page-head">
        <div>
          <p className="eyebrow">{t("nav.account")}</p>
          <h1>{t("orders.title")}</h1>
          <p>{t("orders.intro")}</p>
        </div>
        <span className="pill">{t("orders.count", { count: orders.total })}</span>
      </div>

      <div style={{ marginBlockStart: 18 }}>
        {orders.items.length === 0 ? (
          <EmptyState title={t("orders.empty")} hint={t("account.emptyOrders")}>
            <Link className="btn btn-primary" href="/">
              {t("cart.browse")}
            </Link>
          </EmptyState>
        ) : (
          <ul className="order-list">
            {orders.items.map((order) => (
              <li className="order-row" key={order.order_id}>
                <div className="order-row-id">
                  <code dir="ltr" title={order.order_id}>
                    {order.order_id.slice(-12)}
                  </code>
                  <p>
                    {t("orders.itemCount", { count: order.item_count })}
                    {" · "}
                    <time dateTime={order.created_at}>
                      {formatDateTime(order.created_at, locale)}
                    </time>
                  </p>
                </div>
                <div className="order-row-meta">
                  <span className="pill" data-status={order.status}>
                    {statusLabel(t, order.status)}
                  </span>
                  <span className="price-amount">
                    {formatMoney(order.subtotal, locale)} {order.currency}
                  </span>
                  <Link className="btn btn-sm" href={`/orders/${order.order_id}`}>
                    {t("orders.view")}
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}

        {pages > 1 ? (
          <nav className="pager" aria-label={t("orders.title")}>
            {page > 1 ? (
              <Link className="btn btn-quiet" href={`/account/orders?page=${page - 1}`}>
                {t("orders.previous")}
              </Link>
            ) : (
              <span />
            )}
            <span className="field-hint">{t("orders.page", { page, pages })}</span>
            {page < pages ? (
              <Link className="btn btn-quiet" href={`/account/orders?page=${page + 1}`}>
                {t("orders.next")}
              </Link>
            ) : (
              <span />
            )}
          </nav>
        ) : null}
      </div>
    </main>
  );
}
