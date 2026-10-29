# Smart-eCommerce Management System — Codex Implementation Plan

Prepared from the two supplied project-specification photos on 27 October 2026.

## 1. How Codex must use this plan

Build the graduation project described in the source photos. Preserve its purpose, all seven smart modules, the Business Intelligence objective, the suggested technology choices, and the five implementation stages.

This document has two clearly separated kinds of content:

- **Source requirements:** requirements and technology options stated in the photos. They define the project scope.
- **Implementation breakdown:** proposed tasks, internal structures, verification checks, and supporting components needed to implement that scope. These are planning details, not additional claims about what the photos specify.

Do not remove requirements to produce a smaller MVP. Incremental delivery is allowed, but intermediate versions are not the completed project. Do not silently choose between technology alternatives or invent business policies. Record unresolved decisions and continue work that does not depend on them.

The original photos remain authoritative if a transcription or interpretation is disputed. Do not import requirements or technologies from another project, including Fledge.

## 2. Source requirements — project purpose and objectives

**Project name:** Smart-eCommerce Management System.

**Purpose:** Apply artificial intelligence and data analysis to develop an integrated platform combining management of commercial and marketing operations (**Back-Office / ERP**) with a smart, personalized customer experience (**Front-End / Storefront**).

| ID | Objective stated in the photos |
|---|---|
| OBJ-01 | Improve Customer Experience through accurate, personalized product recommendations and a smart shopping assistant. |
| OBJ-02 | Automate and improve commercial operations: inventory management, sales, and pricing using smart forecasting models. |
| OBJ-03 | Support decisions through Business Intelligence: interactive dashboards analyzing consumer behavior and the store’s financial performance. |

“Back-Office / ERP” describes the operational side of this project. The photos do not independently specify a complete accounting, payroll, HR, or enterprise ERP suite.

## 3. Source requirements — all system modules

### 3.1 Smart Storefront

| ID | Module | Required behavior from the photos |
|---|---|---|
| SF-01 | Smart Recommendation Engine | Use advanced Collaborative & Content-Based Filtering algorithms to recommend products based on purchase history and user browsing. Preserve both filtering approaches and both input sources. |
| SF-02 | AI Shopping Assistant / Chatbot | Answer customer inquiries, help track shipments, and help choose suitable products. All three functions are required. |
| SF-03 | Smart Search & Filtering | Support image search, voice search, and dynamic filters. All three capabilities are required. |

### 3.2 Smart Back-Office

| ID | Module | Required behavior from the photos |
|---|---|---|
| BO-01 | Predictive Inventory Control | Predict future demand levels and automatically reorder to avoid stockouts or excess inventory. Both forecasting and automatic reordering are required. |
| BO-02 | Dynamic Pricing Engine | Automatically adjust prices based on supply and demand, competitors’ costs, and shopping seasons. Preserve every named factor. |
| BO-03 | Customer Segmentation | Analyze customer behavior and classify customers using RFM: Recency, Frequency, Monetary, to target marketing campaigns accurately. |
| BO-04 | Fraud Detection | Analyze payment transactions to identify suspicious activities or stolen cards before order completion. |

**Wording that must not be silently changed:** the pricing line in the Arabic source says “وتكاليف المنافسين” — competitors’ costs. Whether the author intended competitors’ selling prices is an unresolved interpretation, not a correction Codex may make automatically.

**Cross-cutting requirement BI-01:** interactive dashboards for consumer behavior and financial performance, required by OBJ-03 even though not listed as an eighth smart module.

## 4. Source requirements — suggested technology stack

The photos label this stack as proposed/suggested. Preserve the options below; do not present an unchosen alternative as a confirmed decision.

| Layer | Technologies shown in the photos |
|---|---|
| Front-End (User Interface) | Next.js, React.js, Tailwind CSS |
| Back-End (Logic & API) | Node.js / Express or Python (FastAPI / Django) |
| Artificial Intelligence & ML | Python, Scikit-learn, TensorFlow / PyTorch, OpenAI API |
| Database | PostgreSQL / MySQL (Relational) + MongoDB (Product Catalog) |
| DevOps & Hosting | Docker, AWS / Vercel |

