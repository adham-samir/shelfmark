---
name: Smart-eCommerce Management System
description: A bilingual evidence-led commerce workbench, rendered as two instruments: a calm storefront and a dense operations console.
colors:
  canvas: "#f6f7f9"
  canvas-deep: "#eff2f5"
  surface: "#ffffff"
  surface-sunken: "#f4f6f8"
  ink: "#0f172a"
  ink-2: "#334155"
  ink-3: "#556070"
  ink-4: "#94a3b8"
  border: "#e2e5ea"
  border-strong: "#cbd5e1"
  border-control: "#6e7787"
  primary: "#2563eb"
  primary-hover: "#1d4ed8"
  primary-active: "#1e40af"
  primary-soft: "#eff4ff"
  success: "#14682f"
  success-soft: "#e7f4ec"
  danger: "#b42318"
  danger-soft: "#fbeae8"
  warning: "#b45309"
  warning-soft: "#fdf3e4"
  rail: "#16233b"
  rail-active: "#23324e"
  rail-text: "#e6eaf0"
typography:
  display:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "clamp(32px, 3.6vw, 46px)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "32px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  caption:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  price:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "normal"
  identifier:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "4px"
  control: "6px"
  panel: "8px"
  card: "10px"
  feature: "14px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
  "12": "48px"
  "16": "64px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
    height: "40px"
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
    height: "40px"
  input-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "42px"
  card-product:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "0"
  status-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
    height: "24px"
  status-warning:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.warning}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
    height: "24px"
  status-error:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
    height: "24px"
---

# Design System: Smart-eCommerce Management System

## Overview

**Creative North Star: "Two instruments, one truth."**

The product serves two audiences whose jobs are genuinely different, so it is
built as two instruments on one foundation:

- **The storefront is a calm browsing surface.** It gets the space, the larger
  type, and the white cards. The product photography is the loudest thing on the
  page and the interface stays out of its way.
- **The back office is a dense operations console.** It gets the dark rail, the
  compact tables, and the audit vocabulary. The data is the subject and the
  chrome recedes.

Both read the same semantic tokens, so they cannot drift apart in meaning: blue
always means the primary action, green always means a healthy state, red always
means something needs recovery.

The previous iteration of this document described a warm-paper "instrument
ledger" palette (cream canvas, graphite rules, amber selection) and recorded a
58.53% comparison against `.impeccable/mocks/comp-a.png` as an approved
exception. **That composition and that palette are retired.** The amber primary
failed AA contrast at 3.36:1 against its own canvas and 3.66:1 for white-on-amber
text, the 10px type tier was below a comfortable reading size for Arabic, and the
near-invisible 1.66:1 rule made every container read as an unfinished outline.
This document describes what is actually shipped now; the comp and its score are
historical artifacts, not a specification.

## Colors

A cool neutral field with one operating colour and three semantic statuses.
Every value below is verified against WCAG 2.2 AA by
`tests/ui/verify-contrast.mjs`, which fails the build on a regression.

### Primary

- **Operating Blue** (`primary`, `primary-hover`, `primary-active`,
  `primary-soft`): primary buttons, links, focus rings, selected states, active
  navigation, and the leading bar on the current back-office section. White on
  primary measures 5.17:1; primary on its own tint measures 4.69:1.

### Semantic

- **Healthy Green** (`success`, `success-soft`): in-stock marks, completed steps,
  confirmed orders, applied price changes. 6.08:1 on its tint.
- **Recovery Red** (`danger`, `danger-soft`): invalid fields, failed payments,
  supplier failures, destructive actions. 5.65:1 on its tint.
- **Attention Amber** (`warning`, `warning-soft`): pending review, stale input,
  reorder pending — states that need a human but are not failures. 4.57:1 on its
  tint.
- **Dark chrome** (`rail`, `rail-active`, `rail-text`): the back-office
  navigation only. `rail-text` on `rail-active` measures 10.6:1.

### Neutral

- **Canvas** (`canvas`, `canvas-deep`): the page field. Cool and untinted, so it
  never competes with product photography.
- **Surface** (`surface`, `surface-sunken`): cards, panels, tables, and the
  inset band inside a table head.
- **Ink** (`ink`, `ink-2`, `ink-3`): body, secondary, and muted text.
  `ink-3` is deliberately darker than a typical muted grey because it must clear
  4.5:1 on `canvas-deep` (5.67:1), not only on white.
- **Ink-4** (`ink-4`): icons, separators, and disabled states. **Never text.**
- **Borders** (`border`, `border-strong`, `border-control`): `border` is
  structural and intentionally low contrast. `border-control` outlines an
  interactive control and clears 4.2:1, satisfying the 3:1 non-text requirement
  that the previous 1.66:1 rule failed.

### Named Rules

**The One Blue Rule.** Blue means "this is the action" or "this is where you
are". It never means success, warning, or decoration.

