# Decision Register

No option below is selected merely by appearing first. `Pending` entries must be resolved before their dependent implementation claims completion.

| ID | Decision | Allowed/current options | Why needed | Dependent work | Status |
|---|---|---|---|---|---|
| DEC-001 | Main backend | Python + FastAPI | Keep business APIs and AI integration in Python | API scaffold, service architecture | Accepted — 2026-10-27 |
| DEC-002 | Relational database | PostgreSQL for operations; MongoDB for the product catalog | Transactional records and separate descriptive catalog | Schema, migrations, local/deployment setup | Accepted — 2026-10-27 |
| DEC-003 | ML framework/responsibilities | Python + Scikit-learn for baseline models; PyTorch for image features/advanced models; OpenAI API for the assistant | Assign responsibilities within the supplied stack | Model pipelines and assistant | Accepted — 2026-10-27 |
| DEC-004 | Hosting placement | Docker on AWS; one Next.js application, modular FastAPI backend, separate job execution as needed | Support application and model/background workloads | Deployment architecture | Platform accepted — 2026-10-27; AWS service sizing/placement pending |
| DEC-005 | Product context | Egyptian consumer electronics; Arabic and English; EGP; `Africa/Cairo` display timezone | Needed for concrete UI/data semantics | Copy, catalog, money/date logic | Accepted — 2026-10-27 |
| DEC-006 | Permission grouping | Customer or back-office principal, with capability scopes rather than a large role tree | Enforce least privilege while keeping the hierarchy minimal | Authentication/authorization | Accepted — 2026-10-27 |
| DEC-007 | “Competitors' costs” meaning/source | Preserve the literal source wording; synthetic/manual import for the project demonstration | Avoid changing source meaning while no real source exists | BO-02 pricing inputs | Accepted — 2026-10-27 |
| DEC-008 | Inventory policy | Daily 14-day forecast; 7-day lead time; 7-day safety stock; reorder to 21-day cover; idempotent supplier simulator | Makes the automatic reorder demonstration reproducible | BO-01 | Accepted — 2026-10-27 |
| DEC-009 | Pricing policy | Daily calculation; required inputs must be fresh; no update on missing input; at most 20% change per run and never below recorded cost plus 5% | Reproducible and bounded automatic pricing | BO-02 | Accepted — 2026-10-27 |
| DEC-010 | Payment/fraud policy | Tokenized sandbox/simulator; score ≥0.70 or assessment failure sends checkout to review; no order completion before assessment | Defines pre-completion handling without storing card secrets | Checkout and BO-04 | Accepted — 2026-10-27 |
| DEC-011 | RFM policy | Rolling 365 days; paid/completed orders minus refunds; quintile scores; six documented segments | Repeatable customer classification | BO-03 | Accepted — 2026-10-27 |
| DEC-012 | Assistant/search methods | Approved FAQ + catalog + own shipment records; OpenAI API assistant/voice transcription; PyTorch image embeddings; shipment simulator | Concrete integration boundaries within the selected stack | SF-02, SF-03 | Accepted — 2026-10-27 |
| DEC-013 | BI metric contracts | Product views, conversion, order count, gross/net sales, refunds, average order value; date/category filters; no profit without cost coverage | Concrete consumer/financial analysis | BI-01 | Accepted — 2026-10-27 |
| DEC-014 | Quality targets/workload | WCAG 2.2 AA; performance and model thresholds in SRS §7; demo workload up to 10 requests/s and 100 concurrent sessions | Measurable acceptance where source has no values | Acceptance and QA | Accepted baseline — 2026-10-27; revise with representative data |
| DEC-015 | Data availability | No private data/credentials; public, synthetic, and sandbox sources only, labeled by provenance | Honest development/evaluation scope | All AI modules | Accepted current-state constraint — 2026-10-27 |
| DEC-016 | Delivery constraints | Incremental single-repository build; no source deadline/team-size assumption; presentation format remains pending until Stage 5 | Avoid fabricated calendar commitments | Planning and final presentation | Accepted — 2026-10-27 |
| DEC-017 | Demo identity/session boundary | Local demo credentials (argon2id) with revocable database sessions; separate customer and operator surfaces; no production IdP, OAuth, email verification, password reset, or MFA | The customer storefront and the operator back office both need sign-in without claiming a production identity provider | Storefront authentication, account pages, back-office gate | Accepted demonstration scope — 2026-10-28 |
| DEC-018 | Operator order lifecycle | Read-then-write operator access to orders under `orders:read` and `orders:write`: a fixed shipment state machine, pre-delivery cancellation that restores only consumed stock, bounded partial/full refunds that never change the subtotal, and audited stock adjustments under `inventory:write`. Customer pages carry no back-office affordance. | An operator could see orders but could not fulfil, cancel, refund, or correct stock, and a customer banner linked into the operator surface | COM-08, COM-09, back-office orders and inventory | Accepted — 2026-10-29 |

