---
name: Smart-eCommerce Management System
description: A bilingual evidence-led commerce workbench rendered as a warm, ruled instrument ledger.
colors:
  paper: "#f7f6e8"
  paper-deep: "#efece0"
  surface: "#fbf8ee"
  surface-alt: "#f4f1e4"
  ink: "#101011"
  graphite: "#3f3f3f"
  muted: "#62625e"
  rule: "#c2c1bb"
  rule-soft: "#ddd9cd"
  amber: "#b87820"
  amber-strong: "#9c6114"
  amber-soft: "#f1e2c2"
  plate: "#faf8ee"
  green: "#2c7a3f"
  green-soft: "#dcecdd"
  red: "#a13b2e"
  red-soft: "#f4ddd8"
typography:
  display:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "clamp(28px, 4vw, 52px)"
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: "-0.025em"
  headline:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "normal"
  body:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  caption:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  price:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "normal"
  compact-headline:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  micro:
    fontFamily: 'var(--font-alexandria), "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
    fontSize: "10px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  identifier:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "9px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  none: "0px"
  control: "2px"
  circle: "50%"
spacing:
  xxs: "2px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  2xl: "14px"
  3xl: "16px"
  panel: "18px"
  gutter: "20px"
  section: "24px"
  command: "32px"
components:
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "8px 14px"
    height: "36px"
  button-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "8px 14px"
    height: "36px"
  button-amber:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "8px 14px"
    height: "46px"
  input-default:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "8px 10px"
    height: "38px"
  card-product:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "8px"
  navigation-active:
    backgroundColor: "{colors.amber-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "9px 10px"
  status-success:
    backgroundColor: "{colors.green-soft}"
    textColor: "{colors.green}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: "4px 7px"
    height: "24px"
  status-warning:
    backgroundColor: "{colors.amber-soft}"
    textColor: "{colors.amber-strong}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: "4px 7px"
    height: "24px"
  status-error:
    backgroundColor: "{colors.red-soft}"
    textColor: "{colors.red}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: "4px 7px"
    height: "24px"
---

# Design System: Smart-eCommerce Management System

## Overview

**Creative North Star: "The Instrument Ledger"**

The interface feels like a calm service-counter worksheet: warm paper, dark graphite rules, compact typography, and dense but legible records. It supports both storefront discovery and operator audit work without changing visual identity, keeping every claim, control, and state visibly grounded in commerce data.

The system is flat and evidence-led. Structure comes from ruled edges, tonal paper layers, tabular figures, and precise alignment; amber marks intent or selection, while green and red remain semantic. Arabic and English are equal compositions, with direction changing the flow rather than the information hierarchy.

**Key Characteristics:**

- Warm paper rather than clinical white.
- Hairline graphite rules rather than floating containers.
- Compact Alexandria typography across Arabic and Latin scripts.
- Amber selection, green success and availability, red failure and recovery.
- Dense, auditable data that becomes stacked cards on narrow screens.
- Synthetic assets and evaluation limits are labeled, never implied away.

## Colors

The palette is a restrained warm-paper neutral field with one measurement amber and two explicit semantic colors.

### Primary

- **Measurement Amber** (`amber`, `amber-strong`, `amber-soft`): selection fills, current navigation, checkbox accents, focus, active pagination, primary operational action, and warning states.

### Secondary

- **Availability Green** (`green`, `green-soft`): in-stock marks, successful cart feedback, completed timeline points, and planned inventory states.

### Tertiary

- **Recovery Red** (`red`, `red-soft`): field errors, failed payments or suppliers, destructive actions, recording state, and error recovery surfaces.

### Neutral

- **Instrument Paper** (`paper`, `paper-deep`): page canvas, footer, table heads, and stronger ruled bands.
- **Work Surface** (`surface`, `surface-alt`, `plate`): cards, controls, alternate rows, product plates, and tonal separation.
- **Graphite Ink** (`ink`, `graphite`, `muted`): primary text, secondary text, labels, and de-emphasized evidence.
- **Ruled Line** (`rule`, `rule-soft`): structural borders and low-emphasis dividers.

### Named Rules

**The Semantic Accent Rule.** Amber communicates intent or selection; green communicates availability or success; red communicates failure, invalidity, or destructive recovery. Never use those colors as interchangeable decoration.

**The Warm Canvas Rule.** Keep the page and controls within the paper family; pure white is reserved for tiny contrast details, not major surfaces.

## Typography

**Display Font:** Alexandria with Noto Sans Arabic, Segoe UI, Tahoma, Arial, and sans-serif fallbacks  
**Body Font:** Alexandria with the same bilingual fallback stack  
**Label/Mono Font:** Alexandria for labels; `ui-monospace, SFMono-Regular, Consolas, monospace` only for immutable identifiers