### Decisions to record before dependent implementation

1. Choose the main backend from the listed alternatives: Node.js with Express, Python with FastAPI, or Python with Django.
2. Choose PostgreSQL or MySQL for relational data. Retain MongoDB for the product catalog; the “+ MongoDB” is not a substitute for the relational database.
3. Choose TensorFlow or PyTorch for the relevant ML components. Retain Python, Scikit-learn, and the OpenAI API in the planned stack; document their responsibilities.
4. Resolve the AWS / Vercel hosting choice and the actual placement of the frontend, backend, model execution, scheduled work, and databases. Retain Docker.
5. Record actual dependency and runtime versions during setup after checking compatibility. The photos contain no version pins.

Codex should present a compact decision table when these choices become necessary. It should not introduce an unrelated stack. Existing repository choices may resolve an alternative if they match the supplied options and are clearly documented.

## 5. Source requirements — original project roadmap

Keep these five stages in this order:

| Stage | Source stage name | Required source deliverables / activities |
|---|---|---|
| 1 | System Analysis & Requirements | Prepare the Software Requirement Specifications (SRS) document and architectural diagrams: UML, ERD, and Data Flow Diagrams. |
| 2 | UI/UX & Database Architecture | Design initial UI wireframes and interactive diagrams/prototypes in Figma, and design the databases. |
| 3 | Core Development & AI Integration | Build business logic, train AI models, and connect them through APIs. |
| 4 | Testing & QA | Perform functional testing, security testing, and performance testing. |
| 5 | Deployment & Final Presentation | Deploy the system to cloud infrastructure and prepare the final presentation and user manual. |

The photos specify no deadline, sprint duration, team size, language of the interface, branding, or minimum model accuracy. Do not invent these as source requirements.

## 6. Implementation breakdown — Stage 1: System Analysis & Requirements

### Tasks

- [ ] Inspect the repository, if one exists, before modifying it. Identify useful existing work and any conflicts with the source scope.
- [ ] Create an SRS using OBJ-01–OBJ-03, SF-01–SF-03, BO-01–BO-04, and BI-01 as traceable identifiers.
- [ ] Describe customer and back-office user journeys. Define the minimum permissions needed by those journeys without inventing a larger role hierarchy.
- [ ] Document the proposed supporting commerce flow: product discovery → selection/cart → checkout/payment assessment → order → shipment tracking. These are implementation dependencies of the specified modules, not separately quoted source features.
- [ ] Specify inputs, outputs, failure behavior, and dependencies for every smart module.
- [ ] Identify the data needed for browsing history, purchases, catalog content/images, demand, stock, competitors’ costs, seasons, RFM, payment risk, and shipping status.
- [ ] Record data availability and distinguish real, public, synthetic, and sandbox data. Do not claim that generated demonstration data proves real-world model quality.
- [ ] Create UML use-case/component diagrams and sequence diagrams for the important workflows.
- [ ] Create the ERD and Data Flow Diagrams, including movement between the storefront, API, operational database, product catalog, AI components, and integrations.
- [ ] Create the decision register described in Section 13.
- [ ] Agree on measurable acceptance targets where the photos provide none, including model evaluation and performance targets.

### Planned outputs

`docs/SRS.md`, `docs/requirements-traceability.md`, `docs/decisions.md`, `docs/data-plan.md`, and diagrams under `docs/diagrams/`.

### Completion evidence

Every source requirement has a user journey, data dependency, and acceptance check. The SRS contains all seven modules and BI dashboards. Unresolved decisions are explicit rather than hidden in code.

## 7. Implementation breakdown — Stage 2: UI/UX & Database Architecture

### UI/UX work