**The Semantic Colour Rule.** Green, red, and amber carry state and nothing else.
Every status also carries a text label, so meaning never depends on hue alone.

**The Contrast Floor Rule.** No text below 4.5:1 against the surface it sits on;
no interactive control border below 3:1. `ink-4` is excluded from text use
precisely because it cannot meet that floor.

## Typography

**Display / Body / Label Font:** Alexandria, with Noto Sans Arabic, Segoe UI,
Tahoma, and sans-serif fallbacks. Arabic and Latin share one geometry.
**Identifier Font:** `ui-monospace, SFMono-Regular, Consolas, monospace` for
immutable identifiers only.

### Hierarchy

- **Display** (600, fluid 32–46px): the back-office command heading only.
- **Headline** (600, 32px): page titles. 24px on narrow viewports.
- **Title** (600, 17px): panel headings and product names.
- **Body** (400, 15px): interface copy. 13px in back-office tables via the
  `[data-density="compact"]` scope.
- **Label** (500, 13px): controls, actions, table content.
- **Caption** (400, 12px): hints, metadata, secondary evidence.
- **Price** (700, 20px): product and line-item prices, tabular figures.
- **Identifier** (400, 11px, mono): product IDs, principal IDs, supplier
  references.

### Named Rules

**The No-Micro-Text Rule.** Eleven pixels is the floor, and it is reserved for
machine identifiers. Nothing a reader is expected to parse as a sentence is set
below 12px. The previous 9px and 10px tiers were removed because they made
Arabic genuinely hard to read.

**The Evidence Numeral Rule.** Prices, counts, dates, and quantities use tabular
figures. Latin identifiers are isolated LTR inside RTL copy.

## Layout

The storefront canvas is capped at 1400px with a 24px gutter (14px below 900px).
The header is 72px and condenses to 60px once the page scrolls, driven by an
IntersectionObserver sentinel rather than a scroll handler.

The catalog is **filters plus results, and nothing else**: a 264px sticky filter
rail beside a three-column grid (two at 1240px, one at 640px). Comparison is a
dock at the foot of the page that only exists once something is selected. The
earlier design reserved a permanent 344px column for comparison, which cost 21%
of the desktop width while empty and squeezed product cards to 207px.

The back office uses a 248px dark rail that collapses to 64px below 1280px and
becomes a labelled horizontal strip below 900px. Below 760px the dense inventory
table becomes labelled audit cards rather than a horizontal scroller.

Direction comes from the document root (`dir="rtl"` or `dir="ltr"`) and CSS
logical properties. Nothing is manually reversed, and no surface has a separate
Arabic and English layout.

### Named Rules

**The Logical Direction Rule.** Mirror flow with document direction and logical
properties. Motion that moves horizontally flips with the document; motion that
moves vertically does not need to.

**The Content Width Rule.** Reading surfaces cap at 960px. Data surfaces use the
full canvas, because an operator comparing 13 inventory rows needs the width
more than they need a comfortable line length.

## Elevation & Depth

Two tiers, deliberately. `shadow-1` (a single 1px hairline shadow) marks a card
or panel that sits on the canvas. `shadow-2` marks something that is interactive
on hover or floating above the page. The compare dock and drawer use a larger,
directionally-correct shadow because they overlay scrolling content.

Static structure comes from the border and the tonal step between `canvas`,
`surface`, and `surface-sunken` — not from ambient shadow.

### Named Rules

**The Two-Tier Rule.** A surface is either flat on the canvas, raised one tier,
or floating. There is no third resting elevation and no decorative glow.

**The One-Literal Rule.** `tokens.css` is the only stylesheet that contains a
colour literal. The focus ring, the translucent veil under floating controls,
the hairline on the dark rail, and the pulse halo are all named tokens, so
changing one decision means editing one file. A hex value outside `tokens.css`
is a bug, not a shortcut.

## Shapes

Controls use a 6px radius, panels 8px, cards 10px, and feature surfaces 14px.
Pills are fully round and are reserved for status chips and the compare control
that floats over a product image. Circles are functional: the microphone button
and timeline dots only.

Dashed borders appear in exactly one place: the image-search drop zone, where
the dashed edge genuinely means "drop something here". They are not used for
empty states, placeholders, or panels.

### Named Rules

**The Honest Border Rule.** A border style must mean what it looks like. Dashed
means drop target. Solid means container. If an empty state needs emphasis it
gets a tonal fill, not a dashed outline.

## Motion

Motion explains what changed; it never decorates and never blocks input.

- **Durations:** 80ms for colour and border swaps, 140ms for hover and focus,
  220ms for disclosure, 320ms for entering panels, 480ms for the dock and
  drawer.
- **Only `transform` and `opacity` animate.** Nothing that triggers layout.
- **One spring**, described as sampled `linear()` points so it is identical
  across browsers, with overshoot capped under 1.5%.