## Accepted stack — 2026-10-27

**Approved by:** user response “alright let's do it” to the proposed stack.

- **Frontend:** Next.js, React, Tailwind CSS in one application containing storefront and back-office areas.
- **Backend:** Python + FastAPI as one modular application initially. Worker execution can share domain code while running separately.
- **Data:** PostgreSQL owns operational records; MongoDB owns descriptive product catalog records.
- **AI:** Scikit-learn for baseline recommendation, forecast, and fraud models; PyTorch for image features and advanced models when justified; OpenAI API for grounded assistant responses. RFM remains a reproducible calculation.
- **Delivery:** Docker and AWS. Exact AWS services, resource sizing, and deployment credentials are deferred to deployment design.

This resolves DEC-001–003 and the platform portion of DEC-004. DEC-005–017 below resolve the product context, business-policy, data, identity, and acceptance baselines needed for implementation. Library/runtime versions are pinned as each runtime is introduced and tested.

## Product and policy baseline — 2026-10-27

The user instructed the agent to proceed after being offered the product defaults. DEC-005–017 therefore use the concrete project defaults above. They are implementation decisions, not claims that the original photos supplied these details.

- Back-office authorization uses scopes such as `catalog:write`, `inventory:write`, `pricing:write`, `risk:review`, `segments:read`, and `analytics:read`. Customer access remains ownership-scoped.
- Demonstration seasons are Ramadan/Eid, back-to-school, and the year-end shopping period. Dates are configuration records, not hard-coded model knowledge.
- RFM segments are Champions, Loyal, Potential, New, At Risk, and Hibernating, derived from documented quintile combinations.
- AWS S3 is the planned store for uploaded search images and model artifacts. Local development uses a documented filesystem substitute; application databases store references and hashes.
- Demo retention is 365 days for browsing events and risk detail. Orders, price snapshots, and audit records remain for the project dataset. Production retention requires legal/operational review before real data ingestion.

## Data foundation engineering choices — 2026-10-27

Recorded within the authorized Stage 2 design work:

- Product identity is an application-generated UUID, serialized as canonical lowercase text in MongoDB `_id` and APIs, and stored as native PostgreSQL `uuid`.
- PostgreSQL owns lifecycle, current price, and inventory balance. MongoDB contains neither duplicated prices/stock nor a separate publication flag.
- Initial storage supports one inventory balance per product and one current price/currency per product. Currency has no production default; the test code uses `XXX` (no currency) only for synthetic fixtures.
- Monetary storage uses exact `numeric(20,6)` and APIs use decimal strings. EGP presentation/rounding, taxes, and checkout price-lock behavior must be finalized with the checkout implementation; dynamic-price limits are fixed by DEC-009.
- UTC instants are used for machine timestamps; presentation uses the `Africa/Cairo` baseline from DEC-005.
- Initial product lifecycle uses `draft`, `active`, and `archived`. Publication and reconciliation checks belong to the future application layer; no database-to-database foreign key is claimed.

See [data architecture](architecture/data-foundation.md) for ownership, publication, and consistency contracts.

## BO-02 implementation record — 2026-10-27

