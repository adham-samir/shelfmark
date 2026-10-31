import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import { translator, type MessageKey, type Translate } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { FraudModelSummary, Locale, ReviewQueueItem } from "@/lib/types";
import { RiskDecisionForm } from "@/components/risk-decision-form";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Payment risk review — Smart-eCommerce",
  description:
    "Synthetic BO-04 fraud assessment, scored review queue, and audited operator decisions.",
};

function percent(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function outcomeKey(outcome: ReviewQueueItem["outcome"]) {
  return outcome === "assessment_failed"
    ? ("risk.failedOutcome" as const)
    : ("risk.reviewOutcome" as const);
}

/**
 * The fraud model emits stable reason identifiers. Operators get the plain
 * sentence; the identifier stays underneath as the reference that matches the
 * logs and the model artifact.
 */
const reasonKeys: Record<string, MessageKey> = {
  amount_above_customer_norm: "risk.reason.amountAboveNorm",
  order_velocity_24h_high: "risk.reason.orderVelocity",
  prior_failed_attempts: "risk.reason.priorFailures",
  new_shipping_address: "risk.reason.newAddress",
  payment_token_reuse: "risk.reason.tokenReuse",
  unusual_order_hour: "risk.reason.unusualHour",
  first_order: "risk.reason.firstOrder",
  fraud_model_unavailable: "risk.reason.modelUnavailable",
  model_score_at_or_above_threshold: "risk.reason.scoreAbove",
  model_score_below_threshold: "risk.reason.scoreBelow",
};

function reasonLabel(t: Translate, reason: string): string {
  const key = reasonKeys[reason];
  return key ? t(key) : reason;
}

export default async function RiskPage() {
  const locale: Locale = await getLocale();
  const t = translator(locale);

  let reviews: ReviewQueueItem[];
  try {
    reviews = await api.riskReviews();
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("risk.unauthorized")
        : permissionCode === "forbidden"
          ? t("risk.forbidden")
          : t("risk.loadFailed");
    const errorHint =
      permissionCode === "unauthorized"
        ? t("risk.unauthorizedHint")
        : permissionCode === "forbidden"
          ? t("risk.forbiddenHint")
          : error instanceof ApiError
            ? `${t("risk.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
            : t("risk.loadFailedHint");
    return (
      <main className="page inventory-page risk-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("risk.title")}</h1>
            <p>{t("risk.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref="/backoffice/risk"
        />
      </main>
    );
  }

  let model: FraudModelSummary | null = null;
  try {
    model = await api.riskModel();
  } catch {
    // The queue remains usable; the model card reports the missing artifact.
  }

  const failures = reviews.filter(
    (item) => item.outcome === "assessment_failed",
  ).length;
  const metrics = model?.metrics ?? {};

  return (
    <main className="page inventory-page risk-page" id="main">
      <header className="inventory-command">
        <div>
          <h1>{t("risk.title")}</h1>
          <p>{t("risk.intro")}</p>
          <div className="inventory-command-meta">
            <span>{t("risk.operator")}</span>
            {model ? <span>{model.version_label}</span> : null}
            {model ? (
              <span>
                {t("risk.threshold")}: {percent(Number(model.threshold))}
              </span>
            ) : null}
            <span>
              {t("risk.updated", {
                time: formatDateTime(new Date().toISOString(), locale),
              })}
            </span>
          </div>
        </div>
      </header>

      <section className="inventory-ledger" aria-label={t("risk.pending")}>
        {[
          [t("risk.pending"), reviews.length],
          [t("risk.failures"), failures],
          [
            t("risk.recall"),
            metrics.recall === undefined ? "—" : percent(metrics.recall),
          ],
          [
            t("risk.fpr"),
            metrics.false_positive_rate === undefined
              ? "—"
              : percent(metrics.false_positive_rate),
          ],
        ].map(([label, value]) => (
          <div key={String(label)}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </section>

      <div className="ledger-layout">
        <section className="inventory-sheet" aria-labelledby="risk-table-title">
          <div className="inventory-sheet-head">
            <h2 id="risk-table-title">{t("risk.pending")}</h2>
            <span>{model?.dataset_snapshot_id ?? ""}</span>
          </div>
          {reviews.length === 0 ? (
            <EmptyState
              title={t("risk.noReviews")}
              hint={t("risk.noReviewsHint")}
            />
          ) : (
            <div className="inventory-table-wrap" tabIndex={0}>
              <table className="inventory-table risk-table">
                <thead>
                  <tr>
                    <th>{t("risk.order")}</th>
                    <th>{t("risk.subtotal")}</th>
                    <th>{t("risk.score")}</th>
                    <th>{t("risk.outcome")}</th>
                    <th>{t("risk.reasons")}</th>
                    <th>{t("risk.decision")}</th>
                  </tr>
                </thead>
                <tbody>
                  {reviews.map((review) => (
                    <tr key={review.assessment_id} data-status={review.outcome}>
                      <th scope="row">
                        <Link href={`/backoffice/orders/${review.order_id}`} dir="ltr">
                          <code>{review.order_id.slice(-12)}</code>
                        </Link>
                        <small>
                          {t("risk.assessedAt")}:{" "}
                          {formatDateTime(review.assessed_at, locale)}
                        </small>
                        {review.model_version ? (
                          <small dir="ltr">{review.model_version}</small>
                        ) : null}
                      </th>
                      <td data-label={t("risk.subtotal")}>
                        <span className="metric-value" dir="ltr">
                          {formatMoney(review.subtotal, locale)} EGP
                        </span>
                      </td>
                      <td data-label={t("risk.score")}>
                        <span className="metric-value">
                          {review.score === null
                            ? "—"
                            : `${(Number(review.score) * 100).toFixed(1)}%`}
                        </span>
                      </td>
                      <td data-label={t("risk.outcome")}>
                        <span
                          className="status-chip"
                          data-status={review.outcome}
                        >
                          {t(outcomeKey(review.outcome))}
                        </span>
                      </td>
                      <td data-label={t("risk.reasons")}>
                        <ul className="risk-reasons">
                          {review.reasons.map((reason) => (
                            <li key={reason}>
                              <span>{reasonLabel(t, reason)}</span>
                              <code dir="ltr">{reason}</code>
                            </li>
                          ))}
                        </ul>
                      </td>
                      <td data-label={t("risk.allow")}>
                        <RiskDecisionForm
                          locale={locale}
                          assessmentId={review.assessment_id}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="inventory-evidence" aria-label={t("risk.model")}>
          <section>
            <h2>{t("risk.model")}</h2>
            {model ? (
              <>
                <dl>
                  <div>
                    <dt>{t("risk.modelVersion")}</dt>
                    <dd dir="ltr">{model.version_label}</dd>
                  </div>
                  <div>
                    <dt>{t("risk.threshold")}</dt>
                    <dd dir="ltr">{percent(Number(model.threshold))}</dd>
                  </div>
                  <div>
                    <dt>{t("risk.recall")}</dt>
                    <dd dir="ltr">{percent(metrics.recall)}</dd>
                  </div>
                  <div>
                    <dt>{t("risk.precision")}</dt>
                    <dd dir="ltr">{percent(metrics.precision)}</dd>
                  </div>
                  <div>
                    <dt>{t("risk.fpr")}</dt>
                    <dd dir="ltr">{percent(metrics.false_positive_rate)}</dd>
                  </div>
                  <div>
                    <dt>{t("risk.prAuc")}</dt>
                    <dd dir="ltr">
                      {typeof metrics.pr_auc === "number"
                        ? metrics.pr_auc.toFixed(3)
                        : "—"}
                    </dd>
                  </div>
                </dl>
                <p>{model.limitations}</p>
              </>
            ) : (
              <>
                <p data-tone="error">{t("risk.modelUnavailable")}</p>
                <p>{t("risk.modelUnavailableHint")}</p>
              </>
            )}
          </section>
          {model ? (
            <section>
              <h2>{t("risk.features")}</h2>
              <ol className="segments-rules">
                {model.feature_names.map((feature) => (
                  <li key={feature}>
                    <code dir="ltr">{feature}</code>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
          <section>
            <h2>{t("risk.limitations")}</h2>
            <p>{t("risk.synthetic")}</p>
          </section>
        </aside>
      </div>
    </main>
  );
}