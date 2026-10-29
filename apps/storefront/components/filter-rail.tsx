"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { CatalogFacets, Locale } from "@/lib/types";
import { attributeLabel, categoryLabel, translator } from "@/lib/i18n";
import { catalogHref, type CatalogState } from "@/lib/params";
import { CATEGORY_ICONS, IconClose } from "./icons";

const CATEGORY_ORDER = ["phones", "headphones", "laptops", "accessories"];
const HIDDEN_FACET_KEYS = new Set(["category"]);

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

  useEffect(() => {
    if (window.matchMedia("(min-width: 901px)").matches) setOpen(true);
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
    .sort((a, b) => (a.key === "brand" ? -1 : b.key === "brand" ? 1 : a.key.localeCompare(b.key)));

  const activeFilters = Object.entries(state.filters);

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
        <h2>{t("filters.title")}</h2>
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
        <h2 className="rail-title visually-hidden" id="rail-categories">
          {t("filters.categories")}
        </h2>
        <ul className="cat-list">
          <li className="cat-item">
            <Link href={catalogHref({ category: "", page: 1 }, state)} aria-current={!state.category}>
              {t("filters.allCategories")}
              <span className="cat-count">{facets.total}</span>
            </Link>
          </li>
          {orderedCategories.map((category) => {
            const Icon = CATEGORY_ICONS[category];
            return (
              <li className="cat-item" key={category}>
                <Link
                  href={catalogHref({ category, page: 1 }, state)}
                  aria-current={state.category === category}
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

      <section className="rail-section">
        <h2 className="rail-title">{t("filters.results")}</h2>

        <form className="price-form" onSubmit={applyPrice}>
          <p className="field-label">{t("filters.price")}</p>
          <div className="price-inputs">
            <label>
              <span className="visually-hidden">{t("filters.priceFrom")}</span>
              <input
                type="number"
                name="price_min"
                min={0}
                step={1}
                inputMode="numeric"
                placeholder={t("filters.priceFrom")}
                defaultValue={state.priceMin}
              />
            </label>
            <label>
              <span className="visually-hidden">{t("filters.priceTo")}</span>
              <input
                type="number"
                name="price_max"
                min={0}
                step={1}
                inputMode="numeric"
                placeholder={t("filters.priceTo")}
                defaultValue={state.priceMax}
              />
            </label>
          </div>
          <div className="range-track" aria-hidden="true">
            <span />
          </div>
          <button type="submit" className="rail-reset" style={{ marginBlockStart: 10 }}>
            {t("filters.priceApply")}
          </button>
        </form>

        {facetGroups.map((facet) => (
          <fieldset className="facet-group" key={facet.key}>
            <legend className="field-label" style={{ padding: 0 }}>
              {attributeLabel(t, facet.key)}
            </legend>
            {facet.options.map((option) => (
              <label className="check" key={option.value}>
                <input
                  type="checkbox"
                  checked={state.filters[facet.key] === option.value}
                  onChange={() => toggleFilter(facet.key, option.value)}
                />
                <span className="value">{option.value}</span>
                <span className="count">{option.count}</span>
              </label>
            ))}
          </fieldset>
        ))}

        <fieldset className="facet-group">
          <legend className="field-label" style={{ padding: 0 }}>
            {t("filters.availability")}
          </legend>
          <label className="check">
            <input
              type="checkbox"
              checked={state.availability === "in_stock"}
              onChange={() =>
                push({ availability: state.availability === "in_stock" ? "" : "in_stock" })
              }
            />
            <span className="value">{t("filters.inStock")}</span>
          </label>
        </fieldset>

        {activeFilters.length || state.priceMin || state.priceMax || state.availability ? (
          <div className="active-filters">
            <p className="field-label">{t("filters.active")}</p>
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
                    {value}
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
          </div>
        ) : null}

        <button type="button" className="rail-reset" onClick={resetAll}>
          {t("filters.reset")}
        </button>
      </section>
      </div>
    </aside>
  );
}