Decision ID: IMP-BO02-01  
Date: 2026-10-27  
Status: Accepted  
Selected option:
- Calculation: `price = current × (1 + 0.15 × demand balance) × (1 + 0.10 × competitor balance) × season multiplier`, where `demand balance = clamp((demand − supply) / max(demand, supply), −1, 1)` and `competitor balance = clamp((competitor cost − recorded cost) / max(recorded cost, 1), −1, 1)`.
- Bounds: clamp the proposal to ±20% of the current price, then apply the recorded-cost + 5% floor as a lower bound. A floor above the permitted increase blocks the change instead of violating either rule.
- Currency rounding: EGP prices round to `0.01` (half-up) after bounding; bounds are re-checked after rounding. Storage remains exact `numeric(20,6)`.
- Freshness: an observation older than 24 hours, or timestamped in the future, is reported as stale and cannot change the price.
- Idempotency: each observation can produce at most one price change; reruns report `already_applied`. This keeps the daily job retry-safe.
- Seasons: dated windows and multipliers are configuration in `services/api/data/pricing_seasons.json`, not model knowledge.
- Inputs: observation import accepts `synthetic`, `sandbox`, or `public` provenance only; competitors’ costs remain imported synthetic values under DEC-007.

Rationale: makes DEC-009 reproducible and auditable without inventing a real competitor feed or a commercial season calendar.  
Consequences: the demonstration does not establish real pricing quality; a production competitor-cost feed and commercial season calendar remain external dependencies.  
Approved by: continuation of the user-approved Stage 3 plan, where BO-02 was the recorded next increment.  
Evidence/link: `services/api/src/smart_ecommerce_api/pricing.py`, `services/api/tests/test_pricing.py`, `tests/integration/test_commerce_api.py`, and [traceability](requirements-traceability.md).

## BO-03 implementation record — 2026-10-27

Decision ID: IMP-BO03-01  
Date: 2026-10-27  
Status: Accepted  
Selected option:
- Eligibility: rolling 365-day window inclusive of the reference date (UTC run date); `confirmed`, `shipped`, `delivered`, and `refunded` orders with `subtotal - refund_total > 0`. Pre-completion and cancelled orders plus fully refunded orders are excluded.
- Quintile scoring: independent per dimension. Recency scores fewer days higher; frequency and monetary score higher values higher. Ties share a score computed from the empirical distribution (`ceil(better-or-equal count / cohort × 5)`, clamped 1–5). Cohorts smaller than five customers score neutrally at 3.
- Segment matrix, ordered and first-match-wins: Champions `R>=4 & F>=4 & M>=4`; Loyal `R>=3 & F>=3`; Potential `R>=4 & F<=2`; New `R=3 & F<=2`; At Risk `R<=2 & F>=3`; Hibernating `R<=2 & F<=2`. The rules are exhaustive over all 125 score combinations.
- Snapshots: one row per customer and reference date. Recalculation replaces that reference date transactionally, retains older dates, and reports customers without eligible history instead of inventing values. A snapshot is stale when its reference date precedes the current UTC date.
- Group selection: segment filter, paged member rows, and a CSV export of the selected newest snapshot. Exported text cells beginning with `=`, `+`, `-`, or `@` receive a leading apostrophe to prevent spreadsheet formula execution.
- Authorization: `segments:read` covers the overview, calculation, and export because the source scope list defines no segmentation write scope.
Rationale: makes DEC-011 reproducible, exhaustive, and auditable without adding schema or unapproved business rules.  
Consequences: the synthetic order history verifies calculation and integration behavior, not real segmentation quality; the current seed leaves the “new” segment empty.  
Approved by: user-approved continuation of the Stage 3 plan, where BO-03 was the recorded next increment; the ordered matrix, 40-customer/≈480-order seed, and CSV group selection were confirmed in the planning session.  
Evidence/link: `services/api/src/smart_ecommerce_api/segmentation.py`, `services/api/tests/test_segmentation.py`, `tests/integration/test_commerce_api.py`, and [traceability](requirements-traceability.md).

## BO-04 implementation record — 2026-10-27