- [ ] Create Figma wireframes and interactive flows for the storefront and back-office. If Figma access is unavailable, prepare the screen/interaction specification and mark the Figma deliverable pending; do not claim it is completed by unrelated screenshots.
- [ ] Cover product discovery, recommendations, image search, voice search, dynamic filters, product selection, customer questions, and shipment tracking.
- [ ] Cover demand forecasts, stock levels, automatic reorder records, pricing changes and their input factors, RFM segments, payment-risk review, and BI dashboards.
- [ ] Define empty, loading, failed, unauthorized, and insufficient-data states.
- [ ] Include browser microphone permission handling and invalid-image feedback in the search flow.
- [ ] Validate that screen designs expose all required functions. A visually complete dashboard alone is not functional completion.

### Proposed database responsibilities

These are implementation suggestions to refine through the ERD, not a source-prescribed schema.

| Storage | Proposed entities/data | Requirements supported |
|---|---|---|
| Relational database | Customer identities and purchase/order history; order items with historical price snapshots; payments and risk assessments; inventory balances/movements; shipments; reorder records; applied pricing history | SF-01, SF-02, BO-01, BO-02, BO-03, BO-04, BI-01 |
| Relational database, subject to volume/design decisions | Browsing events; demand forecasts; RFM snapshots; pricing input observations; model version references and evaluation records | SF-01, BO-01, BO-02, BO-03, BI-01 |
| MongoDB product catalog | Product descriptions, categories, attributes, image references, and catalog metadata | SF-01, SF-02, SF-03 |

- [ ] Define one stable product identifier shared across catalog and relational records.
- [ ] Define authoritative sources for stock, current prices, historical order prices, and catalog details. Avoid conflicting copies across databases.
- [ ] Define how catalog search obtains current prices and availability.
- [ ] Define retention and access for browsing, order, shipment, and payment-risk information.
- [ ] Design indexes, migrations/setup scripts, and seed data for the agreed schema.
- [ ] Decide where uploaded images and generated model artifacts live; the photos do not specify this.
- [ ] Define API contracts and error formats before frontend/backend integration.

### Completion evidence

Figma flows, database design, API contracts, and revised diagrams cover every source requirement. Cross-database references and ownership of each field are documented.

## 8. Implementation breakdown — Stage 3: Core Development & AI Integration

### 8.1 Foundation and supporting commerce flow

- [ ] Scaffold the chosen stack and document local setup, environment variables, and Docker execution.
- [ ] Connect the relational database and MongoDB product catalog.
- [ ] Implement the customer and back-office access boundaries needed for the specified features.
- [ ] Implement catalog access and the minimum order, payment, stock, and shipment records needed by the smart modules.
- [ ] Capture browsing and purchase events for recommendations, segmentation, forecasting, and BI.
- [ ] Add integration boundaries for payment, shipment tracking, and automatic reordering. Provider choices remain unresolved until recorded.
- [ ] Add reproducible demonstration data with enough history to exercise all modules.

Supporting features must remain limited to what the stated scope needs. Do not expand this into a marketplace, multi-vendor platform, mobile app, loyalty program, or complete ERP suite without a new instruction.

### 8.2 SF-01 — Smart Recommendation Engine

**Inputs:** user purchase history, browsing activity, and product catalog content.

**Build:**

- [ ] Prepare a reproducible interaction dataset with stable user/product references.
- [ ] Implement and train a collaborative filtering component.
- [ ] Implement a content-based filtering component using product characteristics and user interests.
- [ ] Define how both components contribute to recommendations; do not quietly use only one.
- [ ] Expose recommendations through an API and integrate them into the storefront.
- [ ] Handle users/products with insufficient history using a documented fallback. The fallback does not replace either required filtering method.
- [ ] Evaluate on held-out data and record ranking metrics, dataset provenance, and model version. Numerical success targets must be agreed, not invented.

**Acceptance:** recommendations actually depend on history and content; evidence demonstrates both filtering approaches and both purchase/browsing input sources. Displaying the same static products to everyone does not satisfy SF-01.

### 8.3 SF-02 — AI Shopping Assistant / Chatbot

