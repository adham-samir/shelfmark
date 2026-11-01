# Shelfmark

Shelfmark: An AI-Powered Smart E-Commerce Management System

Incremental implementation of [the project plan](docs/source-specification-plan.md).

## Selected stack

Next.js + React + Tailwind CSS; Python + FastAPI; PostgreSQL + MongoDB; Scikit-learn + PyTorch + OpenAI API; Docker + AWS.

Selections are recorded in [the decision register](docs/decisions.md). Development follows the five stages in the source plan. Stages 1–4 are complete in the repository: Stage 3 delivered every module except live OpenAI provider proof, and Stage 4 added the functional, security, workload, accessibility, and AI-evaluation evidence. Stage 5 packaging, deployment guidance, user manual, demo script, and presentation outline are in place; the actual AWS placement is blocked on account access.

## Current deliverables

- [Requirements](docs/SRS.md), [traceability](docs/requirements-traceability.md), and [data plan](docs/data-plan.md).
- [Architecture diagrams](docs/diagrams/README.md).
- [Data foundation](docs/architecture/data-foundation.md): 30 PostgreSQL tables across twelve migrations, MongoDB validation/indexes, seeds, ownership, and consistency contracts.
- [UI/UX specification](docs/ui-ux/README.md): approved visual composition, complete customer/back-office screens, states, and flows; Figma file pending external access.
- [Implemented design system](DESIGN.md): exact bilingual tokens, typography, controls, responsive rules, accessibility conventions, reusable components, and synthetic asset provenance; machine-readable sidecar at `.impeccable/design.json`.
- [API contracts](docs/api/README.md): catalog and full-platform OpenAPI 3.1 designs.
- [FastAPI service](services/api/README.md): Dockerized catalog, commerce/risk spine, demo identity/session harness, trained hybrid recommendations, grounded assistant orchestration, image/voice search, BO-01 predictive inventory control, BO-02 dynamic pricing, BO-03 RFM segmentation, BO-04 trained fraud assessment, and BI-01 analytics backed by both databases.
- [Next.js application](apps/storefront/README.md): Arabic-first RTL customer storefront with sign-in, registration, account, and order history, plus a separately gated operator back office with BO-01 inventory, BO-02 pricing, BO-03 segmentation, BO-04 risk-review, and BI-01 analytics pages, English LTR parity, and server-only credentials.
- [Stage 4 test report](docs/test-report.md): functional matrix, security, workload, accessibility, reliability, and AI evaluation.
- [Final presentation](docs/presentation/README.md): 17-slide self-contained HTML deck with speaker notes, exported PDF, 31 system screenshots, and the [demo rehearsal log](docs/presentation/rehearsal.md).
- [Progress and remaining decisions](docs/progress.md).

## Verify this increment

Prerequisites: Docker with its daemon running, and `uv`. The data checks start isolated PostgreSQL and MongoDB containers, publish no host ports, and stop only those containers afterward. No existing database is used.

```bash
# Schema: one command, tracked by checksum, safe to re-run.
uv run --project services/api python -m smart_ecommerce_api.migrate --status

uv run --with-requirements tests/data_foundation/requirements.txt python -m unittest discover -s tests/data_foundation -v
uv run --project services/api --extra test pytest services/api/tests
uv run --project services/api --extra test pytest tests/integration/test_commerce_api.py -v
uv run --project services/api --extra test pytest tests/security tests/load -v

# Storefront helpers (Node runs TypeScript directly)
cd apps/storefront && npm test && cd ../..

# The migration runner's database behaviour, against a disposable PostgreSQL.
SMART_ECOMMERCE_TEST_POSTGRES_DSN=postgresql://postgres:ephemeral@127.0.0.1:15501/postgres \
  uv run --project services/api --extra test pytest services/api/tests/test_migrations.py -v
```

The integration test is black-box and expects a reachable API at `SMART_ECOMMERCE_TEST_BASE_URL` (default `http://127.0.0.1:8000`). Build the storefront separately:

```bash
cd apps/storefront
npm install
npm run typecheck
npm run build
```

Run the accessibility gate against the started storefront:

```bash
cd tests/accessibility && npm ci
STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run check
```

Run the integrated local slice with `docker compose -f infra/compose.yaml up --build`; see the [API service guide](services/api/README.md) and [storefront guide](apps/storefront/README.md). Database image tags are pinned to `postgres:18.6` and `mongo:8.0.34`; runtime dependencies are locked in `services/api/uv.lock`. Verification evidence is recorded in [progress](docs/progress.md).
