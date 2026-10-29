# Deployment guide

Target placement (DEC-004): Docker on AWS — one Next.js application, one modular
FastAPI service, PostgreSQL, MongoDB, model artifacts, and scheduled jobs.

Status: the **Docker packaging and local orchestration are verified**. The AWS
placement is **blocked** — no credentials or account are available in this
environment. Nothing in this document claims a cloud deployment has happened.

## 1. What ships

| Component | Image / artifact | Notes |
|---|---|---|
| `postgres` | `postgres:18.6` | Migrations 0001–0010 and the synthetic seed mount into `/docker-entrypoint-initdb.d` (identity is `008-identity.sql`, operator order access is `009-operator-orders.sql`, the order lifecycle is `010-order-lifecycle.sql`, and the seed is `011-seed.sql`). |
| `mongo` | `mongo:8.0.34` | Validator and indexes applied by `catalog-init`. |
| `catalog-init` | `mongo:8.0.34` | One-shot: `setup.js` + `seed.synthetic.js`. |
| `api` | `services/api/Dockerfile` | FastAPI + uvicorn on port 8000, runs as UID 65532. |
| `storefront` | `apps/storefront` | Run `next build` then `next start`; deployed separately or as a second container. |
| Jobs | same API image | `inventory-job`, `pricing-job`, `segmentation-job` under the `jobs` profile. |
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

1. Empty database: apply `database/relational/migrations/*.sql` in filename order.
   Migration `0008_identity_sessions.sql` creates the credential/session tables,
   the `login_email` column, and the surface-mapping trigger;
   `0009_operator_order_access.sql` adds the `orders:read` capability to the scope
   constraint, and `0010_order_lifecycle.sql` adds `orders:write`, the
   `order_adjustments` audit table, and the acting operator on shipment events.
   The seed grants both order capabilities to the demo operator.
2. Apply `database/relational/seeds/0001_synthetic_demo.sql` only for
   demonstrations. It is idempotent-free by design; run it on an empty schema.
   The seed creates the demo principals and their argon2id credentials; migrations
   run before seeds, so credentials must stay in the seed.
3. MongoDB: run `database/catalog/setup.js`, then `seed.synthetic.js` for demos.
4. New migrations are additive and numbered; never edit an applied migration.

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

## 6. Scheduled jobs

Run each job once per day from a scheduler (EventBridge Scheduler → ECS task, or
cron in a container):

```bash
docker compose -f infra/compose.yaml --profile jobs run --rm inventory-job
docker compose -f infra/compose.yaml --profile jobs run --rm pricing-job
docker compose -f infra/compose.yaml --profile jobs run --rm segmentation-job
```

Each is retry-safe: reorders, price changes, and RFM snapshots are idempotent per
reference key.

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