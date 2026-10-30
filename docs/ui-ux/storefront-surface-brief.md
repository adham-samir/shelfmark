# Storefront discovery workbench

Mode: Operate. Primary target: future `apps/storefront/app/page.tsx`.

Audience/job: Egyptian electronics customers search, filter, compare specifications, see authoritative EGP price/availability, and move a chosen product into the cart. Arabic and English must be equivalent.

Constraints: synthetic comp content is labeled; no reviews, discounts, provider claims, or production inventory are invented. Required recovery, responsive, keyboard, RTL/LTR, and reduced-motion behavior is defined in `screen-spec.md`.

## Direction contract

THESIS: A product-comparison workbench built with the clarity of a service-center diagnostic sheet. It refuses the promotional hero-and-card storefront and begins directly with search, filters, products, and comparable evidence.

OWN-WORLD: A cool neutral canvas, white product cards on a hairline border, one operating blue for action and current location, and green/red/amber reserved for state. Aligned numeric and spec columns; the interface stays calm under dense information.

STORY: Find a product, narrow the field, place candidates in the comparison tray, understand meaningful differences, then add the selected item to cart with current price and availability visible.

FIRST VIEWPORT: A 72px bilingual header with a centred search across the top; a 264px filter rail on the inline-start edge; a three-column product field filling the rest. Comparison is a dock at the foot of the page that appears once a product is selected, so the product field keeps the full width when nothing is being compared.

FORM: Shipped as the storefront half of the "Two instruments" system in `DESIGN.md`. The earlier `1ea7ceac` diagnostic-record direction and `.impeccable/mocks/comp-a.png` are retired.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