- **Entrance staggers are capped** (6 cards, 24 chart bars) so a long list keeps
  the same total duration as a short one.
- **Focus rings never animate.** A ring that fades in is a ring that is invisible
  for 140ms.
- **`prefers-reduced-motion: reduce`** collapses every duration and delay to
  0.001ms rather than removing the animation, so `animationend` and
  `transitionend` handlers still fire and nothing hangs waiting on an event.

Where motion appears: product cards stagger up on first paint, filter groups
disclose, the compare dock slides in and its thumbnails pop, add-to-cart swaps
its label and bumps the cart badge once, chart bars grow from the baseline,
assistant bubbles rise, and the microphone pulses only while recording.

## Components

### Buttons

40px minimum height, 6px radius, one-pixel border. **Primary** is blue with white
text and appears at most once per view. **Default** is a white control with a
`border-control` outline that clears 3:1. **Quiet** has no border until hover.
**Danger** outlines in red and fills on hover. Disabled controls sit at 50%
opacity and keep `not-allowed`. A successful add-to-cart swaps both colour and
label, so the state never relies on colour alone.

### Chips

Status chips are pills with a tinted fill and the darker text step of the same
hue, always carrying a written label. Filter chips are removable and turn red on
hover to signal removal. They are not colour-coded by category.

### Cards / Containers

A product card is a white surface with a hairline border, a 10px radius, and a
4:3 image plate whose frame is owned by CSS — the image is absolutely positioned
inside it, so a tall photograph cannot stretch the card and break the grid
rhythm. Titles clamp to two lines, three ordered attributes follow, then
availability, price, and one primary action.

Below 640px the plate flattens to 16:10 so a single-column card still shows its
price and action above the fold.

### Inputs / Fields

White background, 6px radius, `border-control` outline at 4.2:1. Focus replaces
the outline with a blue border plus a 3px soft ring. Invalid fields turn red and
add programmatic error text. Placeholder text uses `ink-3` — placeholders are
text and must meet the same contrast floor as a value.

### Navigation

The storefront header carries the wordmark, a centred search field with voice
and image modes inside it, the locale switch, assistant, account, and a cart
badge that always shows its count. Below 1180px action labels hide but every
control keeps its accessible name; below 900px the header becomes two rows and
the brand drops its subtitle so the actions stay on one line.

The back-office rail groups sections by intent — **Overview**, **Operations**,
**Intelligence** — and marks the current section with a filled pill plus a
leading blue bar. Two signals, so it survives forced-colors mode where the fill
is dropped. Labels are never removed: at the narrowest breakpoint the rail
scrolls horizontally rather than becoming a row of unlabelled icons.

### Comparison Dock

Selecting a product raises a dock at the foot of the catalog showing what is
inside and offering Compare and Clear. It expands into a drawer holding the full
attribute matrix, grouped into basic information, specifications, other details,
and price. Escape closes the drawer and returns focus to the control that opened
it. The dock does not exist when nothing is selected.

### Tables

Back-office tables are 13px with sticky headers, tonal header bands, and row
tints only where a status chip also states the reason. Below 760px each row
becomes a labelled card with `data-label` restored, so no column is lost.

### Interaction & Accessibility

A skip link precedes the header. Focus is always visible: a 2px blue ring with a
2px offset, and a lighter ring on dark chrome. Icon-only controls carry hidden
text. Status changes use `aria-live`; errors use `role="alert"`; busy actions
expose `aria-busy`. Horizontal scroll regions are keyboard focusable. The
accessibility gate in `tests/accessibility/check.mjs` runs 46 pages across both
locales and fails on any serious or critical violation; it currently reports
zero.

## Do's and Don'ts

### Do:

- **Do** keep blue for action and current location, and green, red, and amber for
  state only.
- **Do** use logical CSS properties and let document direction drive the flow.
- **Do** verify every colour pairing against the contrast script before shipping
  it; a token that only works on white is not a token.
- **Do** keep status text-labelled, and pair colour with a written state.
- **Do** reserve dashed borders for drop targets.
- **Do** cap entrance staggers so a long list does not turn into a slot machine.
- **Do** label synthetic product imagery and synthetic operational evidence at
  the point where users encounter it.

### Don't:

- **Don't** reintroduce the warm-paper palette, the amber primary, or the 9–10px
  type tiers; they failed contrast and legibility respectively.
- **Don't** reserve layout space for a control that is empty most of the time.
- **Don't** animate a layout-affecting property, or animate a focus ring.
- **Don't** remove a visible label and leave an icon-only control.
- **Don't** use `ink-4` for text, or a hairline border on an interactive control.
- **Don't** fabricate logos, real product photography, reviews, discounts,
  production prices, or operational-quality claims.
- **Don't** cite the retired `.impeccable/mocks/comp-a.png` comparison as a
  current specification.