**Inputs:** customer questions, catalog information, and authorized order/shipment records.

**Build:**

- [ ] Connect the OpenAI API to the assistant workflow; record the selected model and configuration during implementation.
- [ ] Provide catalog lookup for product-selection help.
- [ ] Provide the inquiry information source selected during requirements analysis.
- [ ] Provide shipment-status lookup scoped to the authenticated customer’s orders.
- [ ] Return grounded answers, product choices, and shipment status; show a useful response when source information is missing.
- [ ] Handle service failures and avoid exposing other customers’ data.

**Acceptance:** demonstrate a customer inquiry, a suitable-product request, and shipment tracking with actual application records. Test that an unauthorized order cannot be retrieved. A generic chat box without these integrations does not satisfy SF-02.

### 8.4 SF-03 — Smart Search & Filtering

**Inputs:** uploaded/query images, voice queries, and product attributes.

**Build:**

- [ ] Implement image processing and a retrieval method that searches the catalog by image content.
- [ ] Implement voice capture/transcription and connect the recognized query to catalog search.
- [ ] Implement dynamic filters that reflect available catalog attributes and the current search/result context.
- [ ] Make search modes and filters work together with the same product identifiers, prices, and availability.
- [ ] Handle unsupported microphone access, denied permissions, empty recognition, invalid image uploads, and no results.

**Acceptance:** an image returns relevant catalog matches; a spoken query returns appropriate results; changing filters updates results correctly. Plain text search alone does not satisfy SF-03.

### 8.5 BO-01 — Predictive Inventory Control

**Inputs:** historical demand/sales and current stock; operational reorder settings such as lead times and quantities must be defined separately.

**Build:**

- [ ] Prepare chronological training/evaluation datasets without using future information to predict the past.
- [ ] Train and evaluate a future-demand forecasting model.
- [ ] Make forecast horizons and update schedules explicit implementation settings.
- [ ] Connect forecasts to automatic reorder logic intended to avoid stockouts and overstock.
- [ ] Implement automatic creation/dispatch of reorder requests through the selected integration boundary.
- [ ] Prevent duplicate reorders when jobs retry and reflect pending replenishments in inventory planning.
- [ ] Show forecasts, current stock, and reorder execution/status in the back-office.

**Acceptance:** a controlled low-stock/high-demand scenario triggers a reorder automatically; repeated processing does not create duplicates; sufficient stock does not trigger unnecessary replenishment under the agreed policy. Forecast-only charts or manual reorder suggestions are insufficient.

For a demonstration, an explicitly labeled supplier simulator may be used while a real integration is unavailable. Record that limitation; do not describe simulated dispatch as a real supplier order.

### 8.6 BO-02 — Dynamic Pricing Engine

**Inputs required by the source:** supply and demand, competitors’ costs, and shopping seasons.

**Build:**

- [ ] Resolve the competitor-cost wording and data source before claiming the pricing logic is complete.
- [ ] Define data collection/import contracts for every required input.
- [ ] Implement the price calculation method and any forecasting component chosen in the SRS.
- [ ] Define update frequency and operational price constraints as explicit business decisions.
- [ ] Apply calculated price changes automatically to the authoritative current price.
- [ ] Preserve the price recorded for existing orders and define how in-progress checkout price changes are handled.
- [ ] Record old/new prices, timestamp, and contributing inputs for inspection in the back-office.

**Acceptance:** controlled changes to supply, demand, competitor-cost input, and shopping seasons produce the documented pricing behavior; the resulting price is applied automatically and visible in the storefront. A manual discount form does not satisfy BO-02.

### 8.7 BO-03 — Customer Segmentation

**Inputs:** purchase history, purchase dates, and monetary amounts.

**Build:**

- [ ] Calculate Recency, Frequency, and Monetary values.
- [ ] Document the reference date, observation period, included order statuses, treatment of refunds/cancellations, scoring boundaries, and segment definitions.
- [ ] Classify customers using all three RFM dimensions.
- [ ] Refresh segments from updated transaction data.
- [ ] Provide segment views and a way to select the relevant customer group for targeted marketing campaigns.

