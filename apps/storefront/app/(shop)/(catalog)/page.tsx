import Link from "next/link";
import type { Metadata } from "next";
import type { CatalogFacets, Locale, ProductPage } from "@/lib/types";
import { api, ApiError, type CatalogQuery } from "@/lib/api";
import { getLocale } from "@/lib/locale";
import { categoryLabel, translator } from "@/lib/i18n";
import { formatNumber } from "@/lib/format";
import { catalogHref, catalogQuery, parseCatalogState, type CatalogState } from "@/lib/params";
import { FilterRail } from "@/components/filter-rail";
import { ResultToolbar } from "@/components/result-toolbar";
import { ProductCard } from "@/components/product-card";
import { CompareDock } from "@/components/compare-dock";
import { EmptyState, ErrorState } from "@/components/states";
import { IconArrowBack } from "@/components/icons";

export const metadata: Metadata = {
  title: "الكتالوج — Smart-eCommerce",
};

type RawParams = Record<string, string | string[] | undefined>;

function pageWindow(state: CatalogState, total: number): { from: number; to: number } {
  if (total === 0) return { from: 0, to: 0 };
  const from = (state.page - 1) * state.size + 1;
  return { from, to: Math.min(total, state.page * state.size) };
}

function pageCount(total: number, size: number): number {
  return Math.max(1, Math.ceil(total / size));
}

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<RawParams>;
}) {
  const params = await searchParams;
  const locale: Locale = await getLocale();
  const t = translator(locale);
  const state = parseCatalogState(params);
  const query: CatalogQuery = catalogQuery(state);

  let page: ProductPage | null = null;
  let facets: CatalogFacets | null = null;
  let failure: ApiError | null = null;

  try {
    [page, facets] = await Promise.all([
      api.products(query),
      api.facets({
        q: query.q,
        category: query.category,
        filters: query.filters,
        availability: query.availability,
        priceMin: query.priceMin,
        priceMax: query.priceMax,
      }),
    ]);
  } catch (error) {
    failure = error instanceof ApiError ? error : new ApiError("unknown", 0, "Unexpected");
  }

  const total = page?.total ?? 0;
  const range = pageWindow(state, total);
  const pages = pageCount(total, state.size);
  const activeFilterSummary = [
    state.category ? categoryLabel(t, state.category) : null,
    ...Object.entries(state.filters).map(([, value]) => value),
    state.priceMin || state.priceMax
      ? `${state.priceMin || "0"} – ${state.priceMax || "∞"} EGP`
      : null,
    state.availability ? t("filters.inStock") : null,
  ].filter(Boolean) as string[];

  return (
    <main className="workbench" id="main">
      <FilterRail
        locale={locale}
        state={state}
        facets={facets ?? { total, facets: [] }}
      />

      <section className="field-column" aria-labelledby="results-heading">
        <h1 id="results-heading" className="visually-hidden">
          {t("nav.catalog")}
        </h1>

        {failure ? (
          <ErrorState
            locale={locale}
            title={t("listing.loadError")}
            hint={t("listing.loadErrorHint")}
            onRetryHref={catalogHref({}, state)}
          />
        ) : (
          <>
            <div className="result-bar">
              <p className="result-meta" aria-live="polite">
                {t("listing.meta", {
                  from: formatNumber(range.from, locale),
                  to: formatNumber(range.to, locale),
                  total: formatNumber(total, locale),
                })}{" "}
                {t("listing.synthetic")}
                <span className="stale">{t("listing.stale")}</span>
              </p>
              <ResultToolbar locale={locale} state={state} />
            </div>

            {page && page.items.length ? (
              <div className="product-grid anim" data-view={state.view}>
                {page.items.map((product, index) => (
                  <ProductCard
                    key={product.product_id}
                    product={product}
                    locale={locale}
                    index={index}
                    priority={index < 3}
                  />
                ))}
              </div>
            ) : (
              <div className="pad-block-4">
                <EmptyState
                  title={t("listing.noResults")}
                  hint={
                    activeFilterSummary.length
                      ? `${t("listing.noResultsHint")} ${t("filters.active")}: ${activeFilterSummary.join(" · ")}`
                      : t("listing.noResultsHint")
                  }
                >
                  <Link className="btn" href="/">
                    {t("filters.reset")}
                  </Link>
                  {state.q ? (
                    <Link className="btn btn-quiet" href={catalogHref({ q: "" }, state)}>
                      {t("search.clear")}
                    </Link>
                  ) : null}
                </EmptyState>
              </div>
            )}

            {pages > 1 ? (
              <nav className="pagination" aria-label={t("listing.page", { page: state.page })}>
                <Link
                  className={state.page <= 1 ? "disabled" : ""}
                  href={catalogHref({ page: Math.max(1, state.page - 1) }, state)}
                  aria-label={t("listing.prev")}
                  aria-disabled={state.page <= 1}
                  tabIndex={state.page <= 1 ? -1 : undefined}
                >
                  <IconArrowBack size={14} />
                </Link>
                {Array.from({ length: pages }).map((_, index) => {
                  const number = index + 1;
                  return (
                    <Link
                      key={number}
                      href={catalogHref({ page: number }, state)}
                      aria-current={number === state.page ? "page" : undefined}
                    >
                      {formatNumber(number, locale)}
                    </Link>
                  );
                })}
                <Link
                  className={state.page >= pages ? "disabled" : ""}
                  href={catalogHref({ page: Math.min(pages, state.page + 1) }, state)}
                  aria-label={t("listing.next")}
                  aria-disabled={state.page >= pages}
                  tabIndex={state.page >= pages ? -1 : undefined}
                >
                  <IconArrowBack size={14} style={{ transform: "rotate(180deg)" }} />
                </Link>
              </nav>
            ) : null}
          </>
        )}
      </section>

      <CompareDock locale={locale} />
    </main>
  );
}