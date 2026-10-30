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

## The blocking gate

`tests/accessibility/check.mjs` remains the gate that can fail a release. It
checks 46 pages across both locales and fails on any serious or critical axe
violation, plus a keyboard-focus smoke test and a `lang`/`dir` assertion per
locale.
