import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/lib/format";
import { categoryLabel, translator, type MessageKey } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { AnalyticsResponse, Locale } from "@/lib/types";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Analytics",
  description:
    "BI-01 consumer-behaviour and financial dashboards with date/category filters and source reconciliation.",
};

const CATEGORIES = ["phones", "headphones", "laptops"] as const;
const DAY_MS = 24 * 60 * 60 * 1000;

function isoDay(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function defaultRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to.getTime() - 89 * DAY_MS);
  return { from: isoDay(from), to: isoDay(to) };
}

function isValidDay(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function percentOfMax(value: number, max: number): number {
  if (max <= 0) return 0;
  return Math.max(2, Math.round((value / max) * 100));
}

function metricLabel(metric: string) {
  if (metric === "order_totals") return "analytics.orderTotals" as const;
  if (metric === "gross_sales") return "analytics.gross" as const;
  return "analytics.orderCount" as const;
}

export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const fallback = defaultRange();
  const from = isValidDay(params.from) ? params.from : fallback.from;
  const to = isValidDay(params.to) ? params.to : fallback.to;
  const category =
    typeof params.category === "string" && params.category.trim()
      ? params.category.trim()
      : undefined;

  let report: AnalyticsResponse;
  try {
    report = await api.analytics({ from, to, category });
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("analytics.unauthorized")
        : permissionCode === "forbidden"
          ? t("analytics.forbidden")
          : t("analytics.loadFailed");
    const errorHint =
      permissionCode === "unauthorized"
        ? t("analytics.unauthorizedHint")
        : permissionCode === "forbidden"
          ? t("analytics.forbiddenHint")
          : error instanceof ApiError
            ? `${t("analytics.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
            : t("analytics.loadFailedHint");
    return (
      <main className="page inventory-page analytics-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("analytics.title")}</h1>
            <p>{t("analytics.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref="/backoffice/analytics"
        />
      </main>
    );
  }

  const names = new Map<string, string>();
  try {
    const catalog = await api.products({ limit: 100 });
    for (const product of catalog.items) names.set(product.product_id, product.name);
  } catch {
    // Product identifiers remain an honest fallback when the catalog is down.
  }

  const peak = report.daily.reduce(
    (max, point) => Math.max(max, point.views),
    0,
  );
  const mismatches = report.reconciliation.filter((check) => !check.matches);
  const money = (value: string) => formatMoney(value, locale);
  // Revenue is an aggregate of exact decimal line totals and can carry six
  // decimal places; operators read money at two, so the ledger rounds for
  // display only.
  const revenue = (value: string) => money(Number(value).toFixed(2));
  const unfilteredHref = `/backoffice/analytics?from=${from}&to=${to}`;

  return (
    <main className="page inventory-page analytics-page" id="main">
      <header className="inventory-command">
        <div>
          <h1>{t("analytics.title")}</h1>
          <p>{t("analytics.intro")}</p>
          <div className="inventory-command-meta">
            <span>{t("analytics.operator")}</span>
            <span>
              {t("analytics.range", {
                from: formatDate(report.scope.date_from, locale),
                to: formatDate(report.scope.date_to, locale),
              })}
            </span>
            {report.scope.category ? (
              <span>{categoryLabel(t, report.scope.category)}</span>
            ) : null}
            <span>
              {t("analytics.generated", {
                time: formatDateTime(report.generated_at, locale),
              })}
            </span>
          </div>
        </div>
        <form className="analytics-filters" method="get" action="/backoffice/analytics">
          <label>
            <span>{t("analytics.from")}</span>
            <input type="date" name="from" defaultValue={report.scope.date_from} />
          </label>
          <label>
            <span>{t("analytics.to")}</span>
            <input type="date" name="to" defaultValue={report.scope.date_to} />
          </label>
          <label>
            <span>{t("analytics.category")}</span>
            <select name="category" defaultValue={report.scope.category ?? ""}>
              <option value="">{t("analytics.allCategories")}</option>
              {CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {categoryLabel(t, value)}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit">
            {t("analytics.apply")}
          </button>
        </form>
      </header>

      {report.category_without_products ? (
        <EmptyState
          title={t("analytics.noProducts")}
          hint={t("analytics.noProductsHint")}
        >
          <Link className="btn" href={unfilteredHref}>
            {t("analytics.allCategories")}
          </Link>
        </EmptyState>
      ) : (
        <>
          <section
            className="analytics-grid"
            aria-label={t("analytics.consumer")}
          >
            <article className="analytics-panel">
              <h2>{t("analytics.consumer")}</h2>
              <dl className="analytics-kpis">
                <div>
                  <dt>{t("analytics.views")}</dt>
                  <dd>{formatNumber(report.behaviour.product_views, locale)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.sessions")}</dt>
                  <dd>{formatNumber(report.behaviour.sessions, locale)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.carts")}</dt>
                  <dd>{formatNumber(report.behaviour.add_to_carts, locale)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.orders")}</dt>
                  <dd>{formatNumber(report.behaviour.created_orders, locale)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.conversion")}</dt>
                  <dd dir="ltr">{report.behaviour.orders_per_session}</dd>
                </div>
                <div>
                  <dt>{t("analytics.unfulfilled")}</dt>
                  <dd>{formatNumber(report.behaviour.unfulfilled_orders, locale)}</dd>
                </div>
              </dl>
              {report.no_events ? (
                <p className="analytics-note" data-tone="warn">
                  {t("analytics.noEvents")} — {t("analytics.noEventsHint")}
                </p>
              ) : null}
            </article>

            <article className="analytics-panel">
              <h2>{t("analytics.financial")}</h2>
              <dl className="analytics-kpis">
                <div>
                  <dt>{t("analytics.orderCount")}</dt>
                  <dd>{formatNumber(report.financial.order_count, locale)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.gross")}</dt>
                  <dd dir="ltr">{money(report.financial.gross_sales)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.refunds")}</dt>
                  <dd dir="ltr">{money(report.financial.refunds)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.net")}</dt>
                  <dd dir="ltr">{money(report.financial.net_sales)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.aov")}</dt>
                  <dd dir="ltr">{money(report.financial.average_order_value)}</dd>
                </div>
                <div>
                  <dt>{t("analytics.metric")}</dt>
                  <dd dir="ltr">{report.financial.currency}</dd>
                </div>
              </dl>
              {report.no_orders ? (
                <p className="analytics-note" data-tone="warn">
                  {t("analytics.noOrders")} — {t("analytics.noOrdersHint")}
                </p>
              ) : null}
              <p className="analytics-note">{t("analytics.profit")}</p>
            </article>
          </section>

          <section className="analytics-panel" aria-labelledby="analytics-trend">
            <h2 id="analytics-trend">{t("analytics.trend")}</h2>
            <p className="analytics-sub">{t("analytics.trendHint")}</p>
            <div className="analytics-legend">
              <span data-kind="views">{t("analytics.views")}</span>
              <span data-kind="orders">{t("analytics.orders")}</span>
            </div>
            <ol className="analytics-trend" aria-label={t("analytics.trend")}>
              {report.daily.map((point, index) => (
                <li key={point.day} title={`${point.day} · ${point.views}`}>
                  <span
                    className="analytics-bar"
                    style={
                      {
                        height: `${percentOfMax(point.views, peak)}%`,
                        "--i": Math.min(index, 24),
                      } as React.CSSProperties
                    }
                    data-orders={point.orders > 0 ? "true" : "false"}
                  />
                  <span className="visually-hidden">
                    {point.day}: {point.views} · {point.orders} ·{" "}
                    {money(point.net_sales)}
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <div className="analytics-split">
            <section className="inventory-sheet" aria-labelledby="analytics-top">
              <div className="inventory-sheet-head">
                <h2 id="analytics-top">{t("analytics.topProducts")}</h2>
                <span>{formatNumber(report.top_products.length, locale)}</span>
              </div>
              {report.top_products.length === 0 ? (
                <EmptyState title={t("analytics.noEvents")} />
              ) : (
                <div className="inventory-table-wrap" tabIndex={0}>
                  <table className="inventory-table analytics-table">
                    <thead>
                      <tr>
                        <th>{t("analytics.product")}</th>
                        <th>{t("analytics.views")}</th>
                        <th>{t("analytics.carts")}</th>
                        <th>{t("analytics.units")}</th>
                        <th>{t("analytics.revenue")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.top_products.map((item) => (
                        <tr key={item.product_id}>
                          <th scope="row">
                            <Link href={`/products/${item.product_id}`}>
                              {names.get(item.product_id) ?? item.product_id}
                            </Link>
                            <code dir="ltr">{item.product_id.slice(-12)}</code>
                          </th>
                          <td data-label={t("analytics.views")}>
                            {formatNumber(item.views, locale)}
                          </td>
                          <td data-label={t("analytics.carts")}>
                            {formatNumber(item.add_to_carts, locale)}
                          </td>
                          <td data-label={t("analytics.units")}>
                            {formatNumber(item.units, locale)}
                          </td>
                          <td data-label={t("analytics.revenue")} dir="ltr">
                            {revenue(item.revenue)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <aside className="analytics-side">
              <section className="analytics-panel">
                <h2>{t("analytics.reconciliation")}</h2>
                <table className="analytics-recon">
                  <thead>
                    <tr>
                      <th>{t("analytics.metric")}</th>
                      <th>{t("analytics.reported")}</th>
                      <th>{t("analytics.recomputed")}</th>
                      <th>{t("analytics.matches")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.reconciliation.map((check) => (
                      <tr key={check.metric}>
                        <th scope="row">{t(metricLabel(check.metric))}</th>
                        <td dir="ltr">{money(check.reported)}</td>
                        <td dir="ltr">{money(check.recomputed)}</td>
                        <td>
                          <span
                            className="status-chip"
                            data-status={check.matches ? "fresh" : "missing"}
                          >
                            {check.matches
                              ? t("analytics.matches")
                              : t("analytics.mismatch")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {mismatches.length > 0 ? (
                  <p className="analytics-note" data-tone="error">
                    {t("analytics.mismatch")}: {mismatches.length}
                  </p>
                ) : null}
              </section>

              <section className="analytics-panel">
                <h2>{t("analytics.definitions")}</h2>
                <ol className="segments-rules analytics-definitions">
                  {report.definitions.map((definition, index) => (
                    <li key={definition}>
                      <span>{t(`analytics.def${index + 1}` as MessageKey)}</span>
                    </li>
                  ))}
                </ol>
                <p className="analytics-note">{t("analytics.synthetic")}</p>
              </section>
            </aside>
          </div>
        </>
      )}
    </main>
  );
}