# Project Progress

Last updated: 2026-10-29

## Current increment

**Stage 4 complete — QA, workload, accessibility, demo identity harness, and operator order reads**

| Item | Status | Evidence / note |
|---|---|---|
| FastAPI application scaffold | Verified | Pinned Python project and lockfile under `services/api`; unit/contract tests pass. |
| PostgreSQL + MongoDB connection | Verified | Readiness checks both stores; Docker Compose smoke test returned `ready`. |
| Public catalog list/detail | Verified | Composes PostgreSQL lifecycle/price/availability with MongoDB descriptive data; category filter and detail were exercised through the running container. |
| Error and consistency boundary | Verified | Structured request-ID errors; inactive/unknown is 404, active cross-store gap/outage is 503, internal stock counts/provenance remain private. |
| Reproducible local demonstration | Verified | Migrations, validators, and synthetic seeds start through `infra/compose.yaml`; temporary integration stack was removed after validation. |
| Identity and capability boundaries | Verified for the demo harness (DEC-017) | Argon2id credentials, database-backed revocable sessions, and independent customer/operator cookies replace the fixed server-side bearer identities; customer ownership and `risk:review` scope remain enforced, and the legacy bearer path stays available for scripts. Self-service password change (COM-10) requires the current password and ends every other session of the principal while keeping the caller signed in. Production identity provider selection remains a deployment choice. |
| Cart and retry-safe checkout | Verified | Exact EGP totals, current stock checks, immutable item snapshots, customer-scoped idempotency, and inventory consumption. |
| Pre-completion risk flow | Verified integration; model pending | Safe, high-risk, and assessment-failure sandbox paths persist assessment before confirmation; review decisions are scoped and audited. |
| Owned orders and shipment simulator | Verified | Customer isolation returns 404; shipments exist only after confirmation and provide bilingual events. |
| Browsing event capture | Verified | Authenticated, idempotent event ingestion uses stable customer/session/product IDs and provenance. |
| SF-01 training pipeline | Verified on synthetic data | Collaborative and TF-IDF content components use browsing and purchase signals; fixed holdout evaluation records provenance and limitations. |
| SF-01 API and evidence | Verified backend and storefront | Authenticated hybrid ranking, seen-item exclusion, popularity cold start, model/evaluation registration, and ranked-run persistence pass live integration. The trained artifact covers four products and the seeded customer has seen all four, so the product rail shows an explicit exhausted state rather than inventing a fallback. |
| SF-02 grounded assistant | Verified orchestration and storefront; live provider pending | Bilingual FAQ, full composed catalog, and owned-shipment context feed the OpenAI Responses adapter; missing information, missing key, upstream failure, and cross-customer isolation are covered without leaking records. The storefront chat renders the provider-missing state until `OPENAI_API_KEY` exists. |
| SF-03 image search | Verified synthetic backend | Validated uploads run through a PyTorch feature retriever, combine with catalog filters, register model/evaluation evidence, and pass live Docker retrieval. Synthetic swatches do not establish production visual quality. |
| SF-03 voice search and facets | Verified orchestration and storefront; live provider pending | Recorded-audio adapter targets `gpt-transcribe`; injected transcription, dynamic context facets, combined filtering, empty speech, invalid media, and missing-key behavior pass. The storefront implements microphone-permission, recording, upload, and provider-missing states; live transcription remains pending. |
| BO-01 predictive inventory control | Verified on labeled synthetic data | Leakage-safe lag/rolling/calendar features, final 28-day chronological holdout, recursive 14-day forecasts, DEC-008 reorder policy, persisted model/evaluation/decision evidence, idempotent supplier simulation, and recovery retry are covered in unit, database, and live Docker checks. Non-zero-demand MAPE is 3.35% on the synthetic holdout; this is not a production-quality claim. |
| BO-02 dynamic pricing | Verified on synthetic inputs | DEC-009 calculation from recorded cost, supply, demand, competitor cost, and the dated season calendar; 20% per-run cap, cost+5% floor, 24-hour freshness gate, one-change-per-observation idempotency, immutable `price_changes` audit snapshot, storefront propagation, and order-snapshot preservation are covered in unit, route, contract, and live Docker checks. Synthetic competitor costs are not a real feed (DEC-007). |
| BO-03 customer segmentation | Verified on synthetic order history | 40 synthetic customers and 518 deterministic orders across 400 days (cancelled, failed, partially and fully refunded, and out-of-window records); rolling 365-day eligible window, independent quintile scores with shared ties, the ordered six-segment matrix, versioned daily snapshots, insufficient-history reporting, paged filtering, and CSV export are covered in unit, route, contract, database, and live Docker checks. |
| BO-04 trained fraud detection | Verified on synthetic sandbox data | Deterministic 3,000-transaction generator, scaled logistic baseline and histogram gradient-boosting comparison, validation-selected threshold, sealed holdout recall 83.3% at 7.8% FPR, persisted model/evaluation evidence, fail-closed serving, forced demo tokens, reasons, and audited review decisions pass unit, route, contract, and live Docker checks. Synthetic labels do not establish real fraud quality. |
| BI-01 business intelligence | Verified on synthetic activity | 9,000 deterministic browsing events over 90 days and 1,021 order-item lines whose totals equal their orders exactly; consumer and financial metrics, orders-per-session conversion, date and category filters, 90-day daily series, independent source reconciliation, insufficient-data states, and profit omission are covered in unit, route, contract, database, and live Docker checks. |
| Next.js application scaffold | Verified | Next.js 16.4.3 / React 19.3.1 / Tailwind 4.3.3 / TypeScript 7.0.2 production build emits 30 routes. |
| Catalog workbench | Verified | Arabic-first RTL workbench with English LTR parity, search, category/attribute/availability/price filters, sort, paging, and grid/list views over 13 synthetic fixtures. |
| Product detail and recommendations | Verified | Detail, attributes, availability, synthetic plate labeling, and the SF-01 rail with an explicit exhausted state when the customer has seen the whole artifact; missing products return HTTP 404. |
| Comparison tray and compare page | Verified | Session-scoped compare selection, tray, and side-by-side comparison page. |
| Cart and checkout | Verified | Cart mutations, shipping capture, risk-gated checkout, retry-safe idempotency, and bilingual validation errors. |
| Order and shipment page | Verified | Owned order detail plus shipment events; missing or foreign orders return HTTP 404. |
| Assistant and image/voice search UI | Verified UI; live OpenAI pending | Chat, upload-based image search, and microphone voice search render loading, empty, denied-permission, invalid-upload, and provider-missing states. |
| Storefront data freshness | Verified | Every server-side API read uses `cache: "no-store"`; catalog price and availability are never served from a stale cache. |
| Customer authentication and account | Verified (demo harness) | `/login`, `/register`, `/account`, and `/account/orders` use the database session; registration, profile edit (display name + locale), recent and paged orders, guarded `next` redirects, and sign-out are covered by API and browser smoke checks. |
| Operator gate and back-office shell | Verified (demo harness) | `/backoffice/login` sits outside the gate; every `/backoffice/(panel)` page requires an operator session, and the shell carries the signed-in name, language switch, storefront link, sign-out, and section navigation without appearing in the customer header. |
| Back-office inventory interface | Verified | `/backoffice/inventory` uses a server-only operator token and presents stock, forecast, pending supply, reorder calculations, simulator status, policy evidence, bilingual copy, and accessible run/loading/error/empty states. Desktop and mobile captures passed the finish review. |
| Back-office pricing interface | Verified | `/backoffice/pricing` presents current price, recorded cost/supply/demand/competitor cost, freshness status, proposal and delta, last applied change, audit trail, the DEC-009 policy evidence, and a synthetic observation import form. Bilingual RTL/LTR, run/loading/error/empty states, and a production build pass. |
| Back-office segmentation interface | Verified | `/backoffice/segments` presents the RFM reference date, stale/fresh state, segment counts, paged members with R/F/M values and scores, the ordered policy matrix, and a CSV export proxied through a server-only route. Bilingual RTL/LTR, run/loading/error/empty states, and 1440/960/700 renders pass. |
| Back-office analytics interface | Verified | `/backoffice/analytics` presents date/category filters, consumer and financial KPI panels, a CSS daily trend with an orders marker, top products, a reconciliation table, metric definitions, and the profit-omission note. Bilingual RTL/LTR, loading/empty/insufficient/error states, and 1440/960/700 renders pass. |
| Back-office risk interface | Verified | `/backoffice/risk` presents the pending review queue with score, outcome, model version, reasons and audited allow/decline actions, plus the model card, threshold, holdout metrics, features and limitations. Bilingual RTL/LTR, empty/error states, and 1440/960/700 renders pass. |
| Back-office order queue | Verified | `/backoffice/orders` lists every customer order with status filter, customer identity, amount, and paging; `/backoffice/orders/{id}` shows customer, shipping, line items, refunds, shipment events, and the lifecycle controls. Reads need `orders:read` (migration 0009); fulfilment, cancellation, and refunds need `orders:write` (migration 0010). Bilingual RTL/LTR and empty/error states pass the automated gate. |
| Operator order lifecycle | Verified | Shipment transitions follow an explicit state machine (`pending → ready → in_transit → delivered`, with `exception` and resume); an illegal jump returns 409. Cancellation restores only the stock the order actually consumed, records an `order_adjustments` row, and voids the sandbox payment. Refunds are partial or full, never exceed the remaining total, and leave the subtotal untouched. Inventory adjustments are audited `adjustment` movements that cannot undercut reserved stock. Live rehearsal: 20 → 19 → 20 units across allow-then-cancel, and a seeded order with no sale ledger restored nothing. |
| Storefront visual gate | Closed with approved exception | The storefront remains deliberately Arabic-first RTL. The recorded 58.53% comparison against the LTR reference did not meet the original 72% numerical target; the user approved preserving RTL and documenting the mismatch rather than misrepresenting it as a pass. Impeccable phases are closed. |
| Stage 4 functional matrix | Verified | Every OBJ, SF, BO, BI, and COM requirement maps to a result and reproducible evidence in `docs/test-report.md`; simulated, blocked, and synthetic-data limits are stated per row. |
| Stage 4 security suite | Verified | Capability enforcement, cross-customer 404 isolation, upload validation (415/413/422/200), provider-missing fail-closed behavior, server-only secrets, and token-only payment handling pass black-box checks. |
| Stage 4 workload | Verified on the demonstration fixture | 10 req/s sustained for 20 s plus a 100-session burst pass the DEC-014 p95 targets on the containerized stack; ten simultaneous identical checkout retries create one order. The run exposed and closed a per-request-connection capacity defect with a bounded pool and a checkout advisory lock. |
| Session maintenance | Verified | `python -m smart_ecommerce_api.session_reaper` deletes expired rows and revoked rows older than 30 days, exposed as the `session-reaper` compose job; every one-shot job now closes the connection pool before exit. |
| Security headers | Verified | The API sends `nosniff`, `no-referrer`, `X-Frame-Options: DENY`, a permissions policy, and a strict JSON-only CSP on every path except the interactive docs; the storefront sends the same header family plus a report-only CSP, because an enforcing policy would break Next.js inline styles. |
| Stage 4 accessibility gate | Verified (automated) | axe-core WCAG 2.2 AA checks pass with 0 violations across 21 routes in Arabic RTL and English LTR (42 pages, including signed-in customer and operator states and a live order detail), and keyboard focus reaches a visible skip link. Seven defect classes were fixed, including a label/visible-text mismatch on the new stock-adjust control; no manual screen-reader pass was run. |
| Stage 5 final presentation | Verified | `docs/presentation/deck.html` (17 slides, English speaker notes) and the exported `deck.pdf` are built from the outline, use 26 screens captured from the running system, and verify at 1440/960/700 with no overflow. |
| Demo rehearsal | Verified | The demo script was driven end to end against a freshly seeded isolated stack after adding the sign-in step: 0 drift, 13.9 s of automated interaction, 26 captured screens, and only the two intentional console errors (spoofed-upload 422, unknown-product 404). It previously found a production-build defect in every back-office server action, a misleading recommendation empty state, and broken RTL timestamps — all fixed and re-verified. See `docs/presentation/rehearsal.md`. |

