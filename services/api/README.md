# API service

This service now contains ten verified slices: public catalog composition, the authenticated commerce/risk spine, the demo identity/session harness, the SF-01 hybrid recommendation backend, the SF-02/SF-03 smart-storefront service boundaries, BO-01 predictive inventory control, BO-02 dynamic pricing, BO-03 RFM customer segmentation, BO-04 trained fraud detection, and BI-01 analytics.

The application composes authoritative lifecycle, price, and availability from PostgreSQL with descriptive catalog content from MongoDB. Active records missing either side fail closed with `503 dependency_unavailable`; inactive or unknown product IDs return `404 product_not_found`.

Schema changes go through `python -m smart_ecommerce_api.migrate`. It applies each numbered file under `database/relational/migrations` once, in filename order, in one transaction per file, and records the version plus its checksum in `schema_migrations`. An applied file is immutable: editing one aborts the run instead of leaving two databases that claim the same version with different schemas. `--status` reports pending and changed files, `--seed` also applies the synthetic seed (and refuses a database that already holds products), and `--baseline` adopts a database that predates the tracking table. Compose runs it as the `migrate` service before the API starts.

Every request writes one JSON line to stdout carrying the same `request_id` that is returned in the `x-request-id` header and in error bodies, so a reported ID is traceable. `SMART_ECOMMERCE_LOG_FORMAT=text` switches to readable output, `SMART_ECOMMERCE_LOG_LEVEL` sets the level, uvicorn's duplicate access log is silenced, and the access line never contains credentials, cookies, bodies, or contact details.

PostgreSQL access goes through one bounded pool per process (`db.py`, 48 connections by default, `SMART_ECOMMERCE_POSTGRES_POOL_SIZE`). The pool keeps 100 concurrent sessions inside the server's connection limit, and synchronous endpoints use a matching `SMART_ECOMMERCE_WORKER_THREADS` limit. The commerce slice implements browsing-event capture, cart mutation, retry-safe sandbox checkout, immutable order-price snapshots, pre-completion risk assessment, a capability-protected review queue/decision, customer-owned order and shipment reads, stock consumption, and a shipment simulator. Checkout serializes concurrent retries of the same customer/idempotency key with a transaction-scoped advisory lock, so duplicate requests return the committed order instead of racing the cart transition. Local bearer values are synthetic `identity_subject` values from the seed; they are not production credentials or JWTs.

SF-01 trains collaborative item similarity from interaction co-occurrence and content similarity from product text with Scikit-learn. Runtime ranking combines them 60/40 with a small popularity tie-breaker, consumes both browsing and confirmed-purchase history, excludes seen items, persists ranked evidence, and uses a documented popularity fallback for cold-start customers. If every artifact item is already seen the result is intentionally empty; the storefront reports that exhausted state rather than returning seen items. Rebuild the tracked artifact and evaluation report with:

```bash
uv run --project services/api python services/api/ml/recommendation/train.py \
  --dataset services/api/data/recommendation.synthetic.json \
  --artifact services/api/artifacts/recommendation.joblib \
  --evaluation services/api/artifacts/recommendation.evaluation.json
```

SF-02 grounds an OpenAI Responses API adapter in project-authored bilingual FAQ content, the current composed catalog, the authenticated customer's own recent orders and shipments, and any order they attach explicitly. Set `OPENAI_API_KEY` to exercise the real provider; without it, assistant requests intentionally return a structured `503 dependency_unavailable`. The root `.env.example` ships working defaults — `SMART_ECOMMERCE_OPENAI_BASE_URL=https://openrouter.ai/api/v1` with `SMART_ECOMMERCE_ASSISTANT_MODEL=deepseek/deepseek-v4.1-flash` — while the bare code defaults are only placeholders, and an empty base URL means OpenAI itself.

SF-03 adds contextual catalog facets, repeatable `filter=key:value` filters, validated JPEG/PNG/WebP retrieval through a PyTorch feature baseline, and recorded-audio transcription through `SMART_ECOMMERCE_TRANSCRIPTION_MODEL` (`openai/whisper-large-v3` in `.env.example`). Browser recordings work in every engine because the media type is normalised before the allow-list check. The tracked image evaluation is synthetic and proves pipeline behavior only. Reproduce it with:

```bash
uv run --project services/api python services/api/ml/image_search/evaluate.py \
  --artifact services/api/artifacts/image_search.json \
  --evaluation services/api/artifacts/image_search.evaluation.json
```

BO-01 trains a deterministic Scikit-learn demand model with lag, rolling-demand, and calendar features. Every feature is derived from earlier dates; the final 28 calendar days are the chronological holdout. The runtime recursively predicts 14 days and applies DEC-008: seven-day lead time plus seven-day safety stock, pending replenishment included in inventory position, and reorder quantity up to 21-day cover. Rebuild the explicitly synthetic artifact and evaluation with:

```bash
uv run --project services/api python services/api/ml/forecast/train.py
```

Run the daily one-shot worker, suitable for a scheduler, with:

```bash
uv run --project services/api python -m smart_ecommerce_api.inventory_job
# or: docker compose -f infra/compose.yaml --profile jobs run --rm inventory-job
```

The same operation is exposed for demonstrations at `POST /v1/backoffice/reorders/run`; `GET /v1/backoffice/inventory` returns typed stock, forecast, policy, and supplier evidence. Both require `inventory:write`. The supplier is an injectable simulator, never a claimed real integration. `SMART_ECOMMERCE_FORECAST_ARTIFACT` overrides the tracked model path.

