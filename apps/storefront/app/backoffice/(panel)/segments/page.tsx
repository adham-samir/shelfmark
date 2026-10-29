import type { Metadata } from "next";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/lib/format";
import { translator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { Locale, SegmentName, SegmentationResponse } from "@/lib/types";
import { SegmentationRunControl } from "@/components/segmentation-run-control";
import { EmptyState, ErrorState } from "@/components/states";

export const metadata: Metadata = {
  title: "Customer segmentation — Smart-eCommerce",
  description:
    "Synthetic BO-03 RFM snapshots, quintile scores, six selectable segments, and CSV export.",
};

const SEGMENTS: SegmentName[] = [
  "champions",
  "loyal",
  "potential",
  "new",
  "at_risk",
  "hibernating",
];

const PAGE_SIZE = 25;

function isSegment(value: unknown): value is SegmentName {
  return typeof value === "string" && (SEGMENTS as string[]).includes(value);
}

function segmentKey(segment: SegmentName) {
  switch (segment) {
    case "champions":
      return "segments.champions" as const;
    case "loyal":
      return "segments.loyal" as const;
    case "potential":
      return "segments.potential" as const;
    case "new":
      return "segments.new" as const;
    case "at_risk":
      return "segments.at_risk" as const;
    default:
      return "segments.hibernating" as const;
  }
}

function pageHref(segment: SegmentName | undefined, page: number): string {
  const params = new URLSearchParams();
  if (segment) params.set("segment", segment);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return `/backoffice/segments${query ? `?${query}` : ""}`;
}

function scoreChip(score: number) {
  return (
    <span className="score-chip" data-score={score}>
      {score}
    </span>
  );
}

export default async function SegmentsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const segment = isSegment(params.segment) ? params.segment : undefined;
  const rawPage = typeof params.page === "string" ? Number(params.page) : 1;
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;

  let overview: SegmentationResponse;
  try {
    overview = await api.segments({
      segment,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    });
  } catch (error) {
    const permissionCode = error instanceof ApiError ? error.code : null;
    const errorTitle =
      permissionCode === "unauthorized"
        ? t("segments.unauthorized")
        : permissionCode === "forbidden"
          ? t("segments.forbidden")
          : t("segments.loadFailed");
    const errorHint =
      permissionCode === "unauthorized"
        ? t("segments.unauthorizedHint")
        : permissionCode === "forbidden"
          ? t("segments.forbiddenHint")
          : error instanceof ApiError
            ? `${t("segments.loadFailedHint")} (${error.code}${error.requestId ? ` · ${error.requestId}` : ""})`
            : t("segments.loadFailedHint");
    return (
      <main className="page inventory-page segments-page" id="main">
        <div className="page-head">
          <div>
            <h1>{t("segments.title")}</h1>
            <p>{t("segments.intro")}</p>
          </div>
        </div>
        <ErrorState
          locale={locale}
          title={errorTitle}
          hint={errorHint}
          onRetryHref="/backoffice/segments"
        />
      </main>
    );
  }

  const counts = new Map(
    overview.counts.map((count) => [count.segment, count.customers]),
  );
  const activeSegments = overview.counts.filter(
    (count) => count.customers > 0,
  ).length;
  const pages = Math.max(1, Math.ceil(overview.total_members / PAGE_SIZE));
  const from = overview.total_members === 0 ? 0 : overview.offset + 1;
  const to = Math.min(
    overview.total_members,
    overview.offset + overview.members.length,
  );
  const selectedLabel = segment ? t(segmentKey(segment)) : t("segments.members");

  return (
    <main className="page inventory-page segments-page" id="main">
      <header className="inventory-command">
        <div>
          <h1>{t("segments.title")}</h1>
          <p>{t("segments.intro")}</p>
          <div className="inventory-command-meta">
            <span>{t("segments.operator")}</span>
            {overview.reference_date ? (
              <span>
                {t("segments.referenceDate", {
                  date: formatDate(overview.reference_date, locale),
                })}
              </span>
            ) : null}
            {overview.generated_at ? (
              <span>
                {t("segments.generated", {
                  time: formatDateTime(overview.generated_at, locale),
                })}
              </span>
            ) : null}
            <span>
              {overview.snapshot_available
                ? overview.stale
                  ? t("segments.stale")
                  : t("segments.fresh")
                : t("segments.noSnapshot")}
            </span>
          </div>
        </div>
        <SegmentationRunControl locale={locale} />
      </header>

      {!overview.snapshot_available ? (
        <EmptyState
          title={t("segments.noSnapshot")}
          hint={t("segments.noSnapshotHint")}
        />
      ) : (
        <>
          <section className="inventory-ledger" aria-label={t("segments.cohort")}>
            {[
              [t("segments.cohort"), overview.cohort_size],
              [t("segments.insufficient"), overview.insufficient_history],
              [t("segments.selected"), overview.total_members],
              [t("segments.activeSegments"), activeSegments],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <strong>{formatNumber(Number(value), locale)}</strong>
                <span>{label}</span>
              </div>
            ))}
          </section>

          <section className="segments-grid" aria-label={t("segments.segment")}>
            {SEGMENTS.map((name) => (
              <Link
                key={name}
                className="segment-card"
                href={pageHref(name, 1)}
                aria-current={segment === name ? "page" : undefined}
              >
                <strong>{formatNumber(counts.get(name) ?? 0, locale)}</strong>
                <span>{t(segmentKey(name))}</span>
              </Link>
            ))}
          </section>

          <div className="inventory-layout">
            <section className="inventory-sheet" aria-labelledby="segments-table-title">
              <div className="inventory-sheet-head">
                <h2 id="segments-table-title">{selectedLabel}</h2>
                <div className="segments-head-actions">
                  {segment ? (
                    <Link href={pageHref(undefined, 1)}>
                      {t("segments.allSegments")}
                    </Link>
                  ) : null}
                  <Link
                    className="btn segments-export"
                    href={`/backoffice/segments/export${segment ? `?segment=${segment}` : ""}`}
                    title={t("segments.exportHint")}
                  >
                    {t("segments.export")}
                  </Link>
                </div>
              </div>
              {overview.members.length === 0 ? (
                <EmptyState title={t("segments.noMembers")} />
              ) : (
                <div className="inventory-table-wrap">
                  <table className="inventory-table segments-table">
                    <thead>
                      <tr>
                        <th>{t("segments.customer")}</th>
                        <th>{t("segments.recency")}</th>
                        <th>{t("segments.frequency")}</th>
                        <th>{t("segments.monetary")}</th>
                        <th>{t("segments.segment")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.members.map((member) => (
                        <tr key={member.customer_id} data-status={member.segment}>
                          <th scope="row">
                            <span>{member.display_name}</span>
                            <code dir="ltr">{member.email}</code>
                          </th>
                          <td data-label={t("segments.recency")}>
                            <span className="metric-value">
                              {t("segments.days", {
                                count: formatNumber(member.recency_days, locale),
                              })}
                            </span>
                            {scoreChip(member.recency_score)}
                          </td>
                          <td data-label={t("segments.frequency")}>
                            <span className="metric-value">
                              {t("segments.orders", {
                                count: formatNumber(member.frequency, locale),
                              })}
                            </span>
                            {scoreChip(member.frequency_score)}
                          </td>
                          <td data-label={t("segments.monetary")}>
                            <span className="metric-value" dir="ltr">
                              {formatMoney(member.monetary, locale)} EGP
                            </span>
                            {scoreChip(member.monetary_score)}
                          </td>
                          <td data-label={t("segments.segment")}>
                            <span
                              className="status-chip"
                              data-status={member.segment}
                            >
                              {t(segmentKey(member.segment))}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="segments-pager">
                <span>
                  {t("segments.showing", {
                    from: formatNumber(from, locale),
                    to: formatNumber(to, locale),
                    total: formatNumber(overview.total_members, locale),
                  })}
                </span>
                <nav aria-label={t("segments.page", { page, pages })}>
                  {page > 1 ? (
                    <Link href={pageHref(segment, page - 1)}>
                      {t("segments.previous")}
                    </Link>
                  ) : (
                    <span aria-disabled="true">{t("segments.previous")}</span>
                  )}
                  <span>
                    {t("segments.page", {
                      page: formatNumber(Math.min(page, pages), locale),
                      pages: formatNumber(pages, locale),
                    })}
                  </span>
                  {page < pages ? (
                    <Link href={pageHref(segment, page + 1)}>
                      {t("segments.next")}
                    </Link>
                  ) : (
                    <span aria-disabled="true">{t("segments.next")}</span>
                  )}
                </nav>
              </div>
            </section>

            <aside className="inventory-evidence" aria-label={t("segments.policy")}>
              <section>
                <h2>{t("segments.policy")}</h2>
                <ol>
                  <li>{t("segments.policyWindow")}</li>
                  <li>{t("segments.policyEligible")}</li>
                  <li>{t("segments.policyExcluded")}</li>
                  <li>{t("segments.policyScoring")}</li>
                  <li>
                    {t("segments.policyMinimum", {
                      count: overview.policy.minimum_cohort_size,
                    })}
                  </li>
                </ol>
              </section>
              <section>
                <h2>{t("segments.policyMatrix")}</h2>
                <ol className="segments-rules">
                  {overview.policy.rules.map((rule) => (
                    <li key={rule.segment}>
                      <strong>{t(segmentKey(rule.segment))}</strong>
                      <code dir="ltr">{rule.rule}</code>
                    </li>
                  ))}
                </ol>
              </section>
              <section>
                <h2>{t("segments.evidence")}</h2>
                <p>{t("segments.synthetic")}</p>
              </section>
            </aside>
          </div>
        </>
      )}
    </main>
  );
}