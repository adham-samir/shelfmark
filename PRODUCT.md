# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated and accepted: Next.js, React, and Tailwind CSS for one storefront/back-office web application; Python and FastAPI for the modular backend; PostgreSQL for operational data; MongoDB for the product catalog; Scikit-learn, PyTorch, and the OpenAI API for their recorded AI responsibilities; Docker and AWS for delivery.

## Users

- Customers in Egypt shopping for consumer electronics in Arabic or English, often comparing specifications and availability before buying.
- Back-office operators managing catalog publication, stock, pricing, order/risk status, customer segments, and business analysis through capability-scoped access.

## Product Purpose

Smart-eCommerce combines a customer storefront and commercial back office. It uses recorded application data to personalize discovery, assist customers, automate inventory and pricing work, identify payment risk before order completion, segment customers, and support decisions through interactive analysis.

Success means the complete purchase flow and every required smart module operate on shared product, customer, order, price, inventory, and interaction records with traceable decisions and honest evaluation evidence.

## Positioning

The storefront and operational intelligence use the same authoritative commerce records: what customers browse and buy feeds recommendations, forecasting, segmentation, risk, pricing, and BI without replacing the required human-visible audit trail.

## Operating Context

- Bilingual Arabic/English responsive web use, with EGP amounts and `Africa/Cairo` presentation time.
- Customer flow: discover, compare, select/cart, checkout with payment-risk assessment, order, shipment tracking.
- Back-office flow: publish catalog records, inspect stock/forecast/reorder, audit price changes, review risk, select RFM segments, and filter BI views.
- Development begins with clearly labeled synthetic, public, and sandbox records because no private operational dataset or live provider credential is available.

## Capabilities and Constraints

- Preserve OBJ-01–03, SF-01–03, BO-01–04, BI-01, and the five ordered project stages from `SMART_ECOMMERCE_CODEX_PLAN.md`.
- Recommendations must include collaborative and content-based approaches using purchase and browsing history.
- The assistant must cover inquiries, suitable-product help, and authorized shipment tracking through the OpenAI API.
- Search must cover images, voice, and dynamic filters.
- MongoDB remains the product catalog; PostgreSQL owns operational price, stock, orders, payments/risk, shipments, and audit records.
- Dynamic pricing retains the source phrase “competitors’ costs”; the demonstration uses an explicitly labeled synthetic import rather than silently changing its meaning.
- AI quality claims require documented datasets, held-out evaluation, and explicit limitations. Synthetic data verifies behavior and reproducibility, not real-world quality.
- No marketplace, multi-vendor system, mobile app, loyalty program, or full accounting/HR/payroll ERP is in scope.

## Brand Commitments

The product name is **Smart-eCommerce Management System**. Its voice is direct, useful, calm, and evidence-led in both languages. It does not make invented commercial, model-quality, or availability claims.

## Evidence on Hand

- Source requirements and staged implementation plan in `SMART_ECOMMERCE_CODEX_PLAN.md`.
- Stage 1 requirements, traceability, decisions, data plan, and architecture diagrams under `docs/`.
- Verified PostgreSQL and MongoDB product data foundation plus OpenAPI catalog contract.
- No logo, real catalog photography, private customer/order history, provider credential, testimonial, benchmark, or production deployment evidence is available. Future surfaces must not fabricate them.

## Product Principles

1. One commerce truth: stable IDs and explicit ownership across catalog and operational data.
2. Smart behavior must be observable, reproducible, and grounded in real application records or clearly labeled fixtures.
3. Customers see useful recovery states and only their own order/shipment information.
4. Operators can inspect automatic decisions, inputs, status, and limitations.
5. Arabic and English are equal product experiences, including layout direction and search/display behavior.

## Accessibility & Inclusion

Target WCAG 2.2 AA for the web application. All primary flows must work with keyboard navigation, visible focus, programmatic labels/errors, reduced motion, and correct RTL/LTR behavior. Voice and image search require equivalent text paths and explicit permission/error recovery.