## Stage 1 completion

| Item | Status | Evidence / note |
|---|---|---|
| Repository inspection and selected stack | Verified | Initial repository contained the source plan only; DEC-001–004 record the selected options from that plan. |
| SRS and traceability | Verified | All OBJ, SF, BO, BI, and supporting COM requirements have journeys, dependencies, failure behavior, and acceptance evidence. |
| UML, ERD, sequence, and data-flow diagrams | Verified | Diagrams cover storefront, back-office, data stores, AI boundaries, and integrations. |
| Data/provenance plan | Verified | Real/public/synthetic/sandbox classes and prohibited claims are explicit. |
| Product/business decisions | Verified | DEC-005–017 fix the locale, permissions, inventory, pricing, RFM, risk, assistant/search, BI, workload, dataset, and demo identity baselines. |
| Measurable acceptance targets | Verified | SRS §7 records performance, accessibility, and model thresholds under DEC-014. |

Stage 1 satisfies its repository completion evidence. Functional implementation status remains separate in the traceability matrix.

## Stage 2 completion

| Item | Status | Evidence / note |
|---|---|---|
| UI/UX screens, states, and flows | Implemented | `docs/ui-ux/` covers all customer and back-office functions, loading/empty/error/auth/insufficient-data states, microphone denial, and invalid images. |
| Visual direction | Implemented | Approved storefront composition `.impeccable/mocks/comp-a.png`, with two comparison studies. These are design artifacts, not a working UI. |
| Figma deliverable | Pending external access | The plan explicitly permits an implementable screen/interaction specification when Figma is unavailable; no unrelated screenshot is called a Figma prototype. |
| Stable identity and field ownership | Verified | One canonical UUID across stores; PostgreSQL owns operational data and MongoDB owns descriptive catalog content. |
| Relational design | Verified | 29 tables across migrations 0001–0010; 0008 adds the credential/session tables, `login_email`, and the surface-mapping trigger; 0009 adds `orders:read`; 0010 adds `orders:write`, `order_adjustments`, and the shipment-event actor. |
| MongoDB design | Verified | Validator, indexes, repeatable setup, identity/authority rejection tests, and idempotent synthetic seed. |
| API contracts | Verified | Catalog plus full-platform OpenAPI 3.1 contracts validate structurally and cover every planned boundary. |
| Revised architecture | Implemented | Data ownership, cross-store consistency, retention/access baseline, ERD, and component view reflect the complete design. |