**Character:** Alexandria gives Arabic and Latin copy a shared, compact geometry. Weight, size, and tabular figures establish hierarchy; the system does not introduce a decorative display face.

### Hierarchy

- **Display** (500, fluid 28–52px, 1.05): the dark inventory command heading only; mobile resolves to 32px.
- **Headline** (600, 24px, 1.25): page and product titles, with 19px used for narrow page heads.
- **Title** (600, 15px, 1.5): panels, trays, inventory sheet headings, and strong card-level labels.
- **Body** (400, 13px, 1.5): default interface copy and record content; long introductions stop around 62–70ch.
- **Caption** (400, 11px, 1.5): attributes, counts, availability, and secondary evidence.
- **Label** (500, 12px, 1.5): controls, compact actions, table content, and metadata.
- **Price** (700, 17px, 1.5): compact product-card prices only.
- **Compact Headline** (600, 19px, 1.25): narrow page heads and ledger emphasis.
- **Micro** (400–600, 10px, 1.5): status chips, table headers, timestamps, IDs, and audit qualifiers.
- **Identifier** (400, 9px, 1.5): immutable product IDs and other machine references only.

### Named Rules

**The Alexandria Rule.** Use Alexandria at weights 400, 500, or 600 for both Arabic and English; reserve heavier emphasis for numeric prices already established in product cards.

**The Evidence Numeral Rule.** Prices, counts, dates, quantities, and policy values use tabular numerals; Latin identifiers and supplier references are isolated LTR inside RTL copy.

## Layout

The global canvas is capped at 1505px with a 20px inline gutter, reducing to 14px at 900px. Desktop storefront chrome is a sticky 100px header using a 200px/search/actions grid and a 208px/1fr/344px workbench for filter rail, product field, and comparison tray. Product results use four columns, then three at 1320px, two at 900px, and one at 560px. At 1100px the comparison tray leaves the side column and the fixed comparison bar becomes the persistent entry point.

The BO-01 inventory surface uses a dark command block over a four-cell ledger, then a 1fr/278px sheet-and-evidence layout. At 1050px the command, sheet, and evidence stack; the evidence becomes two columns. At 700px the ledger becomes two by two and each inventory row becomes a bordered two-column audit card: the product header spans both columns, labels are restored with `data-label`, forecast and status span the full width, and status-tinted rows remain distinguishable.

Direction comes from the document root (`dir="rtl"` or `dir="ltr"`) and CSS logical properties. Grids retain their semantic order, borders use inline/block edges, numeric or Latin fragments use bidi isolation, and explicitly Latin IDs use `dir="ltr"`. `.impeccable/mocks/comp-a.png` is an LTR reference whose 58.53% storefront comparison is an approved RTL composition exception, not a numerical pass.

### Named Rules

**The Logical Direction Rule.** Mirror flow with document direction and logical properties; do not manually reverse content order or duplicate separate Arabic and English layouts.

**The Reference Exception Rule.** `.impeccable/mocks/comp-a.png` is an LTR reference. The storefront comparison score of 58.53% is an approved RTL composition exception, not a numerical pass; preserve equivalent hierarchy and task order rather than chasing pixel symmetry.

## Elevation & Depth

The system is flat by default. A one-pixel rule and a change between paper, deep paper, surface, and alternate surface establish containment; there are no ambient shadows on static panels. Product cards gain only a restrained 0 2px 10px warm-black shadow at 6% and a one-pixel lift on hover. The fixed compare bar uses a 0 -2px 10px shadow at 8% solely to separate it from scrolling content, and the recording control uses a temporary red pulse ring.

### Shadow Vocabulary

- **Card Hover** (`0 2px 10px rgb(38 37 34 / 6%)`): a subtle response to direct hover, paired with a one-pixel lift.
- **Dock Separation** (`0 -2px 10px rgb(38 37 34 / 8%)`): the mobile/tablet fixed comparison bar only.
- **Recording Pulse** (`0 0 0 8px rgba(161, 59, 46, 0.12)`): the midpoint of the active microphone pulse only.

### Named Rules

**The Flat-by-Default Rule.** Static hierarchy is made with rules and tonal paper layers; shadow appears only for hover, fixed-overlay separation, or an active recording signal.

## Shapes

The form language is rectangular and ruled. Panels, cards, tables, buttons, fields, notices, chips, and navigation remain square; the shared 2px radius is limited to small utility controls and the skip link. Circles are functional marks only: range handles, availability dots, timeline points, and the microphone control. Dashed borders indicate empty, drop, or placeholder states rather than a new surface style.

