"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Locale } from "@/lib/types";
import { translator } from "@/lib/i18n";
import { catalogHref, PAGE_SIZES, type CatalogState } from "@/lib/params";
import { IconGrid, IconList } from "./icons";

export function ResultToolbar({ locale, state }: { locale: Locale; state: CatalogState }) {
  const t = translator(locale);
  const router = useRouter();

  const go = (patch: Partial<CatalogState>) => {
    router.push(catalogHref({ ...patch, page: 1 }, state));
  };

  return (
    <div className="toolbar">
      <label className="control">
        <span>{t("listing.sort")}</span>
        <select
          value={state.sort}
          onChange={(event) => go({ sort: event.target.value as CatalogState["sort"] })}
          aria-label={t("listing.sort")}
        >
          <option value="relevance">{t("listing.sortRelevance")}</option>
          <option value="price_asc">{t("listing.sortPriceAsc")}</option>
          <option value="price_desc">{t("listing.sortPriceDesc")}</option>
          <option value="name_asc">{t("listing.sortName")}</option>
        </select>
      </label>

      <div className="view-toggle" role="group" aria-label={t("listing.gridView")}>
        <Link
          href={catalogHref({ view: "grid" }, state)}
          aria-current={state.view === "grid" ? "true" : undefined}
          aria-label={t("listing.gridView")}
        >
          <IconGrid size={15} />
        </Link>
        <Link
          href={catalogHref({ view: "list" }, state)}
          aria-current={state.view === "list" ? "true" : undefined}
          aria-label={t("listing.listView")}
        >
          <IconList size={15} />
        </Link>
      </div>

      <label className="control">
        <span>{t("listing.pageSize")}</span>
        <select
          value={state.size}
          onChange={(event) => go({ size: Number(event.target.value) })}
          aria-label={t("listing.pageSize")}
        >
          {PAGE_SIZES.map((size) => (
            <option value={size} key={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}