**Acceptance:** known purchase histories yield correct RFM values and expected segments under the documented scoring rules. Marketing users can identify/select a segment for campaign targeting. The photos do not specify an email/SMS provider or require building an entire campaign-delivery platform.

### 8.8 BO-04 — Fraud Detection

**Inputs:** payment transaction attributes and legally/operationally available risk signals, as established during requirements analysis.

**Build:**

- [ ] Define data sources and labels for suspicious transactions and stolen-card indicators.
- [ ] Train and evaluate the selected fraud-detection model using an appropriate held-out dataset.
- [ ] Integrate transaction assessment into the order flow before order completion.
- [ ] Persist risk results and expose necessary risk information in the back-office.
- [ ] Define the handling policy for flagged transactions and assessment failures; the photos do not specify automatic rejection, manual review, or thresholds.
- [ ] Evaluate false positives and false negatives; document data limitations. A model’s flag is a risk assessment, not proof that a card is stolen.
- [ ] Use sandbox/tokenized payment data for demonstrations; do not store card verification codes or seed real payment credentials.

**Acceptance:** suspicious test transactions are assessed and identified before their orders complete, ordinary cases follow the documented policy, and the completion flow cannot bypass required risk assessment. A fraud report generated after completion does not satisfy the specified timing.

### 8.9 BI-01 — Business Intelligence dashboards

**Inputs:** recorded customer behavior and financial transaction data.

**Build:**

- [ ] Implement interactive consumer-behavior and financial-performance dashboards.
- [ ] Define exact metric formulas and data sources in the SRS. Example candidates are product engagement, purchasing behavior, order value, sales, and refunds; these examples are not additional source requirements.
- [ ] Implement meaningful date/filter interactions and recompute displayed results accordingly.
- [ ] Reconcile financial totals with recorded transactions. Do not present profit unless the required cost data and formula are available.
- [ ] Display honest empty/insufficient-data states instead of fabricated statistics.

**Acceptance:** both consumer behavior and financial performance are represented, interactions change the displayed analysis, and results reconcile with the underlying data.

### Stage 3 integration order

Implement the commerce/data foundation first. Then deliver recommendations, assistant, and search against actual application data; deliver inventory, pricing, segmentation, and fraud against the same records; complete the cross-module BI views. Fraud assessment must be integrated before a checkout is treated as complete. Module-level tests accompany development even though full system QA remains Stage 4.

Record training scripts, preprocessing, data provenance, evaluation results, model artifacts/versions, and API contracts. Hardcoded responses and untrained placeholders must never be reported as completed AI integration.

## 9. Implementation breakdown — Stage 4: Testing & QA

### Functional verification matrix

| Requirement | Required evidence |
|---|---|
| OBJ-01 | Personalized recommendations and all assistant functions work in customer journeys. |
| OBJ-02 | Inventory, sales/order data, and automatic pricing operate together with the implemented prediction components. |
| OBJ-03 / BI-01 | Interactive consumer-behavior and financial-performance analysis uses real application records. |
| SF-01 | Collaborative and content-based recommendations use purchase and browsing history. |
| SF-02 | Inquiry response, suitable-product help, shipment tracking, and order-access isolation pass. |
| SF-03 | Image search, voice search, and dynamic filtering pass individually and together. |
| BO-01 | Future-demand prediction, automatic reorder, duplicate prevention, and adequate-stock scenarios pass. |
| BO-02 | All named pricing factors influence the defined calculation and automatic price application works. |
| BO-03 | Correct RFM values/segments and targeted group selection are demonstrated. |
| BO-04 | Payment assessment executes before completion; flagged and failure cases follow the defined policy. |

### Security testing

