import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/lib/format";
import { translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { Locale, PricingInputStatus, PricingOverviewItem } from "@/lib/types";
import { PricingObservationForm } from "@/components/pricing-observation-form";
import { PricingRunControl } from "@/components/pricing-run-control";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Dynamic pricing — Smart-eCommerce",
  description:
    "Synthetic BO-02 pricing inputs, bounded automatic price changes, and the DEC-009 audit trail.",
};

function outcomeKey(outcome: string) {
  switch (outcome) {
    case "would_update":
      return "pricing.wouldUpdate" as const;
    case "updated":
      return "pricing.updatedOutcome" as const;
    case "unchanged":
      return "pricing.unchanged" as const;
    case "missing_input":
      return "pricing.missingInput" as const;
    case "stale_input":
      return "pricing.staleInput" as const;
    case "constraint_blocked":
      return "pricing.blocked" as const;
    case "already_applied":
      return "pricing.alreadyApplied" as const;
    case "conflict":
      return "pricing.conflict" as const;
    default:
      return "pricing.noProposal" as const;
  }
}

function inputStatusKey(status: PricingInputStatus) {
  switch (status) {
    case "fresh":
      return "pricing.freshStatus" as const;
    case "stale":
      return "pricing.staleStatus" as const;
    default:
      return "pricing.missingStatus" as const;
  }
}

