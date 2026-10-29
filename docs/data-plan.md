# Data Availability and Provenance Plan

## 1. Provenance classes

| Class | Meaning | Permitted claim |
|---|---|---|
| Real | Lawfully obtained operational data for this store/domain | May support production-relevant evaluation only within documented representativeness and consent limits. |
| Public | Externally published dataset with recorded source/license/version | May support research evaluation; domain transfer limitations must be stated. |
| Synthetic | Generated fixtures or simulated histories | May verify pipelines, calculations, and controlled scenarios; does not prove real-world model quality. |
| Sandbox | Records produced by a provider's non-production environment | May verify integration behavior within sandbox limits; is not evidence of live processing. |

Every dataset snapshot must record: owner/source, class, acquisition date, license/consent basis, schema/version, preprocessing, time range, known bias/limitations, retention, access, and the models/tests that use it.

## 2. Data inventory

| Data area | Minimum fields/purpose | Candidate provenance | Availability | Requirements |
|---|---|---|---|---|
| Catalog content | Stable product ID, description, category, attributes, image references | Public/synthetic | Thirteen-product synthetic demonstration seed; no private data | SF-01, SF-02, SF-03 |
| Product images | Product ID, image URI/hash, media metadata | Public/synthetic | Public licensed or generated synthetic assets only | SF-03, SF-01 |
| Browsing events | Customer/session ID, product ID, event type, timestamp, context | Real/synthetic | No repository data | SF-01, BI-01, COM-06 |
| Purchases/orders | Customer/order/product IDs, event times, status, quantity, price snapshot, currency | Real/public/synthetic | No repository data | SF-01, BO-01, BO-03, BI-01 |
| Inventory | Product ID, balance, movement, timestamp, pending replenishment | Real/synthetic | Synthetic current balances, movements, forecast, and supplier-simulator reorder evidence | BO-01, BO-02 |
| Demand history | Product/time bucket and eligible demand quantity | Derived from real/public/synthetic orders | Deterministic 210-day synthetic chronology for 13 products; explicitly pipeline-only | BO-01, BO-02 |
| Competitors' costs | Competitor/source identity, product mapping, value, currency, observed time | Synthetic/manual import | Demonstration feed only under DEC-007 | BO-02 |
| Shopping seasons | Season ID, time boundaries, locale/domain meaning | Project configuration | Ramadan/Eid, back-to-school, year-end baseline in `services/api/data/pricing_seasons.json` | BO-02 |
| RFM inputs | Customer/order date, status, net eligible monetary value | Derived from orders | Implemented by BO-03 as a rolling 365-day calculation over paid/completed orders net of refunds, with versioned daily snapshots | BO-03 |
| Browsing behaviour | Event ID, session, optional customer, product, event type, timestamp, provenance | Synthetic demonstration activity | 9,000 deterministic events over 90 days across 2,251 sessions, 30% anonymous | BI-01, SF-01 |
| Order line items | Order, product, name snapshot, quantity, historical unit price, generated line total | Derived from orders | 1,021 deterministic lines whose totals reconcile exactly to their order subtotals | BI-01, COM-04 |
| Payment risk | Tokenized/sandbox transaction attributes, labels, assessment result | Public/sandbox/synthetic | Deterministic synthetic generator over checkout-observable signals plus a trained, evaluated model artifact; no live credentials or card-network data | BO-04 |
| Shipment status | Authorized customer/order, carrier reference, status, event time | Sandbox/synthetic | Shipment simulator until a provider is selected | SF-02, COM-05 |
| Identity and sessions | Principal ID, account type, login email, preferred locale, password hash, session token digest, surface, expiry | Synthetic demo credentials | Three seeded demo accounts (`customer@example.invalid`, `other-customer@example.invalid`, `operator@example.invalid`); argon2id password hashes and SHA-256 session digests; no production identity data | COM-07 |
| Inquiry knowledge | Approved FAQ/policies/product facts with effective dates | Project-authored/synthetic | Versioned bilingual FAQ plus catalog facts | SF-02 |
| Price history | Product ID, old/new price, inputs, calculation/model version, applied time | Generated operational data | Immutable `price_changes` rows written by BO-02 with the complete `dec-009-v1` input snapshot | BO-02, BI-01 |
| Model/evaluation records | Dataset/code/config/artifact versions and metrics | Generated metadata | Physical schema plus trained synthetic SF-01, SF-03, and BO-01 evidence; other modules pending | All AI modules |

## 3. Collection and ownership rules

1. MongoDB owns descriptive catalog content and image references; the first physical validator is `database/catalog/product.schema.json`.
2. PostgreSQL is selected under **DEC-002**. Migrations 0001–0010 own operational commerce, interaction, audit, planning, model-evidence, checkout-idempotency, risk-review, recommendation evidence, shipment contact, BO-01 reorder-audit records, BI-01 aggregate indexes, the demo identity/session tables (DEC-017), the operator order read capability, and the audited order-lifecycle tables (`order_adjustments`, shipment-event actors); see [data architecture](architecture/data-foundation.md).
3. Browsing, shipment, inventory, pricing, and evaluation evidence uses append-oriented records. Order-item commercial snapshots are preserved independently from current prices; the application must prevent post-creation mutation.
4. Cross-store data uses one canonical UUID: native `uuid` in PostgreSQL and lowercase UUID text in MongoDB `_id` and APIs; no name-based joins.
5. Machine timestamps are UTC instants. The store displays them in `Africa/Cairo` under **DEC-005**.

## 4. Privacy, security, and retention

- Collect only data required by the listed journeys and modules.
- Document the consent/legal basis for behavioral data before using real browsing histories.
- Restrict order, shipment, and payment-risk data by customer ownership and back-office permission.
- Use provider tokens and sandbox values; never store card verification codes or seed real credentials.
- Demo credentials are labelled `.invalid` accounts with argon2id hashes; session tokens are stored only as SHA-256 digests and are revoked on sign-out. They are not production secrets and must be replaced by a real identity provider before deployment (DEC-017).
- Validate image type/content/size and isolate processing from executable content.
- Define retention/deletion periods and de-identification for training extracts before real data ingestion.
- Separate raw, prepared, training, validation, and test snapshots to prevent leakage.

## 5. Reproducibility and evaluation

Each training/evaluation run captures dataset snapshot IDs, chronological or group split rules, preprocessing version, random seed where applicable, feature definitions, model/config version, metrics, and artifact location. BO-01 enforces this baseline with earlier-date-only lag/rolling features and a final 28-day holdout. Time-dependent prediction must not use future information to predict the past.

Synthetic catalog and operational fixtures now exercise the catalog, commerce, SF-01/SF-03, and BO-01 slices. Later Stage 3 fixtures will cover the remaining smart modules. Reports label them `Synthetic` and restrict claims to behavioral/pipeline verification; credible real-world model-quality claims remain unavailable without representative data.

Stage 2 validation fixtures in `tests/data_foundation/` use dataset ID `schema-tests-v1`, reserved `.invalid` image URLs, and currency marker `XXX`. The separately labeled `stage3-catalog-v1` seed uses EGP and powers the Dockerized catalog demonstration. Neither dataset proves production model quality.