- [ ] Verify customer/back-office authorization and isolation of customer orders and shipments.
- [ ] Test malicious image uploads, invalid inputs, and injection attempts at relevant interfaces.
- [ ] Test that chatbot instructions cannot grant unauthorized access or expose confidential records.
- [ ] Verify secrets are not committed or exposed to browser clients.
- [ ] Verify sensitive payment data is handled only through the chosen integration design.

### Performance and reliability testing

- [ ] Measure catalog/search, recommendation, assistant, and checkout/risk-assessment latency against the agreed targets.
- [ ] Check background forecasting, segmentation, and price-update behavior under the agreed workload.
- [ ] Test external service failures, missing model/data artifacts, retry behavior, and database unavailability where relevant.
- [ ] Verify state consistency across stock, current prices, order snapshots, and catalog records.

### AI evaluation

- [ ] Evaluate recommendation ranking quality, image-search relevance, voice-query recognition, forecast error, and fraud classification quality using documented datasets.
- [ ] Check chatbot answers against known inquiry, catalog, and shipment facts.
- [ ] Record limitations caused by synthetic data, small datasets, unavailable competitor-cost information, or simulated integrations.

### Completion evidence

A test report maps every source requirement to a result and reproducible evidence. Report failed, blocked, or simulated capabilities explicitly. Passing UI screenshots alone does not establish functional completion.

## 10. Implementation breakdown — Stage 5: Deployment & Final Presentation

- [ ] Package the system using Docker as planned.
- [ ] Deploy the agreed components to the chosen AWS / Vercel arrangement.
- [ ] Configure databases, secrets, model artifacts, scheduled jobs, and external integration credentials.
- [ ] Run cloud smoke tests covering storefront, back-office, databases, and all smart-module integrations.
- [ ] Document startup, deployment, database setup, retraining, and recovery procedures needed to reproduce the result.
- [ ] Prepare the final presentation with the original objectives, architecture, all seven modules, BI, evaluation results, and clearly stated limitations.
- [ ] Prepare a user manual for both customers and back-office users.
- [ ] Prepare a demo script that exercises every required capability using known data.

**Completion evidence:** deployed system, reproducible source/setup instructions, presentation, user manual, and a requirement-linked demonstration. Hosting choice alone does not satisfy actual deployment.

## 11. Proposed repository organization

This organization is a planning aid and can be adapted to the selected backend without changing scope.

```text
apps/storefront/          Next.js / React.js / Tailwind customer interface
apps/backoffice/          Back-office interface; may share the same Next.js app
services/api/            Selected backend and business logic
services/ai/             Python AI components and API integration
ml/training/             Reproducible training and preprocessing
ml/evaluation/           Evaluation scripts and metric definitions
database/relational/     Relational schema, migrations, seed scripts
database/catalog/        MongoDB catalog setup and indexes
tests/                   Unit, integration, end-to-end, security, performance
infra/                   Docker and selected cloud deployment configuration
docs/SRS.md
docs/decisions.md
docs/data-plan.md
docs/requirements-traceability.md
docs/diagrams/
docs/ui-ux/              Figma links, exports, and interaction specifications
docs/test-report.md
docs/deployment.md
docs/user-manual.md
docs/demo-script.md
docs/progress.md
```

These folders do not mandate separate deployments or microservices. If the backend is Python, AI code can share that service when appropriate. Choose a practical arrangement within the listed stack and document it.

## 12. Codex execution protocol

For each implementation task:

1. Read the relevant requirement and decision entries.
2. Check dependencies and identify the smallest useful increment that advances that requirement.
3. Implement the increment with real data/API integration where available.
4. Run the tests appropriate to the affected behavior and record the result.
5. Update the requirement traceability and progress files, including unresolved blockers.
6. Continue to the next unblocked task in the current stage.

Use these status meanings consistently:

- **Not started:** no implementation exists.
- **In progress:** work exists but required behavior/evidence is incomplete.
- **Blocked:** a concrete decision, dataset, credential, or external access is missing.
- **Implemented:** behavior exists but final acceptance has not yet been verified.
- **Verified:** acceptance checks pass with recorded evidence.