All Stage 2 work possible in the repository is complete. The only declared external artifact is the Figma file; its equivalent screen/interaction and visual specifications are present, as required when Figma access is unavailable.

## Stage status

| Stage | Status | Exit condition |
|---|---|---|
| 1. System Analysis & Requirements | Complete | Accepted, traceable SRS; decisions, data plan, targets, and required diagrams verified. |
| 2. UI/UX & Database Architecture | Complete with declared Figma exception | Repository design, databases, APIs, and UI flows verified; Figma file remains pending external access. |
| 3. Core Development & AI Integration | Complete with declared live-provider exception | Catalog, commerce/access, SF-01–03, the customer storefront, BO-01 inventory, BO-02 dynamic pricing, BO-03 RFM segmentation, BO-04 trained fraud detection, and BI-01 analytics are implemented and verified. Live OpenAI provider proof remains pending a real key. The storefront RTL/LTR comp mismatch is a closed, documented exception. |
| 4. Testing & QA | Complete with declared exceptions | Functional, security, workload, reliability, accessibility, and AI-evaluation evidence is recorded in `docs/test-report.md`. Live OpenAI proof, synthetic-data limits, and manual assistive-technology testing remain declared exceptions. |
| 5. Deployment & Final Presentation | Repository work complete; cloud placement blocked | Docker packaging, deployment guidance, user manual, demo script, and presentation outline are delivered. The actual AWS deployment and cloud smoke test require account access. |

