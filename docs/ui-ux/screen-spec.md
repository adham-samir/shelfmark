# Screen and interaction specification

## Global shell

- Arabic is the initial locale with RTL layout; English switches copy, direction, date, and number presentation without changing capability.
- Header exposes product name, catalog search, locale, account, and cart. Back-office users receive a separate navigation area after authorization.
- EGP is the selected currency. API amounts remain exact decimal strings; the UI formats them without silently changing stored values.
- Every surface defines loading, empty, failure, unauthorized, insufficient-data, and stale-data states. Focus remains visible and returns to the triggering control after drawers/dialogs close.
- Desktop supports dense workbench layouts. At tablet/mobile widths, filters become an in-flow drawer, comparison becomes a dedicated route/panel, and tables become labeled rows without horizontal loss of meaning.

## Customer surfaces

| Route | Purpose and required controls | Important states |
|---|---|---|
| `/` | Product discovery workbench: text search, categories, dynamic filters, availability, sorting, result count, compare selection, add to cart | Initial, loading skeleton, no results with active-filter summary, dependency failure/retry, stale observation timestamp |
| `/products/[id]` | Descriptive catalog, image gallery, exact current price, availability, attributes, recommendation rail, add to cart | Missing/draft 404, unavailable price/stock 503, insufficient recommendation history |
| `/compare` | Two products compared side by side with aligned category-relevant attributes and explicit missing values; the route also accepts up to four IDs directly | Empty slots, incompatible categories explained, stale product removed |
| `/search/image` | Upload/camera image, preview, processing status, catalog matches, text alternative | Invalid image feedback for type/size/content, processing failure, no match, permission fallback |
| `/search/voice` | Microphone request, live/finished state, editable transcript, results and filters | Unsupported browser, denied permission, empty recognition, provider failure; text input always available |
| `/assistant` | Bilingual conversation with inquiry, suitable-product, and own-shipment tools; cited catalog/order facts | Signed-out shipment request, missing source, upstream failure, cross-customer denial without existence disclosure |
| `/cart` | Items, quantities, current-price recheck, availability, totals, checkout action | Empty, price changed, item unavailable, quantity conflict |
| `/checkout` | Address/contact, sandbox payment tokenization, review, risk-assessment progress, outcome | Validation, provider failure, pending risk review, retry-safe submission; completion unavailable before risk result |
| `/orders/[id]` | Own order items/prices, payment/risk handling status, shipment timeline | Unauthorized/not found, pending review, tracking unavailable |

## Back-office surfaces

| Route | Purpose and required controls | Important states |
|---|---|---|
| `/backoffice/catalog` | Draft/active/archived products, missing-counterpart warnings, publication readiness | Partial Mongo/PostgreSQL record, invalid catalog data, retry/reconcile |
| `/backoffice/inventory` | Current/reserved/available stock, forecasts, pending replenishment, automatic reorder records | Insufficient history, forecast failure, supplier simulator failure, duplicate-prevention status |
| `/backoffice/pricing` | Current price, required input freshness, competitor-cost import, season, proposed/applied changes and audit | Missing/stale input, constraint block, conflicting checkout price |
| `/backoffice/segments` | RFM reference date, scores, segment counts, customer-group selection | No eligible orders, stale snapshot, calculation failure |
| `/backoffice/risk` | Pre-completion assessments, score/model version, review queue and handling status | Assessment unavailable, permission denied, ambiguous/manual review |
| `/backoffice/analytics` | Consumer behavior and financial performance with date/category filters | Empty/partial source, metric definition help, reconciliation mismatch; profit omitted without cost coverage |

## Visual and interaction baseline

The shipped interface is documented in [`DESIGN.md`](../../DESIGN.md) as two instruments on one foundation: a calm, spacious storefront and a dense operations console, both reading the same semantic colour tokens.

The storefront is a cool neutral canvas with white product cards, a 264px filter rail, a three-column product field, and one operating blue reserved for actions and current location. Green, red, and amber carry state and nothing else, always beside a written label.

Comparison is the signature interaction, and it is a dock rather than a permanent column: selecting a product raises a bar at the foot of the catalog showing what is inside, which expands into a drawer holding the aligned attribute matrix. The previous design reserved a permanent 344px column for comparison, which cost 21% of the desktop width while empty; the dock costs nothing until it is needed.

Product imagery and prices in comps are synthetic. Shipping UI must use generated/public licensed assets with provenance and label demonstration records where a visitor could mistake them for real inventory.

## Accessibility and internationalization

- WCAG 2.2 AA contrast and semantics; logical DOM order must work in both directions.
- Locale switches set `lang` and `dir`; mixed technical tokens use direction isolation.
- All icons have names or adjacent visible labels. Color is paired with text/status shape.
- Comparison tables expose row/column headers; responsive labeled rows preserve associations.
- Search, filters, cart, checkout, assistant, dashboards, and back-office tables are keyboard operable.
- Live status uses restrained `aria-live`; validation errors identify the field and recovery.
- Motion observes `prefers-reduced-motion`; no required information depends on animation.