Decision ID: IMP-BO04-01  
Date: 2026-10-27  
Status: Accepted  
Selected option:
- Data: deterministic seeded synthetic generator (3,000 transactions, ~17% positives) over checkout-observable signals: amount versus the customer norm, new shipping address, token reuse, 24-hour order velocity, prior failed attempts, overnight order hour, high absolute amount, and first order. Stratified 60/20/20 train/validation/holdout; the holdout is reported once. No real payment, card-network, or device-fingerprint data is used.
- Models: scaled logistic regression baseline and histogram gradient boosting on the same 16-feature vector. The threshold is selected on validation to maximize recall subject to FPR <= 0.09 (a one-point margin under the 0.10 target) and clamped to at most 0.70 to honor DEC-010. The model with higher validation recall is selected; ties break on PR-AUC.
- Result: the logistic baseline was selected at threshold 0.6985 with sealed-holdout recall 0.833, FPR 0.078, precision 0.685, PR-AUC 0.854, and ROC-AUC 0.954. Gradient boosting reached 0.824 recall at 0.088 FPR on the holdout but lower validation recall; both are recorded in `artifacts/fraud.evaluation.json`.
- Serving: forced `risk-high` and `risk-fail` tokens keep deterministic demo behavior. Ordinary tokens use the model. A missing artifact or inference/evidence failure returns `assessment_failed`, which routes to review and never allows completion. The model/evaluation evidence is registered once per process; each assessment persists its `model_version_id`.
- Output: score, outcome, and human-readable feature flags. Reasons are signals, not proof that a card was stolen.
Rationale: makes BO-04 verifiable end-to-end with honest synthetic evidence while preserving the verified pre-completion policy.  
Consequences: the synthetic labels do not establish real fraud-detection quality; real deployment requires labeled provider data, calibration, monitoring, and threshold review.  
Approved by: user-approved increment 9 decisions (synthetic generator, baseline plus gradient boosting, forced tokens retained, risk page included).  
Evidence/link: `services/api/src/smart_ecommerce_api/fraud.py`, `services/api/ml/fraud/`, [model card](models/fraud.md), and [traceability](requirements-traceability.md).

## BI-01 implementation record — 2026-10-28

Decision ID: IMP-BI01-01  
Date: 2026-10-28  
Status: Accepted  
Selected option:
- Conversion: created orders divided by distinct sessions with at least one browsing event in the filtered range. Anonymous and non-converting sessions remain in the denominator; the label is “orders per session”.
- Financial eligibility: `confirmed`, `shipped`, `delivered`, and `refunded` orders. `cancelled` and `payment_failed` are reported separately as unfulfilled demand and excluded from revenue.
- Category scope: the catalog resolves the category to product identifiers; product behaviour and item-line revenue are restricted to those products. Order count is the number of distinct matching orders. Without a category, revenue uses the authoritative `orders.subtotal`; with a category, revenue is the item-line value of matching products and refunds are allocated by that item’s share of the order.
- Reconciliation: the API recomputes order count and total value independently from `order_items.line_total` and returns reported/recomputed pairs with a match flag. The seed derives each line price from its order subtotal, so a match is meaningful rather than trivially true.
- Rendering: server-rendered CSS bars with an orders marker; no charting dependency is added.
- Data: 9,000 deterministic browsing events over 90 days across 2,251 sessions (30% anonymous) and 1,021 order-item lines across the 518 seeded orders.
- Profit is never displayed because no complete cost coverage exists (DEC-013).
Rationale: satisfies OBJ-03/BI-01 with formulas that are computable from recorded data and independently checkable.  
Consequences: results verify calculation, filtering, and reconciliation on synthetic activity, not commercial performance.  
Approved by: user-approved increment 10 decisions (orders per session, CSS bars, server-side reconciliation, 9,000 events over 90 days).  
Evidence/link: `services/api/src/smart_ecommerce_api/analytics.py`, `services/api/tests/test_analytics.py`, `tests/integration/test_commerce_api.py`, and [traceability](requirements-traceability.md).


## Demo identity harness — 2026-10-28

