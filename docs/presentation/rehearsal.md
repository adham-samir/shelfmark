# Demo rehearsal log

Date: 2026-10-28
Script: [`docs/demo-script.md`](../demo-script.md)
Runner: `tests/accessibility/rehearsal.mjs` (Playwright + Chromium, drives the real UI)

## Environment

| Item | Value |
|---|---|
| Stack | Isolated Docker Compose project `demo-rehearsal` (fresh volumes, synthetic seed applied) |
| API | PostgreSQL 18.6 + MongoDB 8.0.34, container image `services/api` |
| Storefront | Next.js 16.4.3 production build, pointed at the isolated API |
| Identities | Demo accounts from the seed: `customer@example.invalid` / `demo-customer-1`, `operator@example.invalid` / `demo-operator-1` (DEC-017) |
| Reset | `docker compose … down -v && up -d` re-seeds the stack between attempts |

Each attempt starts from a re-seeded stack, so seed-baseline counts (12 reorders,
38 classified customers, and the price moves) are reproducible rather than
accumulated. New registrations would raise the segmentation baseline, so the
demo stays on the seeded accounts.

## Result

**0 drift, 26 captured screens, 13.9 s of automated interaction** (a narrated
presentation of the same script runs about 12 minutes).

| Step | Seconds | Observed |
|---|---|---|
| 0. Demo sign-in — COM-07 | 1.3 | Customer signed in at `/login` → `/account`; operator at `/backoffice/login` → `/backoffice`; both sessions present at once |
| 1. Storefront discovery — COM-01, SF-03 | 0.9 | 13 products at page size 24; Phones + `storage 128 GB` narrowed the grid and the facets |
| 1b. Image search — SF-03 | 0.9 | With the Phones filter, X1 Phone ranked first; a text file renamed `.png` was rejected with the reason |
| 1c. Voice search — SF-03 | 0.4 | Microphone denial state shown, with the text-search fallback |
| 2. Recommendations — SF-01 | 0.4 | `strategy: hybrid`, 226 browsing events, 15 purchased items, no seen item returned |
| 3a. Cart + safe checkout — COM-02/03/04 | 1.0 | Order confirmed, shipment created, price snapshot 8,900 EGP |
| 3b. High-risk checkout — BO-04 | 0.7 | Order in review, shipment correctly absent |
| 3c. Risk review allow — BO-04 | 0.8 | Operator allow confirmed the order and created the shipment |
| 3d. Assessment failure — BO-04 | 0.6 | `assessment_failed` routed to review, no completion |
| 3e. Model card — BO-04 | 0.2 | Threshold 0.699, recall 83.3%, FPR 7.8%, limitations listed |
| 4. Predictive inventory — BO-01 | 1.9 | 13 forecasts, 12 new reorders, 0 reused; the rerun created 0 |
| 5a. Dynamic pricing run — BO-02 | 0.7 | 12 prices updated, 1 stale input, 0 blocked |
| 5b. Price propagation + snapshot — BO-02 | 0.6 | Storefront showed 10,039.93; the earlier order still showed 8,900 |
| 5c. Observation import + bounded rerun — BO-02 | 0.7 | 10,039.93 → 12,047.91 (+19.98%, inside the ±20% cap) |
| 6. RFM segmentation — BO-03 | 0.7 | 38 classified, 2 without history, 6 segments, CSV export matched the filtered group |
| 7. BI dashboards — BI-01 | 0.8 | Date/category filters recomputed; both reconciliation checks matched |
| 8. English LTR parity | 0.9 | `lang="en" dir="ltr"` with the same capabilities and both session cookies |
| 9. Failure states | 0.4 | Unknown product returns HTTP 404; the assistant shows its provider state |
| 10. Evidence check | 0.0 | Inventory and model evidence persisted and readable |

Browser console during the final run: exactly two errors, both intentional — the
spoofed-upload 422 and the unknown-product 404. No unexpected errors, and the
favicon request is now served.

## Drift found and how it was handled

The first three attempts surfaced real defects. Only genuine defects were fixed;
nothing was weakened to make a check pass.

