# Smart-eCommerce Management System — Software Requirements Specification

| Field | Value |
|---|---|
| Status | Accepted Stage 1 baseline; Stage 3 implementation and Stage 4 QA complete |
| Source | `docs/source-specification-plan.md` |
| Last updated | 2026-10-29 |
| Scope | Storefront, supporting commerce flow, seven smart modules, and BI dashboards |

## 1. Purpose and scope

The system is an integrated commerce platform that combines a personalized customer storefront with back-office commercial and marketing operations. Artificial intelligence and data analysis support customer experience, operational automation, and business decisions.

The source scope contains three objectives:

- **OBJ-01:** improve customer experience with personalized recommendations and a shopping assistant.
- **OBJ-02:** automate inventory, sales-related operations, and pricing using forecasting and smart models.
- **OBJ-03:** support decisions through interactive consumer-behavior and financial-performance dashboards.

The supporting commerce flow is an implementation dependency rather than an additional source feature:

`product discovery → selection/cart → checkout/payment assessment → order → shipment tracking`

The system is not a marketplace, multi-vendor platform, mobile application, loyalty platform, or full accounting/HR/payroll ERP suite.

## 2. Users and access boundaries

Only the minimum actors needed by the specified journeys are defined.

| Actor | Required access |
|---|---|
| Customer | Browse/search products; manage a cart; check out; view own orders and shipments; receive recommendations; use the assistant. |
| Back-office user | View and operate inventory, reorder, pricing, segmentation, risk, and BI functions according to assigned permissions. |
| Background worker | Run approved forecasting, reorder, pricing, segmentation, and model jobs using service credentials. It is not a human role. |
| External integration | Provide payment/risk, shipment, supplier/reorder, AI, or hosting capabilities through a documented boundary. |

Authorization rules:

1. A customer may access only their own order and shipment data.
2. Back-office capabilities are not exposed through customer permissions.
3. Automated jobs receive only the data and write privileges needed for their task.
4. Risk assessment must complete according to the agreed failure policy before an order can complete.
5. **DEC-006** uses customer ownership plus explicit back-office capability scopes; these boundaries apply to every implementation increment.

## 3. Customer and operational journeys

### JRN-01 — Discover and purchase

1. The customer browses or searches the catalog using text, image, voice, and contextual filters.
2. The storefront returns catalog data joined to authoritative current price and availability.
3. The customer selects products and places them in a cart.
4. Checkout creates a pending transaction and requests pre-completion risk assessment.
5. The order completes only under the agreed fraud and payment policy.
6. Stock, order-price snapshots, payment/risk results, and shipment records remain traceable.

### JRN-02 — Receive personalized help

1. The storefront records authorized browsing and purchase interactions.
2. The customer receives recommendations derived from collaborative and content-based components.
3. The assistant answers inquiries, helps choose catalog products, and retrieves shipment status only for the authenticated customer's order.

### JRN-03 — Operate inventory and pricing

1. A back-office user reviews demand forecasts, stock, and pending replenishments.
2. The system creates an idempotent reorder when the agreed policy requires it.
3. The pricing process evaluates supply, demand, competitors' costs, and shopping seasons.
4. Approved automatic price changes update the authoritative current price and create an audit record without changing historical order prices.

### JRN-04 — Segment and analyze

1. The system calculates Recency, Frequency, and Monetary values from eligible orders.
2. Back-office users inspect/select segments for campaign targeting.
3. Interactive dashboards analyze consumer behavior and financial performance from recorded application data.

## 4. Functional requirements

### SF-01 — Smart Recommendation Engine

- **Inputs:** purchase history, browsing activity, stable customer/product identifiers, and catalog content.
- **Processing:** train and serve both collaborative-filtering and content-based components; document how their results are combined; provide a documented cold-start fallback.
- **Outputs:** ranked product recommendations with model/version provenance.
- **Failures:** return an honest fallback or insufficient-data state when history, catalog features, or a model artifact is unavailable; do not claim personalization for a static list.
- **Dependencies:** consent/retention policy, event capture, catalog, order history, model pipeline, evaluation dataset, and serving API.
- **Acceptance:** evidence shows both required filtering approaches and both purchase and browsing inputs affect results; ranking metrics are evaluated against an agreed target on held-out data.

### SF-02 — AI Shopping Assistant / Chatbot

- **Inputs:** customer questions, approved inquiry knowledge, catalog data, authenticated identity, and authorized order/shipment records.
- **Processing:** use the OpenAI API with tools or application services for grounded catalog and shipment lookup.
- **Outputs:** grounded inquiry answers, suitable-product suggestions, and shipment status.
- **Failures:** state when information is unavailable; handle provider/tool failure; never expose another customer's data or treat prompt text as authorization.
- **Dependencies:** **DEC-003**, **DEC-012**, catalog API, identity/access control, order API, and shipment source.
- **Acceptance:** demonstrate a general inquiry, a catalog-grounded product request, an own-order shipment lookup, and denial of another customer's order.

### SF-03 — Smart Search & Filtering

