# Final demo script

Every step exercises a source requirement and uses known seeded data, so the
outcome is predictable. Total run time ≈ 12 minutes.

This script was rehearsed end to end against a freshly seeded stack; the log of
timings, observed results, and the drift that was found and fixed is in
[`presentation/rehearsal.md`](presentation/rehearsal.md). The captured screens
used by the final deck are in `presentation/assets/`.

Setup:

```bash
docker compose -f infra/compose.yaml up --build      # API :8000
cd apps/storefront && npm run build && npm start     # UI :3000
```

Synthetic demo identities (passwords shown after the slash):

| Surface | Email | Password |
|---|---|---|
| Customer | `customer@example.invalid` | `demo-customer-1` |
| Second customer (isolation) | `other-customer@example.invalid` | `demo-customer-2` |
| Operator | `operator@example.invalid` | `demo-operator-1` |

These are local `.invalid` accounts from the seed under the demo identity harness
(DEC-017), not production credentials.

## 0. Sign in — COM-07 (30 s)

1. Open `/login` and sign in as the seeded customer; the redirect lands on
   `/account`. Point out the account name, profile form, recent orders, and the
   customer header, which links only to customer destinations and carries no
   back-office affordance at all.
2. Open `/backoffice/login` and sign in as the operator; the redirect lands on
   `/backoffice`. Point out the separate operator shell, signed-in name, section
   navigation, and sign-out.
3. Say plainly that this is a labelled demo identity harness: argon2id credentials,
   revocable database sessions, and independent customer/operator cookies, with no
   OAuth, email verification, password reset, or MFA claim.

**Expected:** customer and operator sessions coexist without mixing; signing out
of one leaves the other intact.

## 1. Storefront discovery — COM-01, SF-03 (2 min)

1. Open `/`. Set the page size to 24 in the toolbar to show all 13 synthetic
   products, their prices, availability, and the filter rail.
2. Filter by category **Phones** and attribute **storage 128 GB**; note that the
   result count and facets update.
3. On `/search/image`, choose **Phones**, then upload `phone-blue.png`; X1 Phone
   ranks first and the category filter keeps the result set small. Then upload a
   `.txt` renamed to `.png` to show the rejection message.
4. On `/search/voice`, deny the microphone to show the permission state, then use
   the text-search fallback link to return to the catalog.

**Expected:** filters change results; with the Phones filter, image search returns
X1 Phone first; invalid uploads explain why.

## 2. Recommendations — SF-01 (1 min)

1. Open a product detail page as the seeded customer.
2. The seeded customer has already seen all four products covered by the trained
   artifact, so the rail shows the explicit exhausted state rather than inventing
   results. Say this plainly; it is the seen-item rule working, not a failure.
3. Call `GET /v1/recommendations` with the customer token; note `strategy: hybrid`,
   that the basis reports browsing events and purchased items, and that no seen
   item is returned. Show the recorded nDCG@10 1.0 vs 0.690 popularity baseline.

**Expected:** seen items are excluded; when every artifact item is seen, the rail
says so instead of showing a misleading fallback.

## 3. Cart, checkout, and pre-completion risk — COM-02/03/04, BO-04 (3 min)

1. Signed in as the customer, add a phone to the cart and open `/checkout`; fill
   the address. (Signed out, `/cart` and `/checkout` redirect to
   `/login?next=…`; mention this gate rather than working around it.)
2. Use the normal sandbox option (`tok_sandbox_safe-1`) → order **confirmed**,
   shipment event appears on `/orders/{id}`.
3. Repeat with `tok_sandbox_risk-high-1` → order goes to **review**; show that no
   shipment exists yet.
4. Open `/backoffice/risk`: the row shows score, model version, and reasons.
   **Allow** it, then reload the customer order — now confirmed with a shipment.
   Click the order identifier to open `/backoffice/orders/{id}` and show the
   customer, shipping contact, shipment timeline, and the **Order management**
   controls.
5. From the same page, walk the shipment `pending → ready` and say that each step
   is attributed to the signed-in operator. Stop at **ready** so the cancellation
   and refund controls are still offered; mention that an illegal jump is refused
   with a message and that `in_transit`/`delivered` also move the order status.
6. Repeat with `tok_sandbox_risk-fail-1` to show `assessment_failed` also routes to
   review.
7. Show the model card: threshold 0.699, recall 83.3%, FPR 7.8%, limitations.

**Expected:** no completion path bypasses assessment; decisions are audited once.

## 4. Predictive inventory — BO-01 (1.5 min)

1. Open `/backoffice/inventory`; point out forecast, reorder point, pending supply.
2. Click **Run forecast and reorder**; note created vs reused counts.
3. Run again; show zero new reorders (duplicate prevention).

**Expected:** first run creates reorders, the rerun creates none.

## 5. Dynamic pricing — BO-02 (2 min)

1. Open `/backoffice/pricing`; note current prices, inputs, and freshness.
2. Click **Run pricing**; show updated rows, the ±20% cap, and the audit trail.
3. Open the storefront product page for X1 Phone and show the new authoritative
   price.
4. Reopen a past order and show its historical unit price is unchanged.
5. Import a new observation with a much higher competitor cost, run again, and show
   the bounded increase.

**Expected:** every named factor moves the price; order snapshots never change.

## 6. RFM segmentation — BO-03 (1.5 min)

1. Open `/backoffice/segments`; run segmentation.
2. Show 38 classified and 2 without enough history, and the six segment counts.
3. Click **At risk** to filter, then **Download CSV** and open the file.
4. Show the policy matrix in the side panel.

**Expected:** counts sum to the cohort; CSV rows match the selected group.

## 7. BI dashboards — OBJ-03 / BI-01 (2 min)

1. Open `/backoffice/analytics` with the last 90 days.
2. Point out consumer and financial panels, orders per session, and the daily trend
   with order markers.
3. Apply the **Phones** category; show metrics shrink and the reconciliation still
   matches.
4. Show the reconciliation rows and the profit-omission note.

**Expected:** filters recompute results; totals reconcile; profit is never claimed.

## 8. Evidence and limits — 1 min

Show `docs/test-report.md`: the functional matrix, security results, latency
numbers, and AI evaluation. Then state the declared limits plainly:

- live OpenAI provider not verified (no key);
- all models and dashboards use synthetic data;
- AWS deployment blocked (no credentials);
- no concurrency soak test;
- authentication is a labelled demo harness (DEC-017), not a production identity
  provider: no OAuth/OIDC, email verification, password reset, or MFA.

## Fallback if the stack is unavailable

Run the automated suites instead:

```bash
uv run --project services/api --extra test pytest services/api/tests
uv run --with-requirements tests/data_foundation/requirements.txt \
  python -m unittest discover -s tests/data_foundation -v
```