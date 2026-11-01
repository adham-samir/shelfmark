# Testing and verification

This is the developer reference for running Shelfmark's checks. If you only want
to *use* the app, read the [README](../README.md) instead.

Everything here runs against disposable or freshly seeded data. No command points
at an existing database or an external service.

## Prerequisites

- Docker with its daemon running (the data checks start their own PostgreSQL and
  MongoDB containers and stop only those).
- `uv` for the Python suites (https://docs.astral.sh/uv/).
- Node.js for the storefront and browser gates.

## Run the stack first

The integration, security, load, accessibility, and rehearsal checks are
black-box: they expect the running stack. Start it as the README describes:

```bash
docker compose -f infra/compose.yaml up --build
```

The API is on `http://127.0.0.1:8000` and the storefront on
`http://127.0.0.1:3000`.

## Backend and database

```bash
# The migration runner's own behaviour, against a disposable PostgreSQL.
SMART_ECOMMERCE_TEST_POSTGRES_DSN=postgresql://postgres:ephemeral@127.0.0.1:15501/postgres \
  uv run --project services/api --extra test pytest services/api/tests/test_migrations.py -v

# Real PostgreSQL/MongoDB constraints in throwaway containers (no host ports).
uv run --with-requirements tests/data_foundation/requirements.txt \
  python -m unittest discover -s tests/data_foundation -v

# The FastAPI route/service/contract suite (database-backed tests skip without a DSN).
uv run --project services/api --extra test pytest services/api/tests -q
```

## Black-box suites (need the running stack)

```bash
uv run --project services/api --extra test pytest tests/integration/test_commerce_api.py -v
uv run --project services/api --extra test pytest tests/security tests/load -v
```

`tests/integration` reads `SMART_ECOMMERCE_TEST_BASE_URL` (default
`http://127.0.0.1:8000`).

The integration suite writes orders, price changes, reorders and segments, so it
expects a **freshly seeded stack** per run: re-seed with
`docker compose -f infra/compose.yaml down -v && docker compose -f infra/compose.yaml up -d`
between attempts, or reused state makes the pricing and checkout counts fail.

It runs whether or not an AI provider key is configured. With one, the assistant
answers and voice transcription reaches the provider; without one, those two
surfaces return the typed `dependency_unavailable` envelope. Either is accepted —
the strict missing-key contract is covered by the API unit tests, which never
have a key.

## Storefront

```bash
cd apps/storefront
npm ci
npm run typecheck
npm test          # Node's test runner over tests/**/*.test.ts
npm run build
```

## Accessibility gate

```bash
cd tests/accessibility && npm ci
STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run check
```

axe-core WCAG 2.2 AA across the customer and operator routes in both locales; it
fails on any serious or critical violation.

## Presentation deck

```bash
cd tests/accessibility
npm run verify-deck     # slide layout at 1440 / 960 / 700, no overflow, images present
```

## Demo rehearsal

Drives the demo script through the real UI, records timings, recaptures the deck
screens, and reports drift. It needs the running stack and a Chromium binary.

```bash
cd tests/accessibility
DEMO_UI=http://127.0.0.1:3000 \
  DEMO_API=http://127.0.0.1:8000 \
  DEMO_SHOTS=/tmp/shelfmark-shots \
  npm run rehearse
```

Point `DEMO_SHOTS` at a scratch directory first; it overwrites the committed
`docs/presentation/assets/` otherwise. A run with 0 drift and exactly two
intentional console errors (a spoofed-upload `422` and an unknown-product `404`)
is the expected result. See [`presentation/rehearsal.md`](presentation/rehearsal.md).

## Rendering budget and captures

```bash
cd tests/ui
STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run vitals   # LCP/CLS/TBT budget
npm run capture                                                  # 136-page screenshot/axe baseline
```

## Continuous integration

[CI](../.github/workflows/ci.yml) runs the API suite, the database schema checks,
and the storefront typecheck/tests/build on every push and pull request. The
schema checks start the pinned MongoDB 8.2 image, which starts on the modern
kernels (6.19+) where 8.0.x refuses to
([SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912)). The
stack-dependent gates above stay manual.

Results for a recorded run are in [`test-report.md`](test-report.md).