Decision ID: DEC-017  
Date: 2026-10-28  
Status: Accepted demonstration scope  
Selected option:
- Credentials: `pwdlib[argon2]` (argon2id) hashes in `account_credentials`. Seeded demo values are printed in the user manual; they are not production secrets.
- Sessions: random 32-byte tokens stored only as SHA-256 digests in `sessions`, with a seven-day sliding expiry and explicit revocation on sign-out.
- Surfaces: customer and operator sessions are independent. Customer tokens resolve to customer principals; operator tokens resolve to `backoffice` principals. The database trigger rejects a mismatched surface.
- Cookies: two `httpOnly`, `SameSite=Lax` cookies (`smart_customer_session`, `smart_operator_session`). `SMART_ECOMMERCE_COOKIE_SECURE=1` adds `Secure` for an HTTPS deployment.
- Gating: catalog browsing is public; cart, checkout, assistant, account, orders, and the entire back office require the matching session. The back-office login page is outside the gate.
- Compatibility: the legacy `account_principals.identity_subject` bearer path remains available to tests and scripts. The storefront no longer uses fixed server-side bearer values.
Rationale: satisfies the requested separation of customer and operator surfaces with real password verification, revocation, expiry, and surface isolation while keeping the demonstration self-contained.  
Consequences: the harness is not a production identity implementation. It has no email verification, password reset, MFA, OAuth/OIDC, account lockout beyond a process-local login throttle, or multi-instance throttle coordination. Production deployment requires a selected provider, secret rotation, TLS, and a review of retention and abuse controls.  
Approved by: user request to add customer and operator authentication with a labelled demo identity harness.  
Evidence/link: `database/relational/migrations/0008_identity_sessions.sql`, `services/api/src/smart_ecommerce_api/identity.py`, `apps/storefront/lib/session*.ts`, `apps/storefront/lib/auth-actions.ts`, and `services/api/tests/test_api.py`.

## Operator order lifecycle — 2026-10-29

Decision ID: DEC-018  
Date: 2026-10-29  
Status: Accepted  
Selected option:
- Capabilities: `orders:read` (migration 0009) for the queue and detail; `orders:write` (migration 0010) for every mutation. A customer session never holds either.
- Fulfilment: one explicit state machine — `pending → ready → in_transit → delivered`, with `exception` reachable from the three open states and resumable to `ready`. Any other move is a `409`. `in_transit` and `delivered` also move the order to `shipped` and `delivered`.
- Cancellation: allowed only before delivery. Stock is restored from the order's own `sale` movements, never from `order_items`, so a seeded historical order with no ledger restores nothing instead of inflating stock. The sandbox payment is voided, the shipment becomes `exception`, and an `order_adjustments` row is written.
- Refunds: partial or full, bounded by the remaining total, recorded in `order_adjustments`. The order subtotal is immutable; `refund_total` accumulates and the order becomes `refunded` only when the whole total is returned.
- Stock adjustments: signed quantity changes under `inventory:write`, refused if they would leave less than the reserved quantity, recorded as `adjustment` movements attributed to the operator.
- Customer surface: the customer header no longer links to the back office. Operators reach `/backoffice/login` directly.
Rationale: closes the loop between the existing risk review and the customer order history without inventing a fulfilment provider or rewriting financial history. Every mutation is attributable to a principal.
Consequences: the shipment simulator remains synthetic; there is no carrier webhook, returns workflow, partial-line refund, or exchange path. Refunds adjust recorded totals only and do not call a payment provider.
Approved by: user selection of Phase 1b after the read-only queue.
Evidence/link: `database/relational/migrations/0010_order_lifecycle.sql`, `services/api/src/smart_ecommerce_api/commerce.py`, `apps/storefront/components/order-lifecycle-controls.tsx`, `apps/storefront/lib/order-actions.ts`, and `services/api/tests/test_api.py`.

## Decision record template

When an entry is resolved, add a dated record below rather than overwriting its history.

```text
Decision ID:
Date:
Status: Accepted | Superseded
Selected option:
Rationale:
Consequences:
Approved by:
Evidence/link:
```
