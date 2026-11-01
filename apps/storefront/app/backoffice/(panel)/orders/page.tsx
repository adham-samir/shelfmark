import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import { statusLabel, translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { Locale, OperatorOrderList, OrderState } from "@/lib/types";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Store orders",
  description:
    "Read-only operator view of every customer order with status and customer context.",
};

const PAGE_SIZE = 20;

const STATUSES: OrderState[] = [
  "review",
  "confirmed",
  "shipped",
  "delivered",
  "cancelled",
  "refunded",
  "payment_failed",
  "pending_payment",
  "pending_risk",
];

function isStatus(value: string): value is OrderState {
  return (STATUSES as string[]).includes(value);
}

export default async function BackofficeOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string | string[]; page?: string | string[] }>;
}) {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  const params = await searchParams;
  const rawStatus = Array.isArray(params.status) ? params.status[0] : params.status;
  const status = rawStatus && isStatus(rawStatus) ? rawStatus : undefined;
  const rawPage = Array.isArray(params.page) ? params.page[0] : params.page;
  const page = Math.max(1, Number.parseInt(rawPage ?? "1", 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  let orders: OperatorOrderList;
  try {
    orders = await api.operatorOrders({
      status,
      limit: PAGE_SIZE,
      offset,
    });
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("adminOrders.unauthorized")
        : permissionCode === "forbidden"
          ? t("adminOrders.forbidden")
          : t("adminOrders.loadFailed");
    const errorHint =
      permissionCode === "unauthorized" || permissionCode === "forbidden"
        ? t("adminOrders.loadFailedHint")
        : error instanceof ApiError
          ? `${t("adminOrders.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
          : t("adminOrders.loadFailedHint");
    return (
      <main className="page inventory-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("adminOrders.title")}</h1>
            <p>{t("adminOrders.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref={status ? `/backoffice/orders?status=${status}` : "/backoffice/orders"}
        />
      </main>
    );
  }

  const pages = Math.max(1, Math.ceil(orders.total / PAGE_SIZE));
  const query = (targetPage: number): string => {
    const search = new URLSearchParams();
    if (status) search.set("status", status);
    if (targetPage > 1) search.set("page", String(targetPage));
    const suffix = search.toString();
    return suffix ? `/backoffice/orders?${suffix}` : "/backoffice/orders";
  };

  return (
    <main className="page inventory-page" id="main">
      <header className="page-head">
        <div>
          <h1>{t("adminOrders.title")}</h1>
          <p>{t("adminOrders.intro")}</p>
        </div>
        <span className="pill">{t("adminOrders.count", { count: orders.total })}</span>
      </header>

      <form className="orders-filter" method="get" action="/backoffice/orders">
        <label className="field-label" htmlFor="order-status">
          {t("adminOrders.filterLabel")}
        </label>
        <select className="input" id="order-status" name="status" defaultValue={status ?? ""}>
          <option value="">{t("adminOrders.filterAll")}</option>
          {STATUSES.map((value) => (
            <option value={value} key={value}>
              {statusLabel(t, value)}
            </option>
          ))}
        </select>
        <button className="btn" type="submit">
          {t("adminOrders.apply")}
        </button>
      </form>

      {orders.items.length === 0 ? (
        <EmptyState
          title={t("adminOrders.empty")}
          hint={t("adminOrders.emptyHint")}
        />
      ) : (
        <section className="inventory-sheet" aria-labelledby="orders-table-title">
          <div className="inventory-sheet-head">
            <h2 id="orders-table-title">{t("adminOrders.title")}</h2>
            <span>
              {t("adminOrders.page", { page, pages })}
            </span>
          </div>
          <div className="inventory-table-wrap" tabIndex={0}>
            <table className="inventory-table orders-table">
              <thead>
                <tr>
                  <th scope="col">{t("adminOrders.order")}</th>
                  <th scope="col">{t("adminOrders.customer")}</th>
                  <th scope="col">{t("adminOrders.status")}</th>
                  <th scope="col">{t("adminOrders.items")}</th>
                  <th scope="col">{t("adminOrders.subtotal")}</th>
                  <th scope="col">{t("adminOrders.created")}</th>
                  <th scope="col">
                    <span className="visually-hidden">{t("adminOrders.view")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {orders.items.map((order) => (
                  <tr key={order.order_id}>
                    <th scope="row">
                      <code dir="ltr">{order.order_id.slice(-12)}</code>
                    </th>
                    <td data-label={t("adminOrders.customer")}>
                      <span>{order.customer.display_name}</span>
                      <small dir="ltr">{order.customer.email}</small>
                    </td>
                    <td data-label={t("adminOrders.status")}>
                      <span className="pill" data-status={order.status}>
                        {statusLabel(t, order.status)}
                      </span>
                    </td>
                    <td data-label={t("adminOrders.items")}>{order.item_count}</td>
                    <td data-label={t("adminOrders.subtotal")}>
                      <span className="metric-value" dir="ltr">
                        {formatMoney(order.subtotal, locale)} {order.currency}
                      </span>
                    </td>
                    <td data-label={t("adminOrders.created")}>
                      {formatDateTime(order.created_at, locale)}
                    </td>
                    <td>
                      <Link
                        className="btn btn-quiet"
                        href={`/backoffice/orders/${order.order_id}`}
                      >
                        {t("adminOrders.view")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {pages > 1 ? (
        <nav className="pager" aria-label={t("adminOrders.title")}>
          {page > 1 ? (
            <Link className="btn btn-quiet" href={query(page - 1)}>
              {t("adminOrders.previous")}
            </Link>
          ) : (
            <span />
          )}
          <span className="field-hint">
            {t("adminOrders.page", { page, pages })}
          </span>
          {page < pages ? (
            <Link className="btn btn-quiet" href={query(page + 1)}>
              {t("adminOrders.next")}
            </Link>
          ) : (
            <span />
          )}
        </nav>
      ) : null}
    </main>
  );
}
