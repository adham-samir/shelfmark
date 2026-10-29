# Deployment guide

Target placement (DEC-004): Docker on AWS — one Next.js application, one modular
FastAPI service, PostgreSQL, MongoDB, model artifacts, and scheduled jobs.

Status: the **Docker packaging and local orchestration are verified**. The AWS
placement is **blocked** — no credentials or account are available in this
environment. Nothing in this document claims a cloud deployment has happened.

## 1. What ships

| Component | Image / artifact | Notes |
|---|---|---|
| `postgres` | `postgres:18.6` | Holds the schema only; nothing is mounted into `docker-entrypoint-initdb.d`. |
| `migrate` | same API image | One-shot: `python -m smart_ecommerce_api.migrate --seed`. Applies every numbered migration once, then the synthetic seed. The API waits for it to complete. |
| `mongo` | `mongo:8.0.34` | Validator and indexes applied by `catalog-init`. |
| `catalog-init` | `mongo:8.0.34` | One-shot: `setup.js` + `seed.synthetic.js`. |
| `api` | `services/api/Dockerfile` | FastAPI + uvicorn on port 8000, runs as UID 65532. |
| `storefront` | `apps/storefront` | Run `next build` then `next start`; deployed separately or as a second container. |
| Jobs | same API image | `inventory-job`, `pricing-job`, `segmentation-job`, and `session-reaper` under the `jobs` profile. |
| Artifacts | `services/api/artifacts/*` | Recommendation, image-search, forecast, and fraud models are baked into the image. |

## 2. Local run

```bash
docker compose -f infra/compose.yaml up --build
cd apps/storefront && npm ci && npm run build && npm start
```

Health: `GET /health/live`, `GET /health/ready`.

PostgreSQL access is pooled per process. Size `SMART_ECOMMERCE_POSTGRES_POOL_SIZE`
against the database server's connection limit (RDS `max_connections`, Atlas
tier) and keep the API worker count in mind: each worker opens its own pool.

## 3. Environment variables

| Variable | Purpose | Required |
|---|---|---|
| `SMART_ECOMMERCE_POSTGRES_DSN` | PostgreSQL connection string | Yes |
| `SMART_ECOMMERCE_MONGO_URI` | MongoDB connection string | Yes |
| `SMART_ECOMMERCE_MONGO_DATABASE` | Catalog database name | Yes |
| `SMART_ECOMMERCE_RECOMMENDATION_ARTIFACT` | Recommendation model path | Yes |
| `SMART_ECOMMERCE_IMAGE_SEARCH_ARTIFACT` | Image-search artifact path | Yes |
| `SMART_ECOMMERCE_FORECAST_ARTIFACT` | Forecast model path | Yes |
| `SMART_ECOMMERCE_FRAUD_ARTIFACT` | Fraud model path | Yes |
| `SMART_ECOMMERCE_ASSISTANT_KNOWLEDGE` | FAQ knowledge JSON | Yes |
| `SMART_ECOMMERCE_PRICING_SEASONS` | Season calendar JSON | Yes |
| `OPENAI_API_KEY` | Assistant + transcription provider | Optional; without it both surfaces return a typed 503 |
| `SMART_ECOMMERCE_ASSISTANT_MODEL` / `SMART_ECOMMERCE_TRANSCRIPTION_MODEL` | Provider models | Optional |
| `SMART_ECOMMERCE_MAXIMUM_UPLOAD_BYTES` | Upload cap (default 5 MiB) | Optional |
| `SMART_ECOMMERCE_POSTGRES_POOL_SIZE` | Bounded PostgreSQL connections per process (default 48) | Optional |
| `SMART_ECOMMERCE_WORKER_THREADS` | AnyIO worker threads for synchronous endpoints (default 100, the DEC-014 session baseline) | Optional |
| `SMART_ECOMMERCE_API_URL` | Storefront → API base URL | Storefront |
| `SMART_ECOMMERCE_COOKIE_SECURE` | Set to `1` to mark both session cookies `Secure` (requires HTTPS) | Storefront, production |
| `SMART_ECOMMERCE_SANDBOX_TOKEN` / `SMART_ECOMMERCE_OPERATOR_TOKEN` | Optional legacy server-side bearer identities for scripts. The storefront now authenticates through the session cookies and ignores these when unset. | Storefront, optional |

**Secrets:** never commit `.env*`; inject at runtime (AWS Secrets Manager or task
definition environment). The storefront reads API credentials only on the server.

**Sessions:** the API verifies passwords and issues database-backed, revocable
sessions. The storefront stores two independent `httpOnly`, `SameSite=Lax`
cookies (`smart_customer_session`, `smart_operator_session`) and attaches the
matching bearer token only in server-side requests. Set
`SMART_ECOMMERCE_COOKIE_SECURE=1` behind HTTPS so neither cookie is sent over
plain HTTP. This is the labelled demo identity harness (DEC-017); a production
deployment must replace it with a reviewed identity provider and secret
rotation.

