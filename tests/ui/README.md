# UI verification

Two checks that keep the interface honest after a change.

## Contrast

```bash
node tests/ui/verify-contrast.mjs
```

Reads the token values straight out of `apps/storefront/app/styles/tokens.css`
and asserts every pairing the interface actually renders. Text pairings must
clear 4.5:1 (WCAG 1.4.3); interactive control borders must clear 3:1 (WCAG
1.4.11). It exits non-zero on a regression, so a palette edit that quietly
breaks a status chip fails here rather than in review.

`--ink-4` is deliberately below the text floor and is reported as a note rather
than a failure: it is reserved for icons, separators, and disabled states.

## Screenshots and axe baseline

```bash
cd tests/ui
STOREFRONT_BASE_URL=http://127.0.0.1:3001 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 \
  CAPTURE_LABEL=after \
  npm run capture
```

Captures every route in Arabic (RTL) and English (LTR) at 1440, 900, and 390px —
136 pages — plus the guest routes, and writes `shots/<label>/summary.json` with
the axe violation counts per page. Comparing two labels is a diff of two JSON
files rather than an opinion.

It uses the seeded demo accounts through the API, the same way
`tests/accessibility/check.mjs` does, so customer and operator routes render in
their real signed-in state. `playwright-core` is reused from the accessibility
suite; set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to point at a different Chromium.

The harness waits for `domcontentloaded` rather than `networkidle`: the
back-office rail prefetches every sibling route, so the network never goes idle
and `networkidle` times out on those pages.

## Rendering performance

```bash
cd tests/ui
STOREFRONT_BASE_URL=http://127.0.0.1:3001 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 \
  npm run vitals
```

Measures LCP, CLS, and total blocking time on the eight heaviest routes across
both locales and two viewports — 32 measurements — and fails when any exceeds
the Core Web Vitals "good" thresholds (2500 ms, 0.1, 200 ms). The numbers are
collected in the page with `PerformanceObserver`; the app carries no
instrumentation and no API contract changes.

`longtask` is Chromium-only. Under `BROWSER=firefox` TBT is reported as `n/a`
rather than `0`, because a zero there would be an absent measurement read as a
perfect score. Writes `shots/vitals-<engine>.json`.

## Other engines

Both harnesses accept `BROWSER=chromium|firefox|webkit` (see
`tests/accessibility/engine.mjs`). The default stays the system Chromium.

Playwright patches the browsers it drives, so a system Firefox is not a
substitute. Install the bundled engines once:

```bash
cd tests/accessibility
node node_modules/playwright-core/cli.js install firefox webkit
```

WebKit additionally needs host libraries (`libicu`, `libxml2`, `libflite1`) that
require root to install; without them `BROWSER=webkit` fails at launch rather
than silently passing.

A full capture is 136 pages, which is more than a second engine needs for a
rendering check. `CAPTURE_ONLY` takes a comma-separated list of route names:

```bash
BROWSER=firefox CAPTURE_LABEL=final \
  CAPTURE_ONLY="catalog,product,cart,backoffice-orders,backoffice-analytics" \
  STOREFRONT_BASE_URL=http://127.0.0.1:3000 \
  SMART_ECOMMERCE_API_URL=http://127.0.0.1:8000 npm run capture
```

Output goes to `shots/<label>-<engine>/`, so it never overwrites the Chromium
run.

## The blocking gate

`tests/accessibility/check.mjs` remains the gate that can fail a release. It
checks 46 pages across both locales and fails on any serious or critical axe
violation, plus a keyboard-focus smoke test and a `lang`/`dir` assertion per
locale.
