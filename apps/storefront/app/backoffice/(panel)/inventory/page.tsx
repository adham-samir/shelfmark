import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatNumber } from "@/lib/format";
import { translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { InventoryPlanningItem, Locale } from "@/lib/types";
import { InventoryRunControl } from "@/components/inventory-run-control";
import { InventoryAdjustControl } from "@/components/inventory-adjust-control";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Inventory planning — Smart-eCommerce",
  description: "Synthetic BO-01 demand forecasting and automatic reorder operations.",
};

function statusKey(item: InventoryPlanningItem) {
  switch (item.planning_status) {
    case "reorder_pending":
      return "inventory.reorderPending" as const;
    case "supplier_failed":
      return "inventory.supplierFailed" as const;
    case "planned":
      return "inventory.planned" as const;
    default:
      return "inventory.forecastMissing" as const;
  }
}

export default async function InventoryPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  let planning;
  try {
    planning = await api.inventory();
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("inventory.unauthorized")
        : permissionCode === "forbidden"
          ? t("inventory.forbidden")
          : t("inventory.loadFailed");
    const errorHint =
      permissionCode === "unauthorized"
        ? t("inventory.unauthorizedHint")
        : permissionCode === "forbidden"
          ? t("inventory.forbiddenHint")
          : error instanceof ApiError
            ? `${t("inventory.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
            : t("inventory.loadFailedHint");
    return (
      <main className="page inventory-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("inventory.title")}</h1>
            <p>{t("inventory.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref="/backoffice/inventory"
        />
      </main>
    );
  }

  const names = new Map<string, string>();
  try {
    const products = await api.products({ limit: 100 });
    for (const product of products.items) names.set(product.product_id, product.name);
  } catch {
    // Product IDs remain an honest fallback when the descriptive catalog is unavailable.
  }

  const forecasted = planning.items.filter((item) => item.forecast).length;
  const pending = planning.items.filter((item) => item.pending_replenishment > 0).length;
  const attention = planning.items.filter(
    (item) => item.planning_status === "supplier_failed" || !item.forecast,
  ).length;

  return (
    <main className="page inventory-page" id="main">
      <header className="inventory-command">
        <div>
          <h1>{t("inventory.title")}</h1>
          <p>{t("inventory.intro")}</p>
          <div className="inventory-command-meta">
            <span>{t("inventory.operator")}</span>
            <time dateTime={planning.generated_at}>
              {t("inventory.updated", {
                time: formatDateTime(planning.generated_at, locale),
              })}
            </time>
          </div>
        </div>
        <InventoryRunControl locale={locale} />
      </header>

      <section className="inventory-ledger" aria-label={t("inventory.status")}>
        {[
          [t("inventory.products"), planning.items.length],
          [t("inventory.forecasted"), forecasted],
          [t("inventory.pending"), pending],
          [t("inventory.attention"), attention],
        ].map(([label, value]) => (
          <div key={String(label)}>
            <strong>{formatNumber(Number(value), locale)}</strong>
            <span>{label}</span>
          </div>
        ))}
      </section>

      <div className="inventory-layout">
        <section className="inventory-sheet" aria-labelledby="inventory-table-title">
          <div className="inventory-sheet-head">
            <h2 id="inventory-table-title">{t("inventory.product")}</h2>
            <span>{planning.policy.version}</span>
          </div>
          {planning.items.length === 0 ? (
            <EmptyState title={t("inventory.empty")} />
          ) : (
            <div className="inventory-table-wrap">
              <table className="inventory-table">
                <thead>
                  <tr>
                    <th>{t("inventory.product")}</th>
                    <th>{t("inventory.stock")}</th>
                    <th>{t("inventory.forecast")}</th>
                    <th>{t("inventory.threshold")}</th>
                    <th>{t("inventory.replenishment")}</th>
                    <th>{t("inventory.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {planning.items.map((item) => {
                    const name = names.get(item.product_id);
                    return (
                      <tr key={item.product_id} data-status={item.planning_status}>
                        <th scope="row">
                          {name ? (
                            <Link href={`/products/${item.product_id}`}>{name}</Link>
                          ) : (
                            <span>{item.product_id}</span>
                          )}
                          <code dir="ltr">{item.product_id.slice(-12)}</code>
                        </th>
                        <td data-label={t("inventory.stock")}>
                          <dl className="stock-stack">
                            <div>
                              <dt>{t("inventory.onHand")}</dt>
                              <dd>{formatNumber(item.on_hand, locale)}</dd>
                            </div>
                            <div>
                              <dt>{t("inventory.reserved")}</dt>
                              <dd>{formatNumber(item.reserved, locale)}</dd>
                            </div>
                            <div>
                              <dt>{t("inventory.available")}</dt>
                              <dd>{formatNumber(item.available, locale)}</dd>
                            </div>
                          </dl>
                        </td>
                        <td data-label={t("inventory.forecast")}>
                          {item.forecast ? (
                            <div className="forecast-cell">
                              <strong>
                                {t("inventory.units", {
                                  count: formatNumber(Number(item.forecast.predicted_quantity), locale),
                                })}
                              </strong>
                              <span>
                                {t("inventory.horizon", {
                                  from: formatDate(item.forecast.horizon_start, locale),
                                  to: formatDate(item.forecast.horizon_end, locale),
                                })}
                              </span>
                              <small>{t("inventory.model", { model: item.forecast.model_version })}</small>
                            </div>
                          ) : (
                            <span className="missing-data">{t("inventory.noForecast")}</span>
                          )}
                        </td>
                        <td className="number-cell" data-label={t("inventory.threshold")}>
                          {item.reorder_point == null ? "—" : formatNumber(item.reorder_point, locale)}
                          {item.target_stock == null ? null : (
                            <small>
                              {t("inventory.target")}: {formatNumber(item.target_stock, locale)}
                            </small>
                          )}
                        </td>
                        <td className="number-cell" data-label={t("inventory.replenishment")}>
                          <strong>{formatNumber(item.pending_replenishment, locale)}</strong>
                          <small>
                            {t("inventory.position", {
                              count: formatNumber(item.inventory_position, locale),
                            })}
                          </small>
                        </td>
                        <td data-label={t("inventory.status")}>
                          <span className="status-chip" data-status={item.planning_status}>
                            {t(statusKey(item))}
                          </span>
                          {item.latest_reorder ? (
                            <div className="reorder-note">
                              <strong>
                                {t("inventory.reorderQuantity", {
                                  count: formatNumber(item.latest_reorder.quantity, locale),
                                })}
                              </strong>
                              {item.latest_reorder.supplier_reference ? (
                                <span dir="ltr">
                                  {t("inventory.supplierReference", {
                                    reference: item.latest_reorder.supplier_reference,
                                  })}
                                </span>
                              ) : null}
                              {item.latest_reorder.status_detail ? (
                                <span>{item.latest_reorder.status_detail}</span>
                              ) : null}
                            </div>
                          ) : (
                            <small className="no-reorder">{t("inventory.noReorder")}</small>
                          )}
                          <div style={{ marginBlockStart: 10 }}>
                            <InventoryAdjustControl
                              locale={locale}
                              productId={item.product_id}
                              productName={name ?? item.product_id}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="inventory-evidence" aria-label={t("inventory.evidence")}>
          <section>
            <h2>{t("inventory.policy")}</h2>
            <ol>
              <li>{t("inventory.policyForecast")}</li>
              <li>{t("inventory.policyBuffer")}</li>
              <li>{t("inventory.policyTarget")}</li>
            </ol>
          </section>
          <section>
            <h2>{t("inventory.evidence")}</h2>
            <dl>
              <div>
                <dt>{t("inventory.forecast")}</dt>
                <dd>{planning.policy.forecast_days}</dd>
              </div>
              <div>
                <dt>{t("inventory.threshold")}</dt>
                <dd>{planning.policy.lead_time_days + planning.policy.safety_stock_days}</dd>
              </div>
              <div>
                <dt>{t("inventory.target")}</dt>
                <dd>{planning.policy.target_cover_days}</dd>
              </div>
            </dl>
            <p>{t("inventory.synthetic")}</p>
          </section>
        </aside>
      </div>
    </main>
  );
}