BO-02 prices every active product from the latest imported observation under DEC-009. The deterministic calculation combines demand relative to observed supply (weight 0.15), competitor cost relative to recorded cost (weight 0.10), and the dated season multiplier; it is clamped to ±20% per run and never set below recorded cost + 5%. Observations older than 24 hours (or future-dated) block an update, one observation produces at most one change, and every applied change stores an immutable `price_changes` audit snapshot with the complete input set and `dec-009-v1`. Competitors' costs are imported synthetic values (DEC-007), not a real feed. Run the daily one-shot worker with:

```bash
uv run --project services/api python -m smart_ecommerce_api.pricing_job
# or: docker compose -f infra/compose.yaml --profile jobs run --rm pricing-job
```

`GET /v1/backoffice/pricing`, `POST /v1/backoffice/pricing/observations`, and `POST /v1/backoffice/pricing/run` require `pricing:write`. Season windows live in `services/api/data/pricing_seasons.json` and can be overridden with `SMART_ECOMMERCE_PRICING_SEASONS`.

BO-03 calculates RFM snapshots from a rolling 365-day window of paid/completed orders net of refunds. Recency, frequency, and monetary values are scored in independent quintiles with shared ties, and one ordered first-match-wins matrix maps all 125 score combinations to Champions, Loyal, Potential, New, At Risk, or Hibernating. Recalculation replaces the current reference date only and reports customers without eligible history. Run the daily one-shot worker with:

```bash
uv run --project services/api python -m smart_ecommerce_api.segmentation_job
# or: docker compose -f infra/compose.yaml --profile jobs run --rm segmentation-job
```

`GET /v1/backoffice/segments`, `POST /v1/backoffice/segments/run`, and `GET /v1/backoffice/segments/export` require `segments:read`; the export is CSV with spreadsheet-formula neutralization.

BO-04 trains a fraud model on a deterministic synthetic generator over checkout-observable signals (amount versus customer norm, address novelty, token reuse, 24h velocity, prior failures, overnight orders, high amount, first order). A scaled logistic baseline and histogram gradient boosting are compared; the threshold is selected on validation for recall ≥0.80 at FPR ≤0.09 and the better model is evaluated once on a sealed holdout. The selected logistic model reaches 83.3% recall at 7.8% false-positive rate on that holdout. Missing artifacts fail closed to review. Forced `risk-high`/`risk-fail` sandbox tokens remain for deterministic demonstrations. Rebuild the tracked dataset and artifact with:

```bash
uv run --project services/api python services/api/ml/fraud/generate.py
uv run --project services/api python services/api/ml/fraud/train.py
```

`SMART_ECOMMERCE_FRAUD_ARTIFACT` overrides the artifact path. `GET /v1/backoffice/risk` returns the pending queue with score, model version and reasons; `GET /v1/backoffice/risk/model` returns the model card; `POST /v1/backoffice/risk/{assessment_id}/decision` records the audited disposition. All require `risk:review`.

BI-01 reports consumer behaviour from recorded browsing events and financial performance from authoritative orders. Conversion is created orders divided by sessions with any event, so anonymous and non-converting sessions stay in the denominator. Category filters resolve catalog identifiers and scope product behaviour plus item-line revenue. Every response includes a reconciliation block that compares aggregate values with independently recomputed ones, and profit is omitted because no complete cost coverage exists. `GET /v1/backoffice/analytics?from=…&to=…[&category=…]` requires `analytics:read` and rejects ranges over 366 days with `422`.

Run the whole local slice from the repository root:

```bash
docker compose -f infra/compose.yaml up --build
```

Then open `http://localhost:8000/docs`, or request `http://localhost:8000/v1/products`.

Synthetic local identities:

- Customer: `Bearer synthetic-customer-subject`
- Second customer for isolation tests: `Bearer synthetic-other-customer-subject`
- Back-office operator: `Bearer synthetic-operator-subject`

These legacy `identity_subject` values remain accepted so existing tests and
scripts keep working. The storefront now uses the demo identity harness instead:

- `POST /v1/auth/register` creates a customer account and session.
- `POST /v1/auth/login` takes `email`, `password`, and `surface` (`customer` or
  `operator`) and returns a session token plus the account view.
- `POST /v1/auth/logout` revokes the current session.
- `GET /v1/auth/me`, `GET/PATCH /v1/account`, and `GET /v1/orders` expose the
  signed-in account, profile, and owned order history.

Seeded demo credentials: `customer@example.invalid` / `demo-customer-1`,
`other-customer@example.invalid` / `demo-customer-2`, and
`operator@example.invalid` / `demo-operator-1`. Passwords are argon2id hashes in
`account_credentials`; session tokens are stored only as SHA-256 digests with a
seven-day sliding expiry. Ten failed logins per five minutes return
`429 rate_limited`. This is DEC-017's labelled demonstration boundary: no OAuth,
email verification, password reset, MFA, or production identity claim.

Sandbox payment tokens must start with `tok_sandbox_`. A token containing `risk-high` enters manual review; one containing `risk-fail` simulates an assessment failure and also enters review. This deterministic adapter proves the pre-completion integration policy but does not replace the required trained BO-04 model.

For a local process instead of the API container, set `SMART_ECOMMERCE_POSTGRES_DSN`, `SMART_ECOMMERCE_MONGO_URI`, optionally `SMART_ECOMMERCE_MONGO_DATABASE`, and `OPENAI_API_KEY` when exercising assistant/voice calls, then run:

```bash
uv run --project services/api --extra test uvicorn smart_ecommerce_api.main:app --reload
```

The current list implementation composes the active fixture set before filtering and pagination. That is deliberate for the first demonstrable slice, not the final 100,000-product search architecture; indexed search/projection is a later Stage 3 increment. Forecast metrics likewise establish pipeline behavior on synthetic chronology, not production forecasting quality.

Run the black-box commerce flow after starting Compose:

```bash
uv run --project services/api --extra test pytest tests/integration/test_commerce_api.py -v
```

