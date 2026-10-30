# Final presentation

| File | Purpose |
|---|---|
| `deck.html` | The deck: 17 slides, self-contained (no network, no CDN), English speaker notes |
| `deck.pdf` | Exported from `deck.html` for submission or offline reading |
| `assets/` | 31 screenshots captured from the running system during the rehearsal |
| `rehearsal.md` | Rehearsal log: timings, observed results, drift found and how it was resolved |

## Using the deck

Open `deck.html` in any browser. `assets/` must sit next to it.

| Key | Action |
|---|---|
| `→` / `Space` / `PageDown` | Next slide |
| `←` / `PageUp` | Previous slide |
| `Home` / `End` | First / last slide |
| `N` | Show or hide the speaker notes |
| `F` | Fullscreen |

Clicking the right or left half of the screen also moves between slides. The
slide number is in the address bar (`#slide-7`), so a slide can be linked or
reloaded directly.

## Re-exporting the PDF

```bash
chromium --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=docs/presentation/deck.pdf \
  "file://$(pwd)/docs/presentation/deck.html"
```

The print stylesheet lays out one slide per page at 1280×720 (16:9). The
result is 17 pages.

## Verifying

```bash
cd tests/accessibility && npm ci
npm run verify-deck
```

The check loads the deck at 1440×900, 960×640, and 700×1100 and fails on any
slide whose content overflows, any missing image, or a broken keyboard
navigation.

## Honesty rules for this deck

Every number in the deck is taken from `docs/test-report.md` or from the
rehearsal run, and each limitation slide states the real limits: no live AI
provider, synthetic data only, no cloud deployment, automated-only accessibility,
the labelled demo identity harness (no OAuth/OIDC, email verification, password
reset, or MFA), the Arabic-first RTL visual exception, and the four-product scope
of the recommendation artifact. If a screen changes, recapture it with
`npm run rehearse` rather than editing an image.
