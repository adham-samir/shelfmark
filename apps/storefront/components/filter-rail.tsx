"use client";

import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { CatalogFacets, Locale } from "@/lib/types";
import {
  attributeLabel,
  categoryLabel,
  facetValueLabel,
  translator,
} from "@/lib/i18n";
import { catalogHref, type CatalogState } from "@/lib/params";
import { CATEGORY_ICONS, IconClose, IconFilter } from "./icons";

const CATEGORY_ORDER = ["phones", "headphones", "laptops", "accessories"];
const HIDDEN_FACET_KEYS = new Set(["category"]);

/** Facet groups longer than this get an inline search box. */
const SEARCH_THRESHOLD = 8;

export function FilterRail({
  locale,
  state,
  facets,
}: {
  locale: Locale;
  state: CatalogState;
  facets: CatalogFacets;
}) {
  const t = translator(locale);
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // Desktop shows the rail expanded; below the breakpoint it starts collapsed so
  // the first screen is products rather than controls.
  useEffect(() => {
    if (window.matchMedia("(min-width: 1001px)").matches) setOpen(true);
  }, []);

  const categoryFacet = facets.facets.find((facet) => facet.key === "category");
  const categoryCounts = new Map(
    (categoryFacet?.options ?? []).map((option) => [option.value, option.count]),
  );
  const orderedCategories = [
    ...CATEGORY_ORDER.filter((value) => categoryCounts.has(value)),
    ...(categoryFacet?.options ?? [])
      .map((option) => option.value)
      .filter((value) => !CATEGORY_ORDER.includes(value)),
  ];

  const facetGroups = facets.facets
    .filter((facet) => !HIDDEN_FACET_KEYS.has(facet.key))
    .sort((a, b) =>
      a.key === "brand" ? -1 : b.key === "brand" ? 1 : a.key.localeCompare(b.key),
    );

  const activeFilters = Object.entries(state.filters);
  const activeCount =
    activeFilters.length +
    (state.category ? 1 : 0) +
    (state.availability ? 1 : 0) +
    (state.priceMin || state.priceMax ? 1 : 0);

  const push = (patch: Partial<CatalogState>) => {
    router.push(catalogHref({ ...patch, page: 1 }, state));
  };

  const toggleFilter = (key: string, value: string) => {
    const next = { ...state.filters };
    if (next[key] === value) delete next[key];
    else next[key] = value;
    push({ filters: next });
  };

  const applyPrice = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const min = String(data.get("price_min") ?? "").trim();
    const max = String(data.get("price_max") ?? "").trim();
    push({ priceMin: min, priceMax: max });
  };

  const resetAll = () => {
    router.push(
      catalogHref(
        {
          category: "",
          filters: {},
          availability: "",
          priceMin: "",
          priceMax: "",
          page: 1,
        },
        state,
      ),
    );
  };

  return (
    <aside className="rail" aria-label={t("filters.title")}>
      <div className="rail-head">
        <h2>
          <IconFilter size={15} aria-hidden="true" />
          {t("filters.title")}
          {activeCount > 0 ? <span className="rail-badge">{activeCount}</span> : null}
        </h2>
        <button
          type="button"
          className="rail-toggle"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls="rail-sections"
        >
          {open ? t("filters.hide") : t("filters.show")}
        </button>
      </div>

      <div id="rail-sections" data-open={open}>
        <section className="rail-section" aria-labelledby="rail-categories">
          <h3 className="rail-title" id="rail-categories">
            {t("filters.categories")}
          </h3>
          <ul className="cat-list">
            <li>
              <Link
                href={catalogHref({ category: "", page: 1 }, state)}
                aria-current={!state.category ? "true" : undefined}
              >
                {t("filters.allCategories")}
                <span className="cat-count">{facets.total}</span>
              </Link>
            </li>
            {orderedCategories.map((category) => {
              const Icon = CATEGORY_ICONS[category];
              return (
                <li key={category}>
                  <Link
                    href={catalogHref({ category, page: 1 }, state)}
                    aria-current={state.category === category ? "true" : undefined}
                  >
                    {Icon ? <Icon size={16} /> : null}
                    {categoryLabel(t, category)}
                    <span className="cat-count">{categoryCounts.get(category) ?? 0}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="rail-section" aria-labelledby="rail-price">
          <h3 className="rail-title" id="rail-price">
            {t("filters.price")}
          </h3>
          <form className="price-form" onSubmit={applyPrice}>
            <div className="price-inputs">
              <label>
                <span className="price-label">{t("filters.priceFrom")}</span>
                <input
                  type="number"
                  name="price_min"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  placeholder="0"
                  defaultValue={state.priceMin}
                />
              </label>
              <label>
                <span className="price-label">{t("filters.priceTo")}</span>
                <input
                  type="number"
                  name="price_max"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  placeholder={t("filters.priceAny")}
                  defaultValue={state.priceMax}
                />
              </label>
            </div>
            <button type="submit" className="btn btn-sm btn-block">
              {t("filters.priceApply")}
            </button>
          </form>
        </section>

        {facetGroups.map((facet) => (
          <FacetGroup
            key={facet.key}
            locale={locale}
            label={attributeLabel(t, facet.key)}
            options={facet.options}
            selected={state.filters[facet.key]}
            onToggle={(value) => toggleFilter(facet.key, value)}
          />
        ))}

        <section className="rail-section" aria-labelledby="rail-availability">
          <h3 className="rail-title" id="rail-availability">
            {t("filters.availability")}
          </h3>
          <label className="check">
            <input
              type="checkbox"
              checked={state.availability === "in_stock"}
              onChange={() =>
                push({
                  availability: state.availability === "in_stock" ? "" : "in_stock",
                })
              }
            />
            <span className="value">{t("filters.inStock")}</span>
          </label>
        </section>

        {activeCount > 0 ? (
          <section className="rail-section active-filters" aria-labelledby="rail-active">
            <h3 className="rail-title" id="rail-active">
              {t("filters.active")}
            </h3>
            <ul className="chips">
              {state.category ? (
                <li>
                  <Link className="chip" href={catalogHref({ category: "", page: 1 }, state)}>
                    {categoryLabel(t, state.category)}
                    <IconClose size={11} />
                  </Link>
                </li>
              ) : null}
              {activeFilters.map(([key, value]) => (
                <li key={`${key}:${value}`}>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => toggleFilter(key, value)}
                    aria-label={`${attributeLabel(t, key)}: ${value}`}
                  >
                    {facetValueLabel(t, value)}
                    <IconClose size={11} />
                  </button>
                </li>
              ))}
              {state.priceMin || state.priceMax ? (
                <li>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => push({ priceMin: "", priceMax: "" })}
                  >
                    {state.priceMin || "0"} – {state.priceMax || "∞"} EGP
                    <IconClose size={11} />
                  </button>
                </li>
              ) : null}
              {state.availability ? (
                <li>
                  <button
                    type="button"
                    className="chip"
                    onClick={() => push({ availability: "" })}
                  >
                    {t("filters.inStock")}
                    <IconClose size={11} />
                  </button>
                </li>
              ) : null}
            </ul>
            <button type="button" className="btn btn-sm btn-quiet btn-block" onClick={resetAll}>
              {t("filters.reset")}
            </button>
          </section>
        ) : null}
      </div>
    </aside>
  );
}

/**
 * One collapsible facet group.
 *
 * Long groups get an inline filter box, because scanning 30 checkboxes is slower
 * than typing three letters. Groups stay open by default when they already hold
 * a selection so the current state is never hidden behind a collapsed header.
 */
function FacetGroup({
  locale,
  label,
  options,
  selected,
  onToggle,
}: {
  locale: Locale;
  label: string;
  options: Array<{ value: string; count: number }>;
  selected: string | undefined;
  onToggle: (value: string) => void;
}) {
  const t = translator(locale);
  const id = useId();
  const [open, setOpen] = useState(true);
  const [query, setQuery] = useState("");

  const searchable = options.length > SEARCH_THRESHOLD;
  const needle = query.trim().toLowerCase();
  const visible = needle
    ? options.filter((option) =>
        facetValueLabel(t, option.value).toLowerCase().includes(needle),
      )
    : options;

  return (
    <section className="rail-section facet-group">
      <h3 className="rail-title">
        <button
          type="button"
          className="facet-toggle"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls={id}
        >
          {label}
          <svg
            className="facet-caret"
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M4 6.5 8 10.5 12 6.5" />
          </svg>
        </button>
      </h3>

      <div id={id} className="facet-body" data-open={open}>
        {searchable ? (
          <label className="facet-search">
            <span className="visually-hidden">
              {t("filters.searchWithin", { group: label })}
            </span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("filters.searchWithin", { group: label })}
            />
          </label>
        ) : null}

        {visible.length === 0 ? (
          <p className="facet-none">{t("filters.searchNone")}</p>
        ) : (
          visible.map((option) => (
            <label className="check" key={option.value}>
              <input
                type="checkbox"
                checked={selected === option.value}
                onChange={() => onToggle(option.value)}
              />
              <span className="value">{facetValueLabel(t, option.value)}</span>
              <span className="count">{option.count}</span>
            </label>
          ))
        )}
      </div>
    </section>
  );
}
