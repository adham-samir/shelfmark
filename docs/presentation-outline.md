# Final presentation outline

Audience: graduation committee. Aim for 15–18 minutes plus questions. Each slide
carries one claim and the evidence behind it.

This outline is the source for the built deck: [`presentation/deck.html`](presentation/deck.html)
(17 slides, English speaker notes) with the exported
[`presentation/deck.pdf`](presentation/deck.pdf). Every screen in it was captured
from the running system during the rehearsal recorded in
[`presentation/rehearsal.md`](presentation/rehearsal.md).

## 1. Problem and objectives (2 min)
- Source objectives: OBJ-01 customer experience, OBJ-02 commercial automation,
  OBJ-03 decision support.
- Seven smart modules plus BI, all preserved from the original specification.
- Scope note: this is not a full ERP; it is the specified commerce + AI scope.

## 2. Stack and architecture (2 min)
- Next.js/React/Tailwind storefront; FastAPI backend; PostgreSQL for operations;
  MongoDB for the catalog; Scikit-learn/PyTorch models; Docker.
- One diagram: browser → Next.js server → FastAPI → PostgreSQL + MongoDB, with
  model artifacts and scheduled jobs.
- Ownership rule: PostgreSQL owns price/stock/orders; MongoDB owns descriptive
  content; one UUID links them.
- Two session surfaces: customers and operators sign in separately with revocable
  database sessions; the catalogue stays public while cart, account, and back
  office are gated (DEC-017).

## 3. What was built (4 min)
Walk the seven modules with one screenshot each and one measured number:

| Module | Evidence to show |
|---|---|
| SF-01 recommendations | nDCG@10 1.0 vs 0.690 popularity baseline; exhausted-state rail when all four artifact items are seen |
| SF-02 assistant | grounded FAQ + catalog + owned shipments; isolation proven |
| SF-03 search | image retrieval 1.0 top-1; voice adapter; dynamic facets |
| BO-01 inventory | 3.35% MAPE; 12 reorders created, 0 duplicates on rerun |
| BO-02 pricing | ±20% cap, cost+5% floor, audit trail, storefront propagation |
| BO-03 segmentation | 38 classified; six segments; CSV campaign export |
| BO-04 fraud | recall 83.3% at 7.8% FPR before completion |
| BI-01 | consumer + financial dashboards with source reconciliation |

## 4. Engineering decisions worth defending (3 min)
- DEC-007: competitors' costs kept as literal source wording, imported
  synthetically; the interpretation was not silently changed.
- DEC-009/011: pricing and RFM policies fixed before coding so results are
  reproducible.
- Idempotency everywhere: checkout keys, reorder keys, one-change-per-observation,
  per-date RFM snapshots.
- Fail closed: missing model artifact → review or 503, never a silent pass.
- Honest states: stale inputs block pricing; insufficient history is counted, not
  scored as zero; profit is omitted without cost coverage.

## 5. Testing and quality (2 min)
- 104 API tests, 16 contract/database tests, 5 integration flows, 7 security
  checks, and 3 workload checks.
- Latency at the DEC-014 workload (10 req/s, 100 concurrent sessions): catalog
  8.0 ms sustained / 135.3 ms at burst; recommendations 16.4 ms / 243.7 ms;
  analytics 25.7 ms (p95, containerized local stack).
- Ten simultaneous identical checkout retries produced one order.
- Operator lifecycle: shipment state machine, bounded refunds, cancellable
  orders, and audited stock adjustments verified live.
- Accessibility: axe-core WCAG 2.2 AA, 0 violations across 42 pages (21 routes
  in Arabic RTL and English LTR, including signed-in customer and operator
  states and an operator order detail) plus a keyboard focus check.
- Security: capability enforcement, cross-customer 404s, upload validation, no
  secrets in the browser.

## 6. Limitations stated plainly (2 min)
1. Live OpenAI provider not verified — no key; orchestration proven with injection.
2. All models and dashboards use synthetic or sandbox data.
3. AWS deployment blocked — no credentials; Docker packaging is verified.
4. Accessibility is automated plus a keyboard smoke test; no manual screen-reader
   pass has been run.
5. Authentication is a labelled demo harness (argon2id credentials, revocable
   sessions) with no OAuth/OIDC, email verification, password reset, or MFA.
6. Figma deliverable replaced by the implementable screen specification.

## 7. Demo (live, per `docs/demo-script.md`) (5 min)
Short path: customer + operator sign-in → discovery → checkout with risk review
→ inventory run → pricing run → segmentation → analytics filter.

## 8. Conclusion (1 min)
- All seven modules and BI are implemented and evidenced end to end.
- Remaining gaps are external access (provider key, cloud account) and manual
  assistive-technology testing, not missing functionality.
- Reproducible from `README.md`; evidence in `docs/test-report.md`.

## Anticipated questions

| Question | Answer |
|---|---|
| Why synthetic data? | DEC-015: no private data or credentials were available; provenance is labelled everywhere. |
| Is the fraud model production-ready? | No. It proves the pipeline and policy; production needs labelled provider data and calibration. |
| Why two databases? | The source specified PostgreSQL/MySQL plus MongoDB for the catalog; ownership rules prevent conflicting copies. |
| How do you prevent duplicate reorders? | Idempotency keys per policy/product/horizon, plus pending-replenishment accounting. |
| What happens if a model file is missing? | Forecast/search/pricing surfaces return typed 503; fraud routes to review. |
| Where is the Figma file? | Unavailable access; the screen/interaction specification is the approved substitute. |
| Is the authentication production-ready? | No. It is a labelled demo harness (DEC-017): argon2id passwords and revocable database sessions on separate customer/operator surfaces, but no OAuth/OIDC, email verification, password reset, or MFA. |