function deltaLabel(item: PricingOverviewItem): string | null {
  if (item.proposed_amount === null) return null;
  const current = Number(item.current_amount);
  const proposed = Number(item.proposed_amount);
  if (!Number.isFinite(current) || current === 0 || !Number.isFinite(proposed)) {
    return null;
  }
  const delta = ((proposed - current) / current) * 100;
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`;
}

export default async function PricingPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  let pricing;
  try {
    pricing = await api.pricing();
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("pricing.unauthorized")
        : permissionCode === "forbidden"
          ? t("pricing.forbidden")
          : t("pricing.loadFailed");
    const errorHint =
      permissionCode === "unauthorized"
        ? t("pricing.unauthorizedHint")
        : permissionCode === "forbidden"
          ? t("pricing.forbiddenHint")
          : error instanceof ApiError
            ? `${t("pricing.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
            : t("pricing.loadFailedHint");
    return (
      <main className="page inventory-page pricing-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("pricing.title")}</h1>
            <p>{t("pricing.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref="/backoffice/pricing"
        />
      </main>
    );
  }

  const products: { id: string; name: string }[] = [];
  const names = new Map<string, string>();
  try {
    const catalog = await api.products({ limit: 100 });
    for (const product of catalog.items) {
      names.set(product.product_id, product.name);
      products.push({ id: product.product_id, name: product.name });
    }
  } catch {
    // Product IDs remain an honest fallback when the descriptive catalog is unavailable.
  }

  const fresh = pricing.items.filter((item) => item.input_status === "fresh").length;
  const attention = pricing.items.length - fresh;
  const seasonLabel =
    locale === "ar" ? pricing.season.label_ar : pricing.season.label_en;
  const seasonWindow =
    pricing.season.starts_on && pricing.season.ends_on
      ? t("pricing.seasonWindow", {
          from: formatDate(pricing.season.starts_on, locale),
          to: formatDate(pricing.season.ends_on, locale),
        })
      : null;

  return (
    <main className="page inventory-page pricing-page" id="main">
      <header className="inventory-command">
        <div>
          <h1>{t("pricing.title")}</h1>
          <p>{t("pricing.intro")}</p>
          <div className="inventory-command-meta">
            <span>{t("pricing.operator")}</span>
            <time dateTime={pricing.generated_at}>
              {t("pricing.updated", {
                time: formatDateTime(pricing.generated_at, locale),
              })}
            </time>
            <span>{seasonLabel}</span>
            {seasonWindow ? <span>{seasonWindow}</span> : null}
            <span>
              {t("pricing.multiplier", { value: pricing.season.price_multiplier })}
            </span>
          </div>
        </div>
        <PricingRunControl locale={locale} />
      </header>

      <section className="inventory-ledger" aria-label={t("pricing.inputStatus")}>
        {[
          [t("pricing.products"), pricing.items.length],
          [t("pricing.fresh"), fresh],
          [t("pricing.attention"), attention],
          [t("pricing.changes"), pricing.recent_changes.length],
        ].map(([label, value]) => (
          <div key={String(label)}>
            <strong>{formatNumber(Number(value), locale)}</strong>
            <span>{label}</span>
          </div>
        ))}
      </section>

      <div className="inventory-layout">
        <section className="inventory-sheet" aria-labelledby="pricing-table-title">
          <div className="inventory-sheet-head">
            <h2 id="pricing-table-title">{t("pricing.product")}</h2>
            <span>{pricing.policy.version}</span>
          </div>
          {pricing.items.length === 0 ? (
            <EmptyState title={t("pricing.empty")} />
          ) : (
            <div className="inventory-table-wrap" tabIndex={0}>
              <table className="inventory-table pricing-table">
                <thead>
                  <tr>
                    <th>{t("pricing.product")}</th>
                    <th>{t("pricing.currentPrice")}</th>
                    <th>{t("pricing.inputs")}</th>
                    <th>{t("pricing.inputStatus")}</th>
                    <th>{t("pricing.proposal")}</th>
                    <th>{t("pricing.lastChange")}</th>
                  </tr>
                </thead>
                <tbody>
                  {pricing.items.map((item) => {
                    const name = names.get(item.product_id);
                    const delta = deltaLabel(item);
                    return (
                      <tr key={item.product_id} data-status={item.outcome}>
                        <th scope="row">
                          {name ? (
                            <Link href={`/products/${item.product_id}`}>{name}</Link>
                          ) : (
                            <span>{item.product_id}</span>
                          )}
                          <code dir="ltr">{item.product_id.slice(-12)}</code>
                        </th>
                        <td data-label={t("pricing.currentPrice")}>
                          <div className="price-cell">
                            <strong>
                              {formatMoney(item.current_amount, locale)} {item.currency}
                            </strong>
                            <small>
                              {t("pricing.updated", {
                                time: formatDateTime(item.price_updated_at, locale),
                              })}
                            </small>
                          </div>
                        </td>
                        <td data-label={t("pricing.inputs")}>
                          {item.observation ? (
                            <>
                              <dl className="input-stack">
                                <div>
                                  <dt>{t("pricing.cost")}</dt>
                                  <dd>
                                    {formatMoney(item.observation.recorded_cost, locale)}
                                  </dd>
                                </div>
                                <div>
                                  <dt>{t("pricing.competitor")}</dt>
                                  <dd>
                                    {formatMoney(item.observation.competitor_cost, locale)}
                                  </dd>
                                </div>
                                <div>
                                  <dt>{t("pricing.supply")}</dt>
                                  <dd>{formatMoney(item.observation.supply, locale)}</dd>
                                </div>
                                <div>
                                  <dt>{t("pricing.demand")}</dt>
                                  <dd>{formatMoney(item.observation.demand, locale)}</dd>
                                </div>
                              </dl>
                              <small>
                                {t("pricing.observedAt", {
                                  time: formatDateTime(
                                    item.observation.observed_at,
                                    locale,
                                  ),
                                })}
                              </small>
                            </>
                          ) : (
                            <span className="missing-data">
                              {t("pricing.missingInput")}
                            </span>
                          )}
                        </td>
                        <td data-label={t("pricing.inputStatus")}>
                          <span
                            className="status-chip"
                            data-status={item.input_status}
                          >
                            {t(inputStatusKey(item.input_status))}
                          </span>
                        </td>
                        <td data-label={t("pricing.proposal")}>
                          <span className="status-chip" data-status={item.outcome}>
                            {t(outcomeKey(item.outcome))}
                          </span>
                          {item.proposed_amount !== null ? (
                            <div className="proposal-cell">
                              <strong>
                                {formatMoney(item.proposed_amount, locale)}{" "}
                                {item.currency}
                              </strong>
                              {delta ? <span dir="ltr">{delta}</span> : null}
                            </div>
                          ) : null}
                          {item.detail &&
                          [
                            "stale_input",
                            "missing_input",
                            "constraint_blocked",
                            "conflict",
                          ].includes(item.outcome) ? (
                            <small>{item.detail}</small>
                          ) : null}
                        </td>
                        <td data-label={t("pricing.lastChange")}>
                          {item.latest_change ? (
                            <div className="proposal-cell">
                              <span className="change-line" dir="ltr">
                                {formatMoney(item.latest_change.old_amount, locale)} →{" "}
                                {formatMoney(item.latest_change.new_amount, locale)}
                              </span>
                              <small>
                                {t("pricing.updated", {
                                  time: formatDateTime(
                                    item.latest_change.applied_at,
                                    locale,
                                  ),
                                })}
                              </small>
                            </div>
                          ) : (
                            <span className="missing-data">
                              {t("pricing.noChanges")}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="inventory-evidence" aria-label={t("pricing.evidence")}>
          <section>
            <h2>{t("pricing.policy")}</h2>
            <ol>
              <li>{t("pricing.policyCap")}</li>
              <li>{t("pricing.policyFloor")}</li>
              <li>{t("pricing.policyFresh")}</li>
            </ol>
          </section>
          <section>
            <h2>{t("pricing.evidence")}</h2>
            <dl>
              <div>
                <dt>{t("pricing.weights")}</dt>
                <dd dir="ltr">
                  {pricing.policy.demand_weight} / {pricing.policy.competitor_weight}
                </dd>
              </div>
              <div>
                <dt>{t("pricing.rounding")}</dt>
                <dd dir="ltr">{pricing.policy.rounding}</dd>
              </div>
            </dl>
            <p>{t("pricing.synthetic")}</p>
          </section>
          <section>
            <h2>{t("pricing.audit")}</h2>
            {pricing.recent_changes.length === 0 ? (
              <p>{t("pricing.noChanges")}</p>
            ) : (
              <ol className="audit-list">
                {pricing.recent_changes.slice(0, 8).map((change) => (
                  <li key={change.price_change_id}>
                    <span>{names.get(change.product_id) ?? change.product_id}</span>
                    <strong dir="ltr">
                      {formatMoney(change.old_amount, locale)} →{" "}
                      {formatMoney(change.new_amount, locale)}
                    </strong>
                    <small>
                      {formatDateTime(change.applied_at, locale)} ·{" "}
                      {change.calculation_version}
                    </small>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </aside>
      </div>

      <PricingObservationForm locale={locale} products={products} />
    </main>
  );
}