## Next smallest useful increment

The operator order queue and its audited lifecycle are in place. The next
repository-side gaps are on the customer side (saved addresses, cancelling an own
order, changing a password, buy-again) and in hardening (CI, an Alembic runner,
session reaping, CSRF/Origin checks, security headers, structured logging,
compose hardening). The remaining increments below still require inputs the
environment does not have:

1. **Live provider proof** — set `OPENAI_API_KEY` and re-run the assistant and voice checks, including a prompt-injection attempt, then replace the injected-provider exception with live evidence.
2. **Cloud placement** — supply an AWS account, region, domain, and budget, then apply the planned ECS/RDS/Atlas/S3/Secrets Manager placement and run the documented cloud smoke test.
3. **Manual accessibility** — run a screen-reader and reduced-motion pass with an assistive-technology user; the automated axe gate already passes.
4. **Speaker pass** — the deck ships with English speaker notes; a timed read-through with the actual presenter is still outstanding.

Until those exist, keep the final demo on the local Docker stack and state the exceptions exactly as `docs/test-report.md` records them.

## Known limitations

- The Stage 3 catalog list composes the active fixture set before filtering/pagination. It is correct for the demonstration data but requires indexed search/projection before the 100,000-product target.
- Assistant and voice orchestration plus their storefront interfaces are implemented, but there is no live provider proof because `OPENAI_API_KEY` is unavailable; both surfaces intentionally return the provider-missing state.
- The storefront hero records 58.53% against the approved LTR comp while the page is Arabic-first RTL. This is an approved visual exception, not a numerical pass.
- Storefront product plates are synthetic demonstration assets and are labeled as such in the UI.
- Storefront caching was corrected to `no-store` for all API reads after a stale-catalog defect was found during visual verification.
- Segmentation is verified only against synthetic order history; the current seed leaves the "new" segment empty because no customer lands in the R=3, F<=2 band. Fraud detection is trained and evaluated only on a synthetic generator over checkout-observable signals; no real payment or card-network data was used. Analytics is verified against synthetic events and orders; it does not establish commercial performance. BO-01 forecasting/reorder behavior is implemented only against explicitly synthetic history and a supplier simulator. BO-02 pricing is implemented against imported synthetic competitor costs (DEC-007) and a synthetic season calendar; no real competitor feed or commercial season source exists.
- The local authentication and payment/shipment adapters are explicitly synthetic boundaries, not production providers. Authentication is the labelled demo identity harness in DEC-017: local `.invalid` accounts, no email verification, email-based password reset, MFA, OAuth/OIDC, or coordinated multi-instance throttle.
- The workload result covers the DEC-014 demonstration baseline (10 req/s, 100 concurrent sessions) on the documented synthetic fixture. It is not a production capacity or soak-test claim.
- Accessibility is verified by automated axe-core WCAG 2.2 AA checks and a keyboard smoke test; no manual screen-reader session has been run.
- Synthetic fixtures verify behavior and integration, not real-world recommendation, search, forecast, or fraud quality.
- Figma and AWS access/credentials are unavailable; neither external deliverable is claimed complete.

