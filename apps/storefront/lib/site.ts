/**
 * Site-wide naming.
 *
 * Every page title used to repeat the brand by hand, which is why a rename was
 * 27 edits instead of one. The root layout owns the template now, so a page
 * declares only what makes it that page.
 */
export const SITE_NAME = "Shelfmark";

/** Used by the root layout as `title.template`; `%s` is the page's own title. */
export const SITE_TITLE_TEMPLATE = `%s — ${SITE_NAME}`;

export const SITE_DESCRIPTION =
  "Synthetic bilingual smart-commerce demonstration: customer storefront and operator back office.";