Do not mark a module verified if its only implementation is static UI, mock responses, or an unavailable integration. If a sandbox is the agreed demonstration environment, state exactly what it verifies and what remains unverified in production.

Do not repeatedly ask for routine engineering preferences. Ask only when an unresolved choice changes the source meaning, technology branch, or business behavior. Continue independent documentation/design work while such decisions are pending.

## 13. Decision register — unspecified details to resolve

These gaps do not change the requirements; resolving them makes the implementation concrete.

| Decision | Why it is needed | Dependent work |
|---|---|---|
| Backend, relational database, ML framework, hosting alternatives | Photos list options rather than final selections | Scaffolding and deployment architecture |
| Interface language, store domain/product categories, currency, timezone | Not specified in photos | Final UI copy, catalog, date/money calculations |
| Customer/back-office permissions | Needed to enforce access to required functions | Authentication and authorization |
| Available historical/catalog/image/payment-risk datasets | Required for training and credible evaluation | AI pipelines and evaluation |
| Meaning and availability of competitors’ costs | Source wording must not be silently replaced | Dynamic pricing |
| Shopping-season definitions and price constraints | Needed for reproducible automatic prices | Pricing policies |
| Demand horizon, supplier lead times, reorder quantities and integration | Needed to operationalize automatic replenishment | Inventory automation |
| Payment provider and sandbox/live demo scope | Not specified in photos | Transaction/risk integration |
| Fraud thresholds and flagged/failure handling | Detection is required; response policy is unspecified | Order completion workflow |
| Shipment provider or tracking-data source | Needed for grounded tracking answers | Shopping assistant |
| RFM period, scoring boundaries, segments, refund policy | Needed for repeatable classification | Segmentation |
| Inquiry knowledge source and voice/image processing approach | Required capabilities do not specify these methods/providers | Assistant and search |
| Financial metric definitions and available cost data | “Financial performance” is an objective, not a metric formula | BI dashboards |
| Model-quality and performance targets, expected workload | Photos contain no numerical targets | QA acceptance |
| Team capacity, deadline, and final presentation format | Not given; avoid invented scheduling commitments | Calendar/sprint allocation and presentation packaging |

## 14. Final definition of done

- [ ] The integrated storefront and back-office fulfill all three original objectives.
- [ ] All seven smart modules are implemented and verified with every listed sub-capability preserved.
- [ ] Interactive BI dashboards cover consumer behavior and financial performance.
- [ ] Technology selections are recorded within the alternatives shown in the photos; MongoDB remains the product catalog database.
- [ ] SRS, UML, ERD, and Data Flow Diagrams are delivered.
- [ ] Figma wireframes/interactive flows and database design are delivered.
- [ ] Business logic, trained AI models, and API integration are delivered.
- [ ] Functional, security, and performance test results are delivered.
- [ ] Cloud deployment, final presentation, and user manual are delivered.
- [ ] Missing data, simulations, blocked integrations, and evaluation limitations are disclosed accurately.
- [ ] No source requirement has been silently removed, renamed into a different feature, or deferred beyond the claimed completed project.

## 15. Starter prompt to give Codex

```text
Read docs/source-specification-plan.md completely and use it as the implementation
plan for the Smart-eCommerce Management System graduation project.

Preserve every source requirement, all seven smart modules, the BI objective,
the supplied technology alternatives, and all five roadmap stages. Distinguish
source requirements from proposed implementation details. Do not reduce scope
to an MVP or substitute static interfaces for working features.

Start with Stage 1. Inspect the existing repository, if any. Create the SRS,
requirements traceability, decision register, data plan, UML, ERD, and Data Flow
Diagrams. Identify unresolved choices without silently selecting a technology
branch or changing business meaning. Continue all work independent of those
choices and ask a concise grouped question when a decision blocks progress.

Then proceed through the stages in order, updating docs/progress.md and the
traceability matrix as you implement and test. Report actual evidence, blockers,
and simulations honestly. Do not claim the project is complete until the final
definition of done is satisfied.
```