### Named Rules

**The Ruled Rectangle Rule.** Use a one-pixel graphite or soft-rule border and square corners for all primary containers and controls; do not soften the workbench into rounded cards.

## Components

### Buttons

Buttons are restrained rectangular controls whose state comes from fill and border, not size inflation.

- **Shape:** square by default, 36px minimum height, 14px inline padding, one-pixel graphite border.
- **Primary operational:** amber fill with dark ink; BO-01 uses a 46px minimum height for the inventory run action.
- **Dark:** ink fill with paper text for decisive storefront actions.
- **Default:** surface fill with graphite border; hover reverses to ink and paper.
- **Quiet:** transparent border and background until hover; danger keeps a red rule until hover fills red.
- **Hover / focus / disabled:** state transitions run 120–160ms; the global focus ring is 2px strong amber with a 2px offset; disabled controls remain visible at 55% opacity and use `not-allowed`.

### Chips

Status and filter chips remain flat, square, and text-labeled. Active filters use amber-soft with an amber rule and move to red-soft on removal hover. Success, pending, and failed statuses pair green, amber, and red fills with explicit text so meaning never relies on color alone.

### Cards / Containers

Product cards use a surface fill, one-pixel rule, 8px padding, and a 4:3 tonal plate. Titles stay to one line; up to three ordered attributes, visible availability text, tabular EGP price, and the action follow in a consistent vertical rhythm. The compare tray, panels, notices, empty states, and inventory sheet use the same ruled containment rather than independent visual styles.

All catalog imagery is synthetic repository material: four generated base raster plates plus two generated angle/tone variants per base live under `apps/storefront/public/products`, with prompts under `.impeccable/build/prompts`. Fixture IDs map to plates in `apps/storefront/lib/plates.ts`; every product card carries a visible synthetic-product label. No licensed catalog photography or CDN provenance is implied.

### Inputs / Fields

Inputs use paper or surface backgrounds, one-pixel rules, square corners, and compact 38px minimum height. Search is the larger exception at 56px desktop and 48px narrow. Focus uses the strong amber two-pixel ring; invalid fields replace the rule with red and add programmatic error text. Every icon-only or visually hidden field retains an accessible name.

### Navigation

The sticky header uses a two-line wordmark, dominant search strip, locale switch, and compact action links separated by soft inline rules. Active category navigation uses amber-soft plus a two-pixel amber inline-start rule; links underline or change tone on hover. At 900px the header becomes brand/actions over a full-width search row, action labels hide but accessible names remain, and the filter rail becomes an expandable ruled panel.

### Inventory Audit Sheet

The command block is the only large ink-filled surface. It pairs a fluid heading, operator/update evidence, and an amber run action with an `aria-live` result. The ledger summarizes four counts. The sheet uses sticky headers, fixed table proportions, tabular figures, product IDs, explicit status chips, and subtle row tints for pending and supplier-failed states. On mobile, the table is intentionally transformed into audit cards rather than horizontally scrolled miniatures.

### Interaction & Accessibility

Keyboard focus is always visible; a skip link moves to `#main`; inputs, groups, tables, live results, notices, and error recovery use programmatic labels or roles. Icon-only actions include hidden text. Status changes use `aria-live`, errors use `role="alert"`, and busy actions expose `aria-busy`. All animation and transition durations collapse to 0.001ms under `prefers-reduced-motion: reduce`.

## Do's and Don'ts

### Do:

- **Do** preserve the warm paper, graphite rule, and compact Alexandria foundation across storefront and back-office screens.
- **Do** use logical CSS properties, document direction, bidi isolation, and explicit LTR spans for Latin identifiers so Arabic and English remain equal experiences.
- **Do** keep statuses text-labeled and pair amber, green, or red with borders and surface tones rather than color alone.
- **Do** transform dense inventory rows into labeled mobile audit cards at 700px instead of forcing a 960px table through a phone viewport.
- **Do** label synthetic product imagery and synthetic operational evidence at the point where users encounter it.

### Don't:

- **Don't** introduce rounded dashboard cards, glass effects, decorative gradients, or persistent ambient shadows.
- **Don't** treat the 58.53% comparison against `.impeccable/mocks/comp-a.png` as a pass; it is an approved RTL composition exception to an LTR reference.
- **Don't** use amber, green, or red as arbitrary decoration or as the only carrier of state meaning.
- **Don't** fabricate logos, real-product photography, reviews, discounts, production prices, or operational-quality claims.
- **Don't** remove visible focus, text alternatives, retry paths, reduced-motion behavior, or equivalent text paths for image and voice search.
