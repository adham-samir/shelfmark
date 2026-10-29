# Stage 2 data architecture and Stage 3 catalog slice

Status: the physical schema, validators, seeds, and API design are verified. The Stage 3 service implements catalog, commerce, SF-01–03, the BO-01 forecast/reorder workflow, the BO-02 pricing workflow, BO-03 RFM segmentation snapshots, BO-04 trained risk assessments with audited review decisions, and BI-01 analytics aggregates. Stage 3 is complete except for live OpenAI provider proof.

The data layer supports the full planned commerce and smart-module baseline. This does not claim that order, payment, risk, forecasting, pricing, segmentation, or model behavior is implemented at the application layer.

## Ownership

| Field/data | Authority | Implemented design artifact |
|---|---|---|
| Stable product ID and lifecycle | PostgreSQL `product_registry` | `database/relational/migrations/0001_product_foundation.sql` |
| Product name, description, categories, attributes, images, provenance | MongoDB `products` | `database/catalog/product.schema.json` and `setup.js` |
| Current monetary amount and currency | PostgreSQL `product_prices` | Migration 0001 |
| On-hand, reserved, available stock | PostgreSQL `inventory_balances` | Migration 0001; available is generated from on-hand minus reserved |
| Historical applied prices / order price snapshots | PostgreSQL `price_changes`, `order_items` | Migration 0002; order snapshots use exact amounts and generated line totals |
| Customer/access/cart/order/payment/risk/shipment records | PostgreSQL tables of the same domain names | Migration 0002 with ownership, scope, state-value, and payment-token constraints |
| Demo credentials and sessions | PostgreSQL `account_credentials`, `sessions`, `account_principals.login_email` | Migration 0008 with argon2id hashes, SHA-256 session digests, sliding expiry, and a customer/operator surface-mapping trigger (DEC-017) |
| Browsing, forecast, reorder, RFM and evaluation records | PostgreSQL `browsing_events`, `demand_forecasts`, `reorder_records`, `rfm_snapshots`, `evaluation_runs` | Migration 0002 baseline; migrations 0004 and 0006 extend model and reorder evidence, audit inputs, policy snapshots, and dispatch attempts |

The MongoDB validator rejects top-level price/stock/lifecycle fields. There is no writable duplicate operational source. API responses compose both stores.

## Identity and publication contract

The application generates a UUID once. PostgreSQL stores it as `uuid`; MongoDB stores its canonical lowercase text as `_id`; APIs use that same text as `product_id`. Native keys enforce uniqueness within each store. Cross-store identity checks belong to application/reconciliation code; neither database can enforce a foreign key into the other.

Publication workflow contract:

1. Create the PostgreSQL registry row as `draft`.
2. Create the MongoDB document with the same ID; retries compare existing identity rather than generating another ID.
3. Add explicit current price/currency and inventory balance in PostgreSQL. Missing rows must not be treated as zero price/stock.
4. Verify catalog validation, identity, and all required operational records; then mark the registry row `active`.
5. On failure leave it `draft`, report it, and retry/reconcile. Draft/archived records are excluded from public reads. Archive by lifecycle rather than deleting IDs needed for future historical orders.

The migrations provide the storage primitives, not the publication write workflow. Direct database writes can produce an incomplete active product, so the implemented reads detect missing counterparts and fail with `503`; a later reconciliation job must audit and repair them. MongoDB setup does not retroactively clean invalid existing documents; an existing deployment must audit them before rollout.

## Catalog read contract

`GET /v1/products` and `GET /v1/products/{product_id}` are specified in [the OpenAPI contract](../api/README.md).

- Only `active` registry products are public.
- Text search initially matches literal, case-insensitive substrings in names/descriptions; category matching is exact. Image/voice search and dynamic facets will receive separate contracts for SF-03.
- Apply catalog filters and registry lifecycle eligibility before computing total and pagination. Sort by product ID for reproducibility.
- Read active products, prices, and inventory through one PostgreSQL query and descriptive records through one MongoDB query. Do not perform one query per product.
- Return stock status (`in_stock` when available > 0), not operational stock counts. Include price/availability observation timestamps.
- Missing required catalog or operational records, or a database outage, produce a structured `503 dependency_unavailable`; do not invent data or quietly omit an otherwise eligible product. An empty successful result means no eligible matches.
- A draft/archived/unknown product detail request returns `404 product_not_found`. An active product missing its counterpart returns `503`.
- Detail reads begin with a PostgreSQL lifecycle lookup. List reads detect missing catalog counterparts as part of active-product integrity checks; matching only MongoDB candidates would otherwise hide such gaps. The current fixture-scale implementation composes the active set before filters/pagination; indexed search projection is required before the 100,000-product target.
- There is no distributed snapshot across stores. Descriptions may change between reads; price/stock are revalidated during checkout. This contract does not promise a price lock or stock reservation policy.

