# API contracts

[catalog.openapi.json](catalog.openapi.json) is the OpenAPI 3.1 contract for the catalog reads implemented in `services/api`.

| Method | Path | Purpose | Requirements |
|---|---|---|---|
| GET | `/v1/products` | List active products with text/category/dynamic-attribute filters and offset pagination | COM-01; SF-03 |
| GET | `/v1/products/facets` | Recompute category and attribute counts from the current result context | SF-03 |
| GET | `/v1/products/{product_id}` | Return one composed active product with current price/availability | COM-01; prerequisite for cart and assistant |

These are public read operations (`security: []`). Customer/order, identity, and back-office routes in the platform contract use explicit bearer sessions; the seeded credentials are a labelled demonstration harness, not a production identity mechanism (DEC-017). The legacy synthetic `identity_subject` bearer values remain accepted for tests and scripts.

Prices are decimal strings, product IDs are canonical UUID text, and timestamps use RFC 3339 with UTC output. Public product responses exclude internal provenance and stock counts. See [data architecture](../architecture/data-foundation.md) for publication, read, and cross-database consistency rules.

All errors have the shape `{ "error": { "code": "...", "message": "...", "request_id": "..." } }`. The FastAPI handlers normalize framework validation errors into this envelope. `request_id` is generated/validated by the server; messages do not expose database credentials, queries, or internal stack traces.

- `422 validation_error`: malformed ID/query, invalid limit/offset, or unsupported input shape.
- `404 product_not_found`: unknown, draft, or archived product.
- `503 dependency_unavailable`: required database or cross-store counterpart unavailable.
- `500 internal_error`: unexpected internal failure, with a generic public message.

SF-03 now composes these reads and facets with validated image upload/retrieval and recorded-audio transcription endpoints. The image baseline is explicitly synthetic and its evaluation does not establish production visual-search quality.

## Full platform design contract

[platform.openapi.json](platform.openapi.json) defines the Stage 2 HTTP boundaries for browsing events, recommendations, image/voice search, assistant messages, cart/checkout, demo identity/sessions, account and order history, customer-owned orders/shipments, and back-office inventory, reorder, pricing, RFM, risk, and BI operations.

### Demo identity and account operations

| Method | Path | Purpose | Session |
|---|---|---|---|
| POST | `/v1/auth/register` | Create an open demo customer account and return a session | Public |
| POST | `/v1/auth/login` | Verify `email`/`password` for `surface=customer` or `operator` and return a session | Public |
| POST | `/v1/auth/logout` | Revoke the presented session | Any |
| GET | `/v1/auth/me` | Resolve the presented session to its account view | Any |
| GET | `/v1/account` | Customer profile: display name, email, locale, member since, order count | Customer |
| PATCH | `/v1/account` | Update display name and preferred locale | Customer |
| POST | `/v1/account/password` | Rotate the password; ends every other session of the principal and keeps the caller signed in | Customer |
| GET | `/v1/orders` | Paged order history for the signed-in customer | Customer |
| POST | `/v1/orders/{order_id}/cancel` | Cancel an own order before it ships, from a fixed reason list plus free-text `other` | Customer |
| POST | `/v1/orders/{order_id}/reorder` | Add a past order's lines to the cart and report anything skipped | Customer |
| GET | `/v1/addresses` | Saved addresses, default first, with the book limit | Customer |
| POST | `/v1/addresses` | Save an address; the first becomes the default | Customer |
| PUT | `/v1/addresses/{address_id}` | Update an own address; the default can be moved but not cleared | Customer |
| DELETE | `/v1/addresses/{address_id}` | Delete an own address; a survivor is promoted to default | Customer |

Credentials are argon2id hashes in `account_credentials`; session tokens are stored only as SHA-256 digests with a seven-day sliding expiry. A password change requires the current password, rejects reuse of it, and revokes every other session of the same principal (`400 incorrect_password` when the current value is wrong). `python -m smart_ecommerce_api.migrate` applies the numbered SQL migrations once each, tracked by checksum in `schema_migrations`. `python -m smart_ecommerce_api.session_reaper` deletes expired rows and revoked rows older than 30 days; it runs as the `session-reaper` compose job. Responses carry `x-content-type-options`, `referrer-policy`, `x-frame-options`, `permissions-policy`, and a strict `content-security-policy` on every path except the interactive docs. Customer and operator sessions are independent, and the session-surface trigger rejects a mismatch. Ten failed logins per five minutes return `429 rate_limited`. Open registration is a demo choice; there is no email verification, password reset, MFA, or OAuth/OIDC claim.

