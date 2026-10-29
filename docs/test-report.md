# Stage 4 test report

Date: 2026-10-28  
Scope: the implemented system at Stage 3 completion, plus the Stage 5 demo identity increment.  
Method: automated suites plus black-box checks against a live API and storefront.
Every result below is reproducible with the commands in
[Reproducing the evidence](#reproducing-the-evidence).

Status vocabulary matches the project plan: **Passed**, **Passed with declared
exception**, **Simulated**, **Blocked**.

## 1. Functional verification matrix

| Requirement | Required evidence | Result | Evidence |
|---|---|---|---|
| OBJ-01 | Personalized recommendations and all assistant functions work in customer journeys. | **Passed for recommendations; Simulated for assistant** | Hybrid ranking returns history-dependent, seen-item-excluded results in the live flow. The artifact covers four products and the seeded customer has seen all four, so the product rail shows the explicit exhausted state; the API run and evaluation carry the ranking evidence. Assistant orchestration, grounding, isolation, and storefront states pass with an injected provider; a real OpenAI call is blocked by a missing key. |
| OBJ-02 | Inventory, sales/order data, and pricing operate together with the prediction components. | **Passed on synthetic data** | BO-01 forecast→reorder, BO-02 pricing→storefront price, and BO-03 RFM all read the same order/inventory records; see rows below. |
| OBJ-03 / BI-01 | Interactive consumer-behavior and financial-performance analysis uses real application records. | **Passed on synthetic records** | `/backoffice/analytics` recomputes on date/category filters and reconciles against `order_items`. |
| SF-01 | Collaborative and content-based recommendations use purchase and browsing history. | **Passed** | Trained hybrid artifact (nDCG@10 1.0 vs popularity 0.690465), live ranked run with browsing and purchase basis, seen-item exclusion, popularity cold start. The four-product artifact is fully seen by the seeded customer, so the storefront rail shows the exhausted state instead of a fallback. |
| SF-02 | Inquiry response, suitable-product help, shipment tracking, and order-access isolation pass. | **Passed with declared exception** | Injected-provider tests cover inquiry, catalog grounding, own-shipment lookup, missing information, upstream failure, and cross-customer denial. Live provider call pending `OPENAI_API_KEY`. |
| SF-03 | Image search, voice search, and dynamic filtering pass individually and together. | **Passed for image search and facets; Simulated for voice** | PyTorch retrieval top-1 1.0 / recall@3 1.0 on the synthetic set; contextual facets and combined filters pass; transcription adapter verified with injected results only. |
| BO-01 | Future-demand prediction, automatic reorder, duplicate prevention, and adequate-stock scenarios pass. | **Passed on labeled synthetic history** | 3.35% holdout MAPE; 13 forecasts, 12 reorders on the first live run, zero duplicates on rerun; adequate-stock negative case; supplier failure and recovery. |
| BO-02 | All named pricing factors influence the defined calculation and automatic price application works. | **Passed on synthetic inputs** | Factor-controlled tests for demand, supply, competitor cost, and season; ±20% cap; cost+5% floor; stale-input block; storefront price propagation; order snapshot unchanged. |
| BO-03 | Correct RFM values/segments and targeted group selection are demonstrated. | **Passed on synthetic order history** | 38 classified / 2 insufficient; all 125 score combinations mapped; quintile ties; segment filter and CSV export row counts match. |
| BO-04 | Payment assessment executes before completion; flagged and failure cases follow the defined policy. | **Passed on synthetic sandbox data** | Recall 0.833 at FPR 0.078 on the sealed holdout; review and assessment-failure paths cannot confirm first; forced tokens preserved; missing artifact fails closed. |
| BI-01 | Both analysis areas present, filters change results, totals reconcile. | **Passed on synthetic activity** | 5,400 views / 2,252 sessions / 95 orders; category filter reduces views and revenue; both reconciliation checks match; unknown category shows the empty state. |
| COM-07 | Customers and operators authenticate on separate, revocable sessions; gated routes reject anonymous access. | **Passed for the demo harness (DEC-017)** | Registration, login, throttled failures, logout revocation, session expiry, customer/operator isolation, account update, and order listing pass route tests; browser smoke checks confirm `/account`, `/account/orders`, `/cart`, `/checkout`, `/assistant`, and every `/backoffice` page gate to the correct sign-in page. |
| COM-08 | An operator can locate and inspect any customer order without customer credentials. | **Passed** | `/v1/backoffice/orders` returns 521 live orders with customer identity and a status filter; `/v1/backoffice/orders/{id}` returns shipping, line items, and shipment events. A customer token receives 403 and an operator token still receives 403 on `/v1/orders`. |
| COM-11 | A customer can cancel their own order before it ships, with a recorded reason. | **Passed** | The black-box flow cancels a confirmed order as its owner, checks that another customer receives 404 and a shipped order 409, and confirms the stock returns exactly one unit and the operator detail shows a customer-attributed adjustment with the chosen reason code. |
| COM-09 | An operator can fulfil, cancel, refund, and adjust stock with an auditable record. | **Passed** | Route tests cover each transition, the illegal-jump 409, cancellation, bounded refunds, and inventory adjustment, plus 403 for a customer token. The black-box flow `test_operator_order_lifecycle_advances_cancels_refunds_and_adjusts` repeats this on a freshly seeded stack. A browser rehearsal on a temporary order walked `pending → ready → in_transit → delivered`; cancelling a confirmed order moved stock 20 → 19 → 20; a seeded order with no sale ledger restored nothing; a manual +3 adjustment appeared as an audited movement. The rehearsal rows were then removed so the seeded demo counts stay reproducible. |

## 2. Security testing

| Check | Result | Evidence |
|---|---|---|
| Customer/back-office authorization | **Passed** | The order, inventory, pricing, segments, risk, and analytics routes return 403 for a customer token and 200 for the operator; anonymous access returns 401. An operator token remains excluded from customer-owned `/v1/orders` reads. Every order-lifecycle and stock-adjustment mutation requires `orders:write` or `inventory:write`, which a customer session never holds. |
| Customer order/shipment isolation | **Passed** | A foreign customer receives 404 with a generic message and no order data. |
| Malicious and invalid uploads | **Passed** | Unsupported media returns 415, oversized payload 413, non-image bytes 422, mislabeled image 422, valid PNG 200; responses never echo uploaded content. |
| Chatbot access boundary | **Passed with declared exception** | Without a provider the endpoint returns a typed 503. With an injected provider, cross-customer shipment lookup is denied and other customers' records never appear. No live model was available to test prompt-injection resistance. |
| Secrets not committed or sent to the browser | **Passed** | `.env*` is gitignored; sandbox tokens are read only in server-side modules (`lib/api.ts` is server-only); no key is rendered in any page. |
| Payment data handling | **Passed** | Only `tok_sandbox_*` token references are stored; no card number or CVV field exists in the schema or API. |
| Demo identity harness | **Passed for the declared demo scope** | Argon2id password verification, SHA-256 session-token storage, seven-day sliding expiry, sign-out revocation, customer/operator surface isolation, and self-service password rotation are covered by API route tests and live browser checks. A password change requires the current value, rejects reuse, ends every other session of the principal, and keeps the calling session valid. Ten failed logins return `429 rate_limited`. No production identity claim is made: there is no email verification, email-based password reset, MFA, OAuth/OIDC, or coordinated multi-instance throttle (DEC-017). |

## 3. Performance and reliability

Measured on the local stack (PostgreSQL 18.6, MongoDB 8.0.34, API and storefront
on the same host) against DEC-014 targets.

| Path | Target | Measured p95 | Result |
|---|---|---|---|
| Catalog list | ≤500 ms | 13 ms | Passed |
| Catalog search | ≤500 ms | 17 ms | Passed |
| Facets | ≤500 ms | 13 ms | Passed |
| Recommendations | ≤500 ms (catalog-class read) | 88 ms | Passed |
| Analytics (month range) | ≤2 s | 60 ms | Passed |
| Segments (50 rows) | ≤2 s | 34 ms | Passed |
| Inventory planning | ≤2 s | 19 ms | Passed |
| Checkout with risk assessment | ≤2 s excluding provider time | ≤330 ms | Passed |

| Reliability check | Result | Evidence |
|---|---|---|
| Missing model artifacts | **Passed** | Forecast, image, recommendation, and fraud artifacts each fail closed with a typed `503` or review route. |
| Database unavailability | **Passed** | Store adapters translate driver errors into `503 dependency_unavailable`; unit tests force connection failures. |
| Retry/idempotency | **Passed** | Checkout idempotency key, reorder idempotency key, one-change-per-pricing-observation, and per-customer-per-date RFM snapshots. |
| State consistency | **Passed** | Price and stock stay authoritative in PostgreSQL; MongoDB holds no price/stock; order snapshots never change with later pricing. |
| Background jobs under load | **Passed** | Each one-shot job completed against the seeded dataset; no job exceeded 3 s. |
| Concurrent duplicate checkout | **Passed** | Ten simultaneous retries of one idempotency key returned 202 ten times, all with the same order ID; exactly one order was created. |
| Back-office server actions | **Passed after a defect fix** | The demo rehearsal found that every back-office action returned HTTP 500 in the production build, because each `"use server"` module also exported its initial state object. The states moved to `apps/storefront/lib/action-states.ts`; all five actions were re-verified in the rebuilt production bundle. |

### Workload at the agreed concurrency

`tests/load/test_workload.py` runs the DEC-014 workload against the containerized
API (isolated PostgreSQL 18.6 / MongoDB 8.0.34): 10 requests per second for 20
seconds with up to 100 requests in flight, then a 100-session burst. p95 in ms:

| Workload | Path | Target | Measured p95 | Result |
|---|---|---|---|---|
| Sustained 10 req/s | Catalog list | ≤500 | 8.0 | Passed |
| Sustained 10 req/s | Catalog search | ≤500 | 7.6 | Passed |
| Sustained 10 req/s | Facets | ≤500 | 8.4 | Passed |
| Sustained 10 req/s | Product detail | ≤500 | 7.0 | Passed |
| Sustained 10 req/s | Recommendations | ≤500 | 16.4 | Passed |
| Sustained 10 req/s | Cart | ≤500 | 12.6 | Passed |
| Sustained 10 req/s | Analytics (month) | ≤2 s | 25.7 | Passed |
| 100-session burst | Catalog list | ≤500 | 135.3 | Passed |
| 100-session burst | Product detail | ≤500 | 125.8 | Passed |
| 100-session burst | Recommendations | ≤500 | 243.7 | Passed |
| 100-session burst | Cart | ≤500 | 213.7 | Passed |

The burst measurement warms each session with `/health/live`, so it reports
request latency rather than TCP setup. Without the warm-up, 100 simultaneous
cold connects peaked at 440 ms p95, still inside the target.

The run exposed and closed a real capacity defect: one PostgreSQL server
connection per request exhausted the default 100-slot server limit at 100
sessions and returned typed 503s. Stores now borrow from a bounded pool
(48 connections by default, `SMART_ECOMMERCE_POSTGRES_POOL_SIZE`), synchronous
endpoints use a matching 100-thread AnyIO limit
(`SMART_ECOMMERCE_WORKER_THREADS`), and checkout takes a transaction-scoped
advisory lock per customer/idempotency key so concurrent retries return the
committed order instead of racing the cart transition.

This is the demonstration workload, not a production capacity claim.

## 4. Accessibility (WCAG 2.2 AA)

`tests/accessibility/check.mjs` runs axe-core 4.14.0 with the
`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` rules against 19
routes in Arabic (RTL) and English (LTR) — 42 pages at 1440×900 with reduced
motion. The operator order queue and one live order detail are included. The script signs in through the API once per run and attaches both
session cookies, so customer and operator pages are checked in their real
signed-in state; the three sign-in/registration pages are checked as a guest.

**Passed — 0 violations on all 42 pages**, and the operator order queue, order detail, and inventory page show zero document overflow at 1440, 960, and 700 px in Arabic and English. The gate found and the code now fixes
seven defect classes:

| Finding | Fix |
|---|---|
| `aria-pressed` on `<a>` view toggles | Replaced with `aria-current` and matching CSS. |
| Stock-adjust button's `aria-label` did not contain its visible text | Reworded the label to start with the visible text (`Adjust stock — <product>`). |
| Brand link's `aria-label` did not contain its visible text | Removed; the visible wordmark is the accessible name. |
| Image-search file input had no label and was nested inside a `role="button"` dropzone | Moved outside the dropzone and associated with a visually hidden label. |
| Pricing `<dl>` contained a `<small>` outside a `dt`/`dd` group | Moved the timestamp beside the list. |
| `--muted` text measured 3.93–4.46:1 on warm surfaces | Darkened to `#62625e` (≥4.78:1); design tokens updated in `DESIGN.md`. |
| Confirmed-order pill measured below 4.5:1 on the green surface | Text colour darkened to `#1f5a2e`. |

A keyboard smoke check passes: the first Tab reaches the skip link with a
visible focus ring. Automated checks do not replace manual assistive-technology
testing; no screen-reader pass has been run.

## 5. AI evaluation

| Model | Dataset | Metric | Result | Limitation |
|---|---|---|---|---|
| SF-01 hybrid recommendation | Synthetic interactions | nDCG@10 vs popularity | 1.0 vs 0.690465 (+44.83%) | Synthetic interactions; no real behaviour. |
| SF-03 image retrieval | Synthetic swatches | Top-1 / recall@3 | 1.0 / 1.0 | Deterministic perturbations only. |
| SF-03 voice | Injected transcriptions | Behavioural only | n/a | No live transcription provider. |
| BO-01 demand forecast | Synthetic chronology | Non-zero-demand MAPE | 3.35% | Synthetic seasonality; no real demand. |
| BO-04 fraud | Synthetic generator | Recall / FPR | 0.833 / 0.078 | Labels come from the generator, not real payments. |
| SF-02 assistant | Injected provider | Grounding cases | Passed | No live provider; answers not evaluated against a live model. |
| BI-01 analytics | Synthetic events/orders | Reconciliation | Matched | Verifies calculation, not commercial insight. |

## 6. Declared gaps

1. **Live OpenAI provider** — assistant and voice transcription are verified only
   with an injected provider. No key is available.
2. **Figma deliverable** — no Figma access; the implementable screen/interaction
   specification stands in, as the plan permits.
3. **Synthetic data only** — every model and dashboard is evaluated on synthetic
   or sandbox data and must not be presented as production quality.
4. **AWS deployment** — no credentials; Stage 5 cloud placement is unproven.
5. **Manual accessibility** — WCAG 2.2 AA is verified by automated axe-core
   checks and a keyboard smoke test only; no screen-reader session was run.

## Reproducing the evidence

```bash
# Unit, route, and contract suites
uv run --project services/api --extra test pytest services/api/tests
uv run --with-requirements tests/data_foundation/requirements.txt \
  python -m unittest discover -s tests/data_foundation -v

# Black-box functional, security, latency, and workload checks (API must be running)
# The integration flows assume a freshly seeded stack; reset the volumes between runs.
SMART_ECOMMERCE_TEST_BASE_URL=http://127.0.0.1:8000 \
  uv run --project services/api --extra test pytest tests/integration tests/security tests/load -v

# Accessibility gate (storefront and API must be running)
cd tests/accessibility && npm ci
STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run check

# Demo rehearsal against a freshly seeded stack, then the deck layout check
DEMO_UI=http://127.0.0.1:3000 DEMO_API=http://127.0.0.1:8000 npm run rehearse
npm run verify-deck

# Model rebuilds
uv run --project services/api python services/api/ml/recommendation/train.py
uv run --project services/api python services/api/ml/forecast/train.py
uv run --project services/api python services/api/ml/image_search/evaluate.py
uv run --project services/api python services/api/ml/fraud/generate.py
uv run --project services/api python services/api/ml/fraud/train.py
```