## Validation evidence

| Check | Result |
|---|---|
| Source requirement and decision-reference coverage | Passed. |
| OpenAPI 3.1 catalog/platform validation and JSON Schema examples | Passed — 6 contract tests against the v0.11.0 platform contract. |
| PostgreSQL/MongoDB physical data suite | Passed — 11 database tests plus the pricing/RFM seed assertions on PostgreSQL 18.6 and MongoDB 8.0.34. |
| FastAPI route/service suite | Passed — 108 tests including identity registration/login/throttle/session-revocation/isolation/account/orders checks, self-service password rotation with session survival and revocation, the session reaper, operator order list/detail capability and surface isolation, order-lifecycle transitions/cancellation/refund/inventory-adjustment authorization and validation, plus BI-01 metric/filter/reconciliation/validation checks, BO-04 feature/forced-token/fail-closed/evidence checks, BO-03 quintile/matrix/exclusion/idempotency/export checks, BO-02 factor/constraint/freshness/idempotency/audit checks, BO-01 chronology/leakage, deterministic inference, 14-day horizon, policy negatives, retry/idempotency, model unavailability, supplier failure/recovery, typed authorization, and all prior storefront services. |
| Black-box commerce/recommendation/risk/search integration | Passed — 6 flows including commerce/risk cases with required shipping address, live history-based hybrid recommendation, dynamic facets, filtered image retrieval, missing-key assistant/voice behavior, persisted evidence, the BO-02 pricing flow with order-snapshot preservation, and the operator lifecycle (illegal-transition 409, `ready`/`in_transit` shipment walk, partial refund with immutable subtotal, over-refund and post-shipment cancellation refusals, customer 403, stock restore on cancellation, and an audited +2 adjustment). |
| Storefront production build | Passed — `next build` with clean TypeScript and the lifecycle controls compiled into the order detail and inventory pages. |
| Storefront route matrix | Passed — catalog, filtered catalog, product, compare, cart, checkout, assistant, image search, voice search, order, sign-in, registration, account, account orders, back-office sign-in, back-office overview, the order queue and detail, and all five smart back-office modules return 200 with the matching session; guest access to gated pages redirects to the correct sign-in page; missing product and missing order return 404. |
| Demo identity flow | Passed — seeded customer and operator sign-in, registration with `next` preservation, profile update, paged orders, sign-out revocation, signed-in `/login` and `/register` redirects, and customer/operator surface isolation were exercised through the running browser and API. |
| Storefront locale and direction | Passed — Arabic `lang="ar" dir="rtl"` and English `lang="en" dir="ltr"` with equivalent copy. |
| Storefront responsive layout | Passed at desktop and mobile widths; the BO-01 worksheet becomes stacked audit cards at 700 px and below. The operator order queue, order detail with lifecycle controls, and inventory adjustment render with zero document overflow at 1440, 960, and 700 px in both locales. |
| Storefront visual gate | Closed by approved exception — recorded 58.53% hero diff vs 72% target; the LTR reference mismatch is preserved honestly and was not counted as a numerical pass. |
| BO-01 held-out evaluation | Passed on labeled synthetic fixture — non-zero-demand MAPE 3.35%, MAE 0.257357, final 28-day chronological holdout. Pipeline behavior only. |
| BO-01 live idempotency flow | Passed — first isolated job generated 13 forecasts, created and acknowledged 12 reorders, and left one adequate-stock product; the second generated no duplicate reorder. Twelve reorder rows, 13 forecasts, one model version, and one evaluation record persisted. |
| BO-01 authorization/API/UI | Passed — missing/customer/operator boundaries return 401/403/typed success; the inventory route returned 13 items and the isolated Next.js page returned 200 in Arabic RTL and English LTR. |
| BO-02 calculation and constraint suite | Passed — 22 pricing unit checks plus route checks cover the demand/competitor/season factors, the 20% cap in both directions, the cost+5% floor and its blocked case, missing/stale/future inputs, one-change-per-observation idempotency, concurrent-writer conflict, audit snapshot contents, season-window resolution, post-rounding bounds, and observation import validation. |
| BO-02 live pricing flow | Passed — isolated PostgreSQL 18.6/MongoDB 8.0.34 databases with the real seed behind a local API: observation import, bounded run, storefront price propagation, repeated-run suppression (`already_applied`), a second observation lowering the price, an order placed before the change retaining its `unit_price`, and two audited `price_changes` rows with complete contributing inputs. |
| BO-02 one-shot job | Passed — `python -m smart_ecommerce_api.pricing_job` evaluated 13 products: 11 updated, 1 already applied, 1 stale, 0 missing/blocked/conflicting. |
| BO-02 storefront interface | Passed — `/backoffice/pricing` returns 200 in Arabic RTL and English LTR with policy, inputs, proposals, last changes, audit trail, and the import form; renders at 1440×900, 960×640, and 700×1100 without document overflow, and the production build includes the route. |
| BO-03 segmentation suite | Passed — 23 segmentation unit checks plus route checks cover recency direction, quintile boundaries and ties, neutral small cohorts, the exhaustive 125-combination matrix, excludes/full refunds, insufficient customers, snapshot replacement, stale snapshots, filtering/paging, CSV shape, and spreadsheet-formula neutralization. |
| BO-03 live segmentation flow | Passed — isolated PostgreSQL 18.6/MongoDB 8.0.34 with the real seed behind a local API: run returned 38 classified and 2 insufficient customers, 345 eligible and 135 excluded orders, the six counts summed to the cohort, segment filtering matched counts, the CSV row count matched the selected group, and a rerun reproduced the same counts. |
| BO-03 one-shot job | Passed — `python -m smart_ecommerce_api.segmentation_job` produced the same snapshot and distribution against the isolated database. |
| BO-03 storefront interface | Passed — `/backoffice/segments` returns 200 in Arabic RTL with segment counts, members and scores, policy matrix, and CSV; the proxied CSV route returned `text/csv`, and 1440×900, 960×640, and 700×1100 renders show no document overflow. |
| BO-04 model evaluation | Passed — sealed holdout: recall 83.3%, false-positive rate 7.8%, precision 68.5%, PR-AUC 0.854, ROC-AUC 0.954 at threshold 0.6985 on the synthetic generator; the logistic baseline beat gradient boosting on validation recall, and both are recorded. |
| BO-04 serving and review flow | Passed — normal contexts allow, strongly suspicious contexts review, forced `risk-high`/`risk-fail` tokens keep their behavior, a missing artifact fails closed to review, model/evaluation evidence persists, and the live queue exposes score, model version, reasons, and audited allow/decline decisions. |
| BO-04 storefront interface | Passed — `/backoffice/risk` returns 200 in Arabic RTL and English LTR with the queue, score/outcome/reasons and decisions, plus the model card; 1440×900, 960×640, and 700×1100 renders show no document overflow. |
| BI-01 analytics suite | Passed — 9 analytics unit checks plus route checks cover both metric families, orders-per-session, zero-denominator handling, category scoping and empty-category honesty, reconciliation match/mismatch, daily ordering, 366-day range validation, profit omission, and source-outage failures. |
| BI-01 live analytics flow | Passed — isolated PostgreSQL 18.6/MongoDB 8.0.34 with the real seed behind a local API: 90-day report returned 5,400 views, 2,252 sessions, 901 add-to-carts, 95 eligible orders, 568,633.34 gross and 511,383.34 net EGP; both reconciliation checks matched; the `phones` filter reduced views and revenue and still reconciled; an unknown category returned the empty state; an inverted range returned 422. |
| BI-01 storefront interface | Passed — `/backoffice/analytics` returns 200 in Arabic RTL and English LTR with KPI panels, trend, top products, reconciliation, and definitions; 1440×900, 960×640, and 700×1200 renders show no document overflow. |
| Stage 4 workload suite | Passed — 10 req/s for 20 s and a 100-session burst on the containerized stack met every DEC-014 p95 target (catalog 8.0 ms, recommendations 16.4 ms, analytics 25.7 ms sustained; catalog 135.3 ms, recommendations 243.7 ms at 100 concurrent sessions), and 10 simultaneous identical checkout retries produced one order. |
| Stage 4 accessibility gate | Passed — axe-core 4.14.0 WCAG 2.2 AA with 0 violations across 42 pages (21 routes × Arabic RTL / English LTR), including signed-in customer and operator states and a live order detail, and keyboard focus reaches the skip link with a visible ring. Fixes: link `aria-current`, brand name, labeled file input outside the dropzone, valid pricing definition list, and a darker muted token (≥4.78:1); the account/order confirmed pill was darkened to `#1f5a2e` for contrast. |
| Demo rehearsal | Passed — 0 drift across 19 steps (including the two sign-ins) on a freshly seeded stack: 13.9 s, 26 screenshots, and only the two intentional console errors; the first attempts exposed a production-build server-action defect, a misleading empty state, and garbled RTL timestamps, all fixed and re-verified. |
| Presentation deck | Passed — 17 slides verified at 1440×900, 960×640, and 700×1100 with no slide overflow and no missing image; exported to a 17-page PDF. |
| SF-01 held-out evaluation | Passed on labeled synthetic fixture — hybrid nDCG@10 1.0 vs popularity 0.690465; relative lift 44.83%. |
| SF-03 synthetic image evaluation | Passed — top-1 accuracy 1.0 and recall@3 1.0 across 12 deterministic perturbation cases; pipeline-only limitation recorded. |
| Docker Compose build/start/seed/readiness | Passed. |
| Live container requests | Passed — readiness, commerce, hybrid recommendation, contextual facets, and filtered PyTorch image retrieval returned expected seeded records; image model/evaluation rows persisted. |
| UI flow Mermaid rendering | Passed — 4 customer/publication flow diagrams rendered with Mermaid CLI 12.0.0. |
| Temporary integration environment cleanup | Passed after verification — only the isolated `codex-bo01-e2e` project and port-3101 Next process were removed; the pre-existing OpenCode stack was left untouched. |

Reproduce the automated checks:

```bash
uv run --with-requirements tests/data_foundation/requirements.txt python -m unittest discover -s tests/data_foundation -v
uv run --project services/api --extra test pytest services/api/tests
uv run --project services/api --extra test pytest tests/integration tests/security tests/load -v
cd tests/accessibility && npm ci && STOREFRONT_BASE_URL=http://127.0.0.1:3000 npm run check
```

Run the local slice:

```bash
docker compose -f infra/compose.yaml up --build
```