## Storage semantics

- PostgreSQL prices use exact `numeric(20,6)`; nonfinite and negative values are rejected. The precision is a storage envelope, not a currency-rounding rule. Application validation must reject excess precision before PostgreSQL can round it.
- APIs serialize amounts as decimal strings to avoid binary floating-point conversion. Currency is explicit and has no production default; uppercase format validation alone is not a full supported-currency policy.
- A price or stock update must increment `version` and set `updated_at` in the same transaction. These are caller obligations for the future write layer, not trigger guarantees in this migration.
- Timestamps are instants; applications use UTC for transport. Store presentation uses `Africa/Cairo` under DEC-005.
- Inventory represents one nonnegative balance per product, with reserved <= on-hand. Multi-location stock and backorder commitments are outside this increment and require explicit design if needed.
- Descriptive attributes start as strings to support consistent filtering. Numeric/unit-aware attributes can be added with a versioned migration once product categories are known.
- Images store HTTPS references only. URL validation does not establish trust or image safety; media upload/storage and retrieval allowlists are deferred. Tests use reserved `.invalid` URLs and do not download images.

## Apply against a development database

Supply explicitly selected local database URLs. Do not use production databases for development validation.

```bash
psql "$ECOMMERCE_POSTGRES_URL" -v ON_ERROR_STOP=1 -f database/relational/migrations/0001_product_foundation.sql
psql "$ECOMMERCE_POSTGRES_URL" -v ON_ERROR_STOP=1 -f database/relational/migrations/0002_commerce_foundation.sql
psql "$ECOMMERCE_POSTGRES_URL" -v ON_ERROR_STOP=1 -f database/relational/seeds/0001_synthetic_demo.sql
mongosh "$ECOMMERCE_CATALOG_URL" --file database/catalog/setup.js
mongosh "$ECOMMERCE_CATALOG_URL" --file database/catalog/seed.synthetic.js
```

Migrations 0001–0012 are ordered, transactional, and applied once; the Docker setup applies them in filename order. Migration 0003 adds checkout controls, 0004 recommendation evidence, 0005 required shipment contact, 0006 BO-01 audit and dispatch-attempt evidence, 0007 BI-01 aggregate indexes, 0008 demo credentials/sessions and the surface-mapping trigger, 0009 the `orders:read` capability for operator order reads, 0010 the `orders:write` capability, the append-only `order_adjustments` table, and the acting operator on shipment events, 0011 the optional canonical `reason_code` on those adjustments, and 0012 `customer_addresses`, whose partial unique index allows one default per customer. Orders never read that table: each keeps its own shipping snapshot. A repeat fails atomically. MongoDB setup is repeatable and updates validator/index definitions without deleting records; the synthetic MongoDB seed is an upsert. Changes to deployed schemas must use subsequent migrations. No rollback/drop script is supplied.

The category/index design supports exact category lookup; text substring search is not yet optimized. Use [the repository verification command](../../README.md#verify-this-increment) to test against fresh disposable databases.

## Retention, access, and remaining work

The schema stores the designed customer, interaction, commerce, shipment, payment-risk, audit, model-evidence, credential, and session records. Customer ownership, the implemented `risk:review` and `inventory:write` back-office capabilities, and the separate customer/operator session surfaces are enforced by the local demo identity boundary (DEC-017). DEC-015 prohibits private production data in this project baseline, and database credentials, operator tokens, and session tokens are never sent to browser clients.

Next Stage 3 increment: BO-02 dynamic pricing against the shared operational records, followed by BO-03, trained BO-04, and BI. S3 remains the planned production store for uploaded images and model artifacts; local filesystem substitution and AWS service placement are deployment work. The Figma file remains pending external access, while the repository contains the approved composition and complete interaction specification.

## References used for this design

- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [MongoDB JSON Schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/specify-json-schema/)
- [OpenAPI 3.1 specification](https://spec.openapis.org/oas/v3.1.0.html)