Browsing-event capture, cart, checkout, owned order/shipment reads, trained pre-completion risk assessment and review, hybrid recommendations, grounded assistant orchestration, image/voice search, dynamic filtering, BO-01 inventory/reorder planning, BO-02 dynamic pricing, BO-03 RFM segmentation, BO-04 fraud detection, and BI-01 analytics are implemented through Stage 3 increment 10. BO-01–BO-04 and BI-01 replace their generic placeholders with typed results and require `inventory:write`, `pricing:write`, `segments:read`, `risk:review`, and `analytics:read` respectively. Operators read orders through the queue below with `orders:read` and act on them with `orders:write`. Every implementation preserves the shared error envelope and explicit authorization/ownership behavior.

### Operator order reads

| Method | Path | Purpose | Scope |
|---|---|---|---|
| GET | `/v1/backoffice/orders` | Paged every customer order with status, customer identity, subtotal, refund total, and item count; optional `status`, `limit`, `offset` | `orders:read` |
| GET | `/v1/backoffice/orders/{order_id}` | One order with customer, shipping contact, line items, and shipment events | `orders:read` |

The queue exists so an operator can locate the order behind a risk-queue row or a customer question instead of seeing confirmed orders only as analytics aggregates. Customer-owned reads remain `/v1/orders` and `/v1/orders/{order_id}`; an operator token still receives `403` there, and a customer token receives `403` on the back-office routes.

### Buy again

`POST /v1/orders/{order_id}/reorder` copies a past order's lines into the current
cart at **current** prices and availability, never the old snapshot. It answers
with `added[]` and `skipped[]`; a skip carries `product_inactive`,
`price_unavailable`, `out_of_stock`, or `quantity_capped`, so nothing disappears
silently. Quantities accumulate with what is already in the cart and are capped
at the smaller of availability and the 99-per-line limit.

### Saved addresses

The book holds at most ten addresses per customer and exactly one default,
enforced by a partial unique index. The first saved address becomes the default
even when the request does not ask for it, deleting the default promotes the
oldest survivor, and clearing the default outright is refused (`409`) — the
supported move is to promote another address. Checkout preselects the default and
offers an opt-in save; a full book never turns a successful checkout into an
error, because the order is reported first and the save outcome separately.
Orders never read this table: each keeps its own frozen shipping snapshot, so
editing or deleting an address cannot rewrite history.

### Customer cancellation

`POST /v1/orders/{order_id}/cancel` accepts one of `changed_mind`,
`ordered_by_mistake`, `wrong_item`, `found_cheaper`, `delivery_too_slow`, or
`other`. Fixed codes are expanded to canonical English text in
`order_adjustments.reason` so reporting stays countable; `other` stores the
customer's own words and is rejected when they are missing (`422 invalid_input`).
The route is ownership-scoped, so another customer receives `404`, and it shares
the operator cancellation path: stock is restored only from the order's own
`sale` movements, the sandbox payment is voided, the shipment becomes
`exception`, and the adjustment records the customer principal. An order that has
shipped returns `409`.

### Operator order lifecycle

| Method | Path | Purpose | Scope |
|---|---|---|---|
| POST | `/v1/backoffice/orders/{order_id}/shipment` | Advance the shipment: `ready`, `in_transit`, `delivered`, or `exception` | `orders:write` |
| POST | `/v1/backoffice/orders/{order_id}/cancel` | Cancel an order that has not shipped; restores only the stock it consumed | `orders:write` |
| POST | `/v1/backoffice/orders/{order_id}/refund` | Record a partial or full refund against the remaining total | `orders:write` |
| POST | `/v1/backoffice/inventory/{product_id}/adjustments` | Record an audited stock adjustment | `inventory:write` |