- **Inputs:** uploaded images, microphone/voice input, recognized text, and catalog attributes.
- **Processing:** retrieve products by image content, transcribe voice and search the catalog, and compute dynamic filters for the current result context.
- **Outputs:** relevant catalog results using consistent product identifiers, current prices, and availability.
- **Failures:** handle denied/unsupported microphone access, empty recognition, invalid or malicious images, unavailable processing, and no results.
- **Dependencies:** **DEC-012**, product images/attributes, safe upload pipeline, speech and image-processing components, catalog query API.
- **Acceptance:** a known image and spoken query return relevant results, and changing a filter correctly changes the result set; modes work together.

### BO-01 — Predictive Inventory Control

- **Inputs:** chronological sales/demand history, current stock, pending replenishment, lead time, forecast horizon, and reorder rules.
- **Processing:** forecast future demand without temporal leakage and automatically create/dispatch an idempotent reorder when policy conditions are met.
- **Outputs:** forecasts, reorder records/status, and an operational audit trail.
- **Failures:** retries must not duplicate reorders; missing/stale inputs and supplier failure must be visible; pending replenishment must influence subsequent decisions.
- **Dependencies:** **DEC-008**, order/inventory data, scheduler, supplier boundary, model pipeline.
- **Acceptance:** controlled low-stock/high-demand data triggers one reorder across retries; adequate stock does not trigger one under the agreed policy.

### BO-02 — Dynamic Pricing Engine

- **Inputs:** supply, demand, competitors' costs, shopping seasons, and agreed operational price constraints.
- **Processing:** calculate and automatically apply prices on the agreed schedule; retain the inputs and calculation version.
- **Outputs:** authoritative current price plus immutable old/new price audit records.
- **Failures:** do not update on incomplete or invalid mandatory inputs unless an explicitly agreed fallback permits it; report stale/unavailable sources.
- **Dependencies:** **DEC-007**, **DEC-009**, inventory/demand data, competitor-cost source, season calendar, price authority.
- **Acceptance:** controlled changes to every named input produce documented behavior and the applied price appears in the storefront without altering historical order snapshots.

### BO-03 — Customer Segmentation

- **Inputs:** eligible order dates, statuses, refunds/cancellations, and monetary amounts.
- **Processing:** calculate all RFM dimensions and classify customers using documented scoring boundaries and a reproducible reference date.
- **Outputs:** versioned RFM snapshots, segment assignments, and selectable customer groups.
- **Failures:** insufficient or excluded histories are labeled; invalid monetary/order data is reported rather than silently classified.
- **Dependencies:** **DEC-011**, order history, customer identifiers, scheduler.
- **Acceptance:** fixture histories yield expected RFM values/segments and a back-office user can select the resulting group for campaign targeting.

### BO-04 — Fraud Detection

- **Inputs:** sandbox/tokenized payment attributes and legally/operationally available risk signals with documented labels.
- **Processing:** assess the transaction before order completion and persist the model/rule result.
- **Outputs:** risk score/classification, reasons available under the agreed design, assessment version, and handling status.
- **Failures:** timeout/unavailability follows an explicit fail-open, fail-closed, or review policy; the completion path cannot bypass required assessment.
- **Dependencies:** **DEC-010**, payment sandbox/provider, labeled evaluation data, checkout state machine, risk model.
- **Acceptance:** suspicious fixtures are identified before completion, ordinary fixtures follow policy, failure behavior is demonstrated, and false-positive/negative metrics are reported.

### BI-01 — Interactive dashboards

- **Inputs:** recorded browsing/customer behavior and authoritative financial transaction records.
- **Processing:** calculate documented metrics and recompute them for meaningful date and dimension filters.
- **Outputs:** interactive consumer-behavior and financial-performance views with data timestamps and honest empty/insufficient-data states.
- **Failures:** unavailable or incomplete sources are disclosed; profit is not displayed without the required cost data and formula.
- **Dependencies:** **DEC-013**, event/order/payment/refund data, metric contracts, access control.
- **Acceptance:** both required analysis areas are present, filter interactions change results, and totals reconcile to source transactions.

## 5. Supporting commerce and identity requirements