| # | Drift | Kind | Resolution |
|---|---|---|---|
| 1 | Every back-office action returned HTTP 500 in the production build: `A "use server" file can only export async functions, found object`. The action modules exported their initial state objects. | **Product defect** (production build only; unit tests never exercised the built bundle) | Initial states moved to `apps/storefront/lib/action-states.ts`; the `"use server"` modules now export only async functions. All five actions re-verified. |
| 2 | The product rail rendered "not enough history" when the customer had seen everything, and showed no items. | **Product defect** (misleading empty state) | Two distinct states: `product.allSeen` (candidate set exhausted) and `product.recommendationsUnavailable` (API failure). |
| 3 | Technical timestamps rendered as `2819:37 2026/10/` inside the Arabic RTL layout. | **Product defect** (bidi) | `formatDateTime` returns a fixed `YYYY-MM-DD HH:mm` stamp wrapped in an LTR isolate; `time` elements are forced LTR. |
| 4 | The script named payment tokens (`tok_sandbox_demo`, `tok_sandbox_risk-high-demo`) that the checkout form does not offer. | **Script drift** | `docs/demo-script.md` now names the three options the UI actually provides. |
| 5 | The script promised "the blue phone first" and "type the query" on the voice page. | **Script drift** | Image search now chooses the Phones filter first (X1 ranks first, and it exercises the combined filter); the voice page offers a text-search fallback link, not a query box. |
| 6 | The script implied 13 products on the first page. | **Script drift** | The default page size is 12; the script now sets page size 24 to show all 13. |
| 7 | The catalog shows 12 of 13 products per page. | Script drift (same as 6) | Fixed in the script, not in the product. |

Two earlier candidate fixes were **reverted** because they were not real defects:

- Reassigning part of the synthetic browsing seed was dropped: the recommendation
  artifact only covers four products, so no seed reshuffle could make the rail
  non-empty. The honest exhausted state is the correct behaviour.
- The seeded customer seeing every artifact product is not a bug — it is the
  seen-item rule working, and it is now stated in the script and the deck.

## Demo identity increment

The sign-in step was added after the first rehearsal. API and browser smoke
checks found four defects, all fixed and re-verified before the final run:

| # | Finding | Resolution |
|---|---|---|
| 8 | Operator sign-in returned `401` because the login check compared the stored `backoffice` account type with the `operator` surface string. | The API now maps `operator` → `backoffice`; the session-surface trigger uses the same mapping, and the isolation test covers it. |
| 9 | A successful sign-in with no `next` value redirected to `/?q=`, because `safeNext` returned `/` and the catalog's own redirect added the empty query. | `safeNext` returns `""` for missing/invalid values; pages supply `/account` or `/backoffice` defaults. |
| 10 | Credential rows seeded inside migration 0008 failed on a fresh volume because migrations run before the principals exist. | Demo credentials moved to `0001_synthetic_demo.sql`, after the principal rows. |
| 11 | Missing products returned HTTP 200 because the catalog's streaming boundary committed the response first. | Catalog page moved to `(shop)/(catalog)/`, so detail pages resolve the entity before streaming and return a real 404. |

The final fresh-stack run above includes the sign-in step and covers the fixed
paths.

## Screenshots

`docs/presentation/assets/` holds the 26 captured screens used by the deck:
catalog and filtered catalog, image search results and rejection, microphone
denial, product detail with the exhausted recommendation state, cart, checkout,
confirmed order, order in review, risk queue, model card, inventory run, pricing
run, storefront price after repricing, order price snapshot, observation import,
pricing after import, segmentation run and filtered segment, analytics (Arabic
and English), unknown product, and the assistant surface.

## Reproducing

```bash
docker compose -f infra/compose.yaml up -d          # API on :8000
cd apps/storefront && npm run build && npm start      # UI on :3000
cd tests/accessibility && npm ci
DEMO_UI=http://127.0.0.1:3000 DEMO_API=http://127.0.0.1:8000 npm run rehearse
npm run verify-deck     # checks the deck layout at 1440 / 960 / 700
```

`rehearse.mjs` needs `DEMO_UI` and `DEMO_API` if the stack is not on the default
ports. The isolated stack used here ran the API on 18000 and the storefront on
3100, with the storefront pointed at that API.
