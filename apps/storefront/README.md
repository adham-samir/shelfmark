# Storefront (Next.js)

Customer-facing Smart-eCommerce storefront: Arabic-first, RTL, with English LTR parity.

The implemented visual system is documented in [`DESIGN.md`](../../DESIGN.md), with the schema-version-2 machine-readable sidecar at [`.impeccable/design.json`](../../.impeccable/design.json).

## Stack

Next.js 16.4.3 (App Router), React 19.3.1, Tailwind CSS 4.3.3, TypeScript 7.0.2. All API access happens on the Next.js server. Customer and operator sessions are held in `httpOnly` cookies; the browser never receives a bearer token.

## Run

```bash
npm install
npm run dev          # http://127.0.0.1:3000
npm run typecheck
npm run build && npm run start -- --port 3001
```

The API must be reachable (default `http://127.0.0.1:8000`). Environment overrides:

| Variable | Default | Purpose |
|---|---|---|
| `SMART_ECOMMERCE_API_URL` | `http://127.0.0.1:8000` | FastAPI base URL. |
| `SMART_ECOMMERCE_COOKIE_SECURE` | unset | Set to `1` to add `Secure` to both session cookies (requires HTTPS). |
| `SMART_ECOMMERCE_SANDBOX_TOKEN` | unset | Optional legacy customer bearer for scripts; the storefront authenticates through the session cookie instead. |
| `SMART_ECOMMERCE_OPERATOR_TOKEN` | unset | Optional legacy operator bearer for scripts; the back office uses the operator session cookie instead. |

Demo accounts are seeded in `database/relational/seeds/0001_synthetic_demo.sql`:
`customer@example.invalid` / `demo-customer-1`,
`other-customer@example.invalid` / `demo-customer-2`, and
`operator@example.invalid` / `demo-operator-1`. See DEC-017: this is a labelled
demo identity harness, not a production provider.

## Routes

| Route | Purpose |
|---|---|
| `/` | Catalog workbench: search, dynamic facets, combined filters, sort, paging, grid/list. |
| `/login`, `/register` | Customer sign-in and open demo registration, with guarded `next` redirects. |
| `/account`, `/account/orders` | Profile (display name + locale) and paged order history; requires a customer session. |
| `/products/[id]` | Detail, attributes, availability, SF-01 recommendations. |
| `/compare?ids=…` | Side-by-side comparison of selected products. |
| `/cart` | Cart with quantity changes and removal; requires a customer session. |
| `/checkout` | Shipping address and risk-gated sandbox checkout; requires a customer session. |
| `/orders/[id]` | Owned order status and shipment events; requires a customer session. |
| `/assistant` | Grounded assistant chat (SF-02); requires a customer session. |
| `/search/image` | Upload-based visual search (SF-03). |
| `/search/voice` | Microphone voice search (SF-03). |
| `/backoffice/login` | Operator sign-in, outside the back-office gate. |
| `/backoffice` | Operator overview with pending-review, stale-pricing, reorder-failure, and snapshot cards. |
| `/backoffice/inventory` | BO-01 stock, forecast, reorder-policy evidence, supplier status, and manual daily run. |
| `/backoffice/pricing` | BO-02 current price, latest inputs and freshness, proposal, applied-change audit, DEC-009 policy evidence, and observation import. |
| `/backoffice/segments` | BO-03 RFM reference date, segment counts, paged members with R/F/M values and scores, policy matrix, and CSV export through a server-only route. |
| `/backoffice/risk` | BO-04 review queue with model score, outcome, model version, reasons, and audited allow/decline actions; model card with threshold, holdout metrics, features, and limitations. |
| `/backoffice/analytics` | BI-01 consumer-behaviour and financial dashboards with date/category filters, daily trend, top products, source reconciliation, metric definitions, and profit omission. |

Product and order pages resolve their entity in `generateMetadata` through request-memoised reads (`lib/data.ts`), so missing or foreign records return a real HTTP 404 instead of a soft 200. Catalog routes keep a loading skeleton in `app/(catalog)/loading.tsx`; detail routes deliberately have no loading boundary so the 404 status is not committed early by streaming.

## Data freshness

Every server API read uses `cache: "no-store"` (`lib/api.ts`). Catalog price and availability are authoritative and must never be served from a stale cache.

## States

Loading, empty, error, invalid-upload, microphone-denied, and provider-missing states are implemented. BO-01 additionally exposes forecast-missing, supplier-failure, and permission failures through the shared error boundary; BO-02 exposes fresh/stale/missing inputs, would-update/unchanged/constraint-blocked proposals, and import validation; BO-03 exposes no-snapshot, stale-snapshot, empty-segment, and insufficient-history states; BO-04 exposes an empty queue, decision conflicts, and a missing-model state while keeping the queue usable; BI-01 exposes no-events, no-eligible-orders, empty-category, mismatch, and profit-omitted states. Assistant and voice search return the provider-missing state until a real `OPENAI_API_KEY` reaches the API service; that live-provider proof remains pending.

## Limitations

- Product plates are synthetic demonstration assets and are labeled as such in the UI.
- The catalog composes the active fixture set (13 synthetic products) before filtering/pagination; indexed search is required before the 100,000-product target.
- The approved comp `.impeccable/mocks/comp-a.png` is LTR while this storefront is deliberately Arabic-first RTL. The user accepted preserving the RTL composition as a documented visual exception. The recorded 58.53% comparison did not pass its original 72% numerical target and is not represented as having done so.
- BO-01 uses the operator session cookie for local demonstration. The demo identity harness (DEC-017) is not a production identity provider; production deployment still requires a reviewed provider, TLS, secret rotation, and revocation policy.
- BO-02 uses imported synthetic competitor costs (DEC-007) and a synthetic dated season calendar; the interface verifies policy behavior, not real pricing quality.
- BO-03 uses synthetic order history; the interface verifies RFM calculation and policy behavior, not segmentation quality on real customers.
- BO-04 is trained on a synthetic generator over checkout-observable signals; its metrics verify pipeline, threshold, and policy behavior, not real fraud-detection quality.
- BI-01 reads synthetic browsing events and seeded orders; it verifies calculation, filtering, and reconciliation, not commercial performance.