## 4. Database setup and upgrades

One command owns the schema, for a fresh database and an existing one alike:

```bash
python -m smart_ecommerce_api.migrate            # apply every pending migration
python -m smart_ecommerce_api.migrate --status   # what is applied, pending, or changed
python -m smart_ecommerce_api.migrate --seed     # also apply the synthetic seed
python -m smart_ecommerce_api.migrate --baseline # adopt a pre-runner database
```

How it behaves:

- `schema_migrations` records each version, its checksum, and how long it took.
  Every file is applied at most once, in filename order.
- Each migration runs in **its own transaction**. A failure leaves neither a
  schema change nor a version row. (This also fixes `0005_shipping_contact.sql`,
  which has no `BEGIN`/`COMMIT` of its own.)
- An applied file is **immutable**. Editing one aborts the run with the file name
  instead of leaving two databases that claim the same version with different
  schemas. Add a new numbered file instead.
- Concurrent runs serialise on a PostgreSQL advisory lock, so several API
  replicas can start at once.
- `--seed` is explicit and refuses a database that already holds products.
  Compose passes it because it is the demo stack; a production deployment runs
  plain `migrate`. Seeding a real database with synthetic orders is never
  automatic.

`docker compose up` runs this as the `migrate` service, and the API waits for it
to complete. A second `up` applies nothing and skips the seed, so restarting the
stack is safe.

**Adopting a database built before the runner existed.** Such a database has the
tables but no `schema_migrations`. Run `--baseline` once: it records the current
files as applied *without running them*, refuses if the database is empty, and
refuses if it is already tracked. Never baseline a database whose actual state
you have not checked.

MongoDB is unchanged: run `database/catalog/setup.js`, then `seed.synthetic.js`
for demos.

## 5. Model artifacts and retraining

Artifacts are versioned files, not database rows. Rebuild and redeploy the image:

```bash
uv run --project services/api python services/api/ml/recommendation/train.py
uv run --project services/api python services/api/ml/forecast/train.py
uv run --project services/api python services/api/ml/image_search/evaluate.py
uv run --project services/api python services/api/ml/fraud/generate.py
uv run --project services/api python services/api/ml/fraud/train.py
```

Model and evaluation rows are registered on first use (`model_versions`,
`evaluation_runs`). Fraud evidence registers once per process.

## 5b. Response security headers

The API sets `x-content-type-options: nosniff`, `referrer-policy: no-referrer`,
`x-frame-options: DENY`, `permissions-policy`, and a strict JSON-only
`content-security-policy` on every path except `/docs`, `/redoc`, and
`/openapi.json`. The storefront sets the same header family in `next.config.ts`
and a **report-only** CSP: an enforcing policy would break Next.js inline styles,
so enforcement is deliberately not claimed. A production deployment should add
HSTS once TLS terminates in front of both services.

## 6. Scheduled jobs

Run each job once per day from a scheduler (EventBridge Scheduler → ECS task, or
cron in a container):

```bash
docker compose -f infra/compose.yaml --profile jobs run --rm inventory-job
docker compose -f infra/compose.yaml --profile jobs run --rm pricing-job
docker compose -f infra/compose.yaml --profile jobs run --rm segmentation-job
docker compose -f infra/compose.yaml --profile jobs run --rm session-reaper
```

Each is retry-safe: reorders, price changes, and RFM snapshots are idempotent per
reference key. The session reaper is a delete: it removes expired sessions and
revoked sessions older than 30 days, so it is safe to run on any schedule.

## 7. AWS placement (planned, not executed)

| Concern | Planned service |
|---|---|
| Storefront + API containers | ECS Fargate behind an ALB |
| PostgreSQL | RDS for PostgreSQL 18 |
| MongoDB | MongoDB Atlas (or DocumentDB with a compatibility review) |
| Artifacts and uploads | S3 with an IAM task role |
| Secrets | AWS Secrets Manager |
| Scheduled jobs | EventBridge Scheduler → ECS tasks |
| Logs and metrics | CloudWatch |

**Blocked:** account access, credentials, domain, and budget approval. Until
those exist, no cloud smoke test can be run and no deployment is claimed.

## 8. Recovery

- **Database loss:** restore the latest RDS snapshot; reapply migrations only if
  the snapshot predates them.
- **Artifact loss:** rebuild from the training scripts; evaluation is
  deterministic for a fixed seed.
- **Job failure:** rerun the same command; idempotency keys prevent duplicates.
- **Provider outage:** assistant and voice return typed `503`; checkout continues
  because risk assessment is local and fails closed to review.

## 9. Post-deployment smoke test

```bash
curl -fsS "$BASE/health/ready"
curl -fsS "$BASE/v1/products?limit=1"
curl -fsS -H "authorization: Bearer $OPERATOR_TOKEN" "$BASE/v1/backoffice/inventory" >/dev/null
curl -fsS "$STOREFRONT/" >/dev/null
curl -fsS "$STOREFRONT/backoffice/analytics" >/dev/null
```