# Accessibility gate

Stage 4 WCAG 2.2 AA automated checks for the storefront and back-office routes.

```bash
npm ci
STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run check
```

The script signs in through the API with the seeded demo accounts and attaches
both session cookies, so customer and operator pages are checked in their real
signed-in state while the sign-in/registration pages are checked as a guest. It
uses axe-core with the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa`
rule tags against 19 routes in Arabic (RTL) and English (LTR) — 38 pages — plus a
keyboard focus smoke check. It exits non-zero on any `serious` or `critical`
violation. Lower-impact findings are printed as warnings.

It needs a Chromium binary. The default is `/usr/bin/chromium`; set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` to use another path. `playwright-core` is used
so no browser download is required.

Start the API first (`docker compose -f infra/compose.yaml up --build`) and the
storefront (`cd apps/storefront && npm run build && npm start`); the back-office
pages read the API with server-side credentials.

Limitation: automated rules do not replace a manual screen-reader pass. The
report records that limitation explicitly.