Transitions are an explicit state machine: `pending → ready → in_transit → delivered`, with `exception` reachable from the three open states and resumable to `ready`. Any other move returns `409 conflict`. `in_transit` and `delivered` also move the order to `shipped` and `delivered`. Cancellation is refused once a shipment is delivered, records an `order_adjustments` row, voids the sandbox payment, and inserts `release` movements only for `sale` movements the order actually produced — seeded historical orders predate that ledger and therefore restore nothing. A refund never changes the subtotal: it accumulates in `refund_total`, flips the order to `refunded` only when the whole total is returned, and is rejected if it exceeds the remainder. Every transition, cancellation, refund, and adjustment stores the acting operator principal.

### BO-02 pricing operations

| Method | Path | Purpose | Scope |
|---|---|---|---|
| GET | `/v1/backoffice/pricing` | Current price, latest observation, freshness, proposal, last applied change, season, policy, and audit trail | `pricing:write` |
| POST | `/v1/backoffice/pricing/observations` | Import recorded cost, supply, demand, and competitor cost for an active product (`synthetic`/`sandbox`/`public` provenance) | `pricing:write` |
| POST | `/v1/backoffice/pricing/run` | Apply the DEC-009 calculation; optional `product_ids` limits the run | `pricing:write` |

One observation produces at most one price change, so retries of the daily job are idempotent. Prices are bounded to ±20% per run and never below recorded cost + 5%; stale (over 24 hours) or future-dated observations block an update and are reported. Applied changes persist an immutable `price_changes` row with the complete input snapshot and `dec-009-v1` calculation version. Storefront reads compose the updated authoritative price from PostgreSQL; completed orders keep their `unit_price_snapshot`.

### BO-03 segmentation operations

| Method | Path | Purpose | Scope |
|---|---|---|---|
| GET | `/v1/backoffice/segments` | RFM snapshot, segment counts, insufficient-history count, policy, and paged members; optional `segment`, `reference_date`, `limit`, `offset` | `segments:read` |
| POST | `/v1/backoffice/segments/run` | Recalculate the reference-date snapshot from eligible order history | `segments:read` |
| GET | `/v1/backoffice/segments/export` | Selected newest snapshot as CSV, optionally filtered by `segment` | `segments:read` |

The calculation uses a rolling 365-day window and scores recency, frequency, and monetary value in independent quintiles; tied values share a score. One ordered, first-match-wins rule set maps all 125 score combinations to the six DEC-011 segments. Recalculation replaces only the current reference date, so older snapshots remain available. Customers without eligible history are reported and never assigned invented values. CSV cells that could start a spreadsheet formula are neutralized with a leading apostrophe.

### BO-04 risk operations

| Method | Path | Purpose | Scope |
|---|---|---|---|
| GET | `/v1/backoffice/risk` | Pending review queue with score, outcome, model version, and reasons | `risk:review` |
| GET | `/v1/backoffice/risk/model` | Model card: version, threshold, holdout metrics, features, limitations | `risk:review` |
| POST | `/v1/backoffice/risk/{assessment_id}/decision` | Audited `allow`/`decline` disposition for a review assessment | `risk:review` |

Assessment happens inside checkout before any completion transition. Ordinary payments are scored by the trained model; forced `risk-high`/`risk-fail` sandbox tokens keep deterministic demo behavior. A missing artifact, inference error, or evidence failure returns `assessment_failed`, which routes to review. Decimal scores are serialized as strings; reasons are signal names, not proof of stolen credentials.

### BI-01 analytics

| Method | Path | Purpose | Scope |
|---|---|---|---|
| GET | `/v1/backoffice/analytics` | Consumer-behaviour and financial metrics, daily series, top products, and reconciliation for `from`/`to` and an optional `category` | `analytics:read` |

Conversion is created orders divided by sessions with at least one event in the range; anonymous sessions remain in the denominator. Without a category, revenue uses the authoritative order subtotal; with a category, revenue is the item-line value of the matching products and refunds are allocated by that item share. Ranges are inclusive and capped at 366 days (`422` otherwise). Every response carries reconciliation checks that recompute values independently from order-item lines, and profit is never reported because the project holds no complete cost coverage.