| ID | Requirement | Acceptance check |
|---|---|---|
| COM-01 | Expose product discovery and stable product selection against the product catalog. | Catalog items resolve to one stable product ID across catalog, pricing, stock, and orders. |
| COM-02 | Maintain a customer cart sufficient for checkout. | Quantities and selected products survive the defined session boundary and invalid items are rejected. |
| COM-03 | Create a pending checkout/payment assessment before completing an order. | No completion transition exists that skips the required BO-04 assessment. |
| COM-04 | Store order items with historical price snapshots. | Later pricing changes do not alter completed order totals. |
| COM-05 | Track shipment status for authorized assistant/customer lookup. | Own-order status is returned; cross-customer access is denied. |
| COM-06 | Record browsing and purchase events for downstream modules. | Events contain stable customer/session and product references plus timestamps and provenance. |
| COM-07 | Authenticate customers and operators on separate surfaces with revocable sessions. | Credentials are verified server-side; customer and operator sessions are independent, expire, and revoke on sign-out; cart, checkout, account, orders, and the back office require the matching session while catalog browsing stays public. |
| COM-08 | Let an operator locate and inspect any customer order without customer credentials. | The back-office order queue and detail return status, customer identity, shipping contact, line items, and shipment context under `orders:read`; customer-owned routes stay closed to operator tokens and back-office routes stay closed to customer tokens. |
| COM-09 | Let an operator fulfil, cancel, refund, and adjust stock with an auditable record. | Shipment status advances only through the declared state machine; cancellation restores only stock the order consumed; refunds never exceed the remaining total and leave the subtotal unchanged; every action records the acting operator. |
| COM-10 | Let a customer rotate their own password without an email loop. | The current password is required; the new one must differ and meet the length rule; other sessions of the same principal end while the calling session stays valid. |
| COM-11 | Let a customer cancel their own order before it ships, with a recorded reason. | Cancellation is ownership-scoped and refused after shipping; the reason is a fixed code plus free text for `other`; stock is restored only for what the order consumed; the cancellation is attributed to the customer. |
| COM-12 | Let a customer save delivery addresses and reuse the default at checkout. | At most one default per customer; the first saved address becomes it; deleting the default promotes a survivor; checkout preselects it and only saves a new address when asked; order history never reads the book. |
| COM-13 | Let a customer repeat a past order into the cart. | Lines are re-priced at add time; unavailable lines and capped quantities are reported, never silently dropped; one customer cannot reorder another's order. |

## 6. Data and integration requirements

1. One stable product identifier must connect MongoDB catalog documents to relational price, stock, interaction, order, and model records.
2. Authoritative ownership must be defined for catalog details, stock, current price, order-price snapshots, payments, risk results, and shipments.
3. Provenance must distinguish real, public, synthetic, and sandbox data; see [data-plan.md](data-plan.md).
4. Secrets and payment credentials must not be committed or sent to browser clients. Card verification codes and real payment credentials must never be seeded.
5. External service calls need timeouts, safe retries where applicable, and explicit error states.
6. Training/evaluation records must identify dataset snapshot, preprocessing/code version, parameters, metrics, and model artifact version.

## 7. Quality requirements and baseline targets

The source defines no numeric targets. The following project baselines are accepted under **DEC-014** and must be revised if representative datasets or deployment measurements show they are unsuitable.

| Area | Requirement now | Target status |
|---|---|---|
| Security | Enforce customer isolation, least privilege, upload validation, secret handling, session revocation, and pre-completion risk assessment. | Zero cross-customer authorization successes in the required isolation suite; no raw card credentials/CVV stored; expired or revoked sessions are rejected. |
| Performance | Measure at up to 10 requests/s and 100 concurrent sessions with the documented fixture size. | Catalog/search p95 ≤500 ms; checkout/risk application processing p95 ≤2 s excluding external-provider time; assistant p95 ≤5 s excluding upstream outage/retry. |
| Reliability | Exercise retry/idempotency, missing model/data, dependency failure, and database-unavailable behavior. | Duplicate reorder/order side effects: zero; every required dependency failure produces the documented state/error. |
| Recommendations | Evaluate both required approaches on held-out interactions. | Hybrid nDCG@10 at least 10% above the popularity baseline; report Recall@10 and coverage. |
| Image and voice search | Evaluate known labeled queries. | Image Recall@5 ≥0.80 and voice intent/query accuracy ≥0.90 on the documented project test set. |
| Forecast and fraud | Evaluate chronological demand and held-out payment-risk fixtures. | Forecast MAPE ≤25% on non-zero-demand series; fraud recall ≥0.80 and false-positive rate ≤0.10. |
| Auditability | Retain applied prices, risk assessments, reorder actions, model versions, and material input provenance. | Every automated test decision links to its inputs/config/model version; demo retention follows the DEC-005–017 baseline. |
| Accessibility | Storefront and back-office interactions must be keyboard-usable and expose labels/errors programmatically. | WCAG 2.2 AA automated checks plus keyboard, focus, RTL/LTR, reduced-motion, and screen-reader smoke tests. |

## 8. Selected technology stack

The user accepted these selections from the source options on 2026-10-27; see [decisions.md](decisions.md):

- Next.js, React, and Tailwind CSS for one storefront/back-office frontend.
- Python + FastAPI for the modular backend and AI integration.
- Python, Scikit-learn, PyTorch, and the OpenAI API for the documented AI/ML responsibilities.
- PostgreSQL for operational data and MongoDB for descriptive product catalog data.
- Docker and AWS for packaging and hosting; exact AWS service placement remains pending.

Stage 2 covers the complete physical data baseline, UI/interaction specification, and [API contracts](api/README.md). The first Stage 3 slice implements composed catalog reads using the pinned FastAPI runtime in `services/api`.

## 9. Requirement status and verification

This SRS is the accepted Stage 1 baseline. Software status is maintained per requirement in [requirements-traceability.md](requirements-traceability.md); completed design or schema work is not presented as completed smart-module behavior. Architecture views are under [diagrams/](diagrams/README.md), and decisions are in [decisions.md](decisions.md).
