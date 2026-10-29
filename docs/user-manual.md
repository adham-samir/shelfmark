# User manual

Two audiences: **customers** on the storefront and **back-office users** on the
operations pages. The interface is Arabic-first (RTL) with an English switch in
the header; both languages have the same capabilities.

All data in this deployment is synthetic and labelled as such. Prices, stock,
ratings, and events are demonstration records, not real commerce.

## Customer guide

### Sign in (demo identity harness)
1. Open `/login` to sign in, or `/register` to create a customer account. Both
   pages accept a `next` destination for the action that sent you there.
2. Seeded demo accounts (the password is shown after the slash):
   - `customer@example.invalid` / `demo-customer-1`
   - `other-customer@example.invalid` / `demo-customer-2`
   - `operator@example.invalid` / `demo-operator-1` (back office only)
3. Registration asks for a display name, email, and password (at least 8
   characters); the preferred locale starts as the current interface language
   and can be changed later in `/account`. These are local `.invalid`
   demonstration accounts, not a production identity provider (DEC-017).
4. Catalog browsing stays public. Cart, checkout, the assistant, account pages,
   and order pages require a customer session; visiting one signed out redirects
   to `/login?next=…`.
5. Signed-in customers get `/account` (profile and recent orders) and
   `/account/orders` (paged order history). Sign out from the account page.

### Find products
1. Open `/`. The catalog lists products with price, availability, and attributes.
2. Use the search field, the category list, or the filter rail (attribute,
   availability, price range) to narrow results.
3. Change sort order (relevance, price, name) and page size from the results
   toolbar; switch between grid and list views.

### Compare products
Tick **Compare** on up to four products. The tray keeps your selection while you
keep browsing; open `/compare` for a side-by-side table that marks missing values
explicitly.

### Search by image or voice
- `/search/image`: upload a JPEG, PNG, or WebP under 5 MiB. Invalid, oversized, or
  mislabeled files show a specific message; matches appear as normal product
  results and you can keep filtering them.
- `/search/voice`: allow microphone access, speak, then edit the transcript before
  searching. If the browser denies access or the provider is unavailable, the
  page explains why and offers text search instead.

### Ask the assistant
`/assistant` answers questions about products, policies, and **your own** order
shipments. It never returns another customer's order. If the provider key is not
configured, the page states that the assistant is unavailable rather than
inventing an answer.

### Buy something
1. Sign in as a customer, then add products to the cart (`/cart`) and adjust
   quantities.
2. Open `/checkout`, enter recipient name, phone, city, and address.
3. Submit with a sandbox payment token. The order is assessed **before**
   completion:
   - passed assessment → order confirmed and a shipment record is created;
   - flagged assessment → order waits in review; you can still open it from
     `/orders/{id}`;
   - assessment failure → the order waits in review as well.
4. `/orders/{id}` shows items, the price you paid, risk handling status, and the
   shipment timeline. Prices on past orders never change when prices are updated.

## Back-office guide

Sign in at `/backoffice/login` with the operator demo account
(`operator@example.invalid` / `demo-operator-1`). The operator session is
independent of any customer session and is required by every `/backoffice` page.
The navigation, signed-in name, language switch, and sign-out control are in the
back-office shell. The customer header contains no back-office link, so open
`/backoffice/login` directly. Each page states which capability it needs and shows a
specific message when it is missing.

### Order queue — `/backoffice/orders` (`orders:read`)
- Lists every customer order, newest first, with the customer, status, item
  count, subtotal, and creation time. Filter by status and page through results.
- Open an order to see the customer, delivery contact, line items with the prices
  paid, refunds, and the shipment timeline.
- A risk-review order links to the order detail, and the risk page links back.
- Operators still cannot use the customer routes (`/v1/orders`); the queue is the
  supported way to read orders.

### Order management — the same detail page (`orders:write`)
- **Shipment**: the available next steps depend on the current state —
  `pending → ready → in_transit → delivered`, with **Record exception** available
  from the open states and **Resume as ready** from an exception. Illegal moves
  are refused with a message, never silently skipped.
- **Cancel order**: only before delivery. It restores the stock this order
  actually took, voids the sandbox payment, and writes an audited cancellation
  record. Seeded historical orders have no stock ledger, so cancelling one
  restores nothing.
- **Refund**: enter an amount up to the remaining refundable total and a reason.
  Partial refunds keep the order status; a full refund marks it refunded. The
  order subtotal never changes.
- Every action is attributed to the signed-in operator in the shipment timeline
  or the adjustment record.

### Inventory planning — `/backoffice/inventory` (`inventory:write`)
- Read current, reserved, and available stock, the 14-day forecast, the reorder
  point, the 21-day target, and pending supply.
- **Run forecast and reorder** executes the same job the daily scheduler runs.
- **Adjust stock** records a signed quantity change with a reason. It is refused
  if it would leave less stock than is reserved, and it appears as an audited
  `adjustment` movement.
- Statuses: planned, supply pending, supplier simulator failed, forecast
  unavailable. Failed supplier attempts are preserved for retry, and reruns do not
  duplicate reorders.

### Dynamic pricing — `/backoffice/pricing` (`pricing:write`)
- Each row shows the current price, recorded cost, supply, demand, competitor
  cost, input freshness, the proposed price with its delta, and the last applied
  change.
- **Run pricing** applies bounded changes: at most ±20% per run, never below
  recorded cost + 5%. Inputs older than 24 hours block a change instead of pricing
  on stale data, and one observation can never produce two changes.
- **Import pricing observation** records cost, supply, demand, and competitor cost
  for an active product; the next run uses them.
- The audit trail keeps the old price, new price, calculation version, and the
  full input snapshot.

### Customer segmentation — `/backoffice/segments` (`segments:read`)
- Run segmentation to build an RFM snapshot for the current reference date.
- Six segments (Champions, Loyal, Potential, New, At Risk, Hibernating) come from
  documented score rules; click a card to filter members.
- Members show recency, frequency, monetary value, and the three scores. Customers
  without enough history are counted separately, never scored as zero.
- **Download CSV** exports the selected group for a campaign.

### Payment risk review — `/backoffice/risk` (`risk:review`)
- The queue lists orders that crossed the risk threshold or whose assessment
  failed, with the score, model version, and the signals that fired.
- **Allow** confirms the order and creates its shipment; **Decline** cancels it.
  Each decision is recorded once and cannot be repeated.
- The side panel shows the model card: threshold, holdout recall, precision,
  false-positive rate, PR-AUC, features, and limitations.

### Analytics — `/backoffice/analytics` (`analytics:read`)
- Set a date range (up to 366 days) and optionally a category, then apply.
- Consumer panel: product views, sessions, add-to-carts, created orders, orders per
  session, unfulfilled orders.
- Financial panel: order count, gross sales, refunds, net sales, average order
  value. Profit is deliberately omitted because no complete cost coverage exists.
- The daily trend shows views per day and marks days with orders; top products list
  views, add-to-carts, units, and revenue.
- Reconciliation compares reported totals with values recomputed from order lines;
  a mismatch is shown rather than hidden.

## Keyboard and accessibility

- Every control is reachable by keyboard; focus is visible and returns to the
  trigger after dialogs close.
- Status is never conveyed by colour alone: chips carry text, and tables use row
  and column headers.
- Arabic and English set the document language and direction; technical tokens
  (IDs, model names, signal names) are isolated left-to-right.

## Troubleshooting

| Symptom | Meaning | Action |
|---|---|---|
| “Operator session unavailable” | The operator session cookie is missing, expired, or revoked | Sign in again at `/backoffice/login`; check `SMART_ECOMMERCE_API_URL` |
| Sign-in returns to the same page | The session cookie was not set or the API rejected the credentials | Use the seeded demo credentials; confirm the storefront and API share the same host and the API is reachable |
| “Permission required” | The operator lacks the page's capability | Grant the listed capability |
| “Dependency unavailable” (503) | A database or model artifact is missing | Check `/health/ready` and the artifact paths |
| Empty analytics or segment page | No records in the selected range | Widen the range or run the corresponding job |
| Assistant or voice “provider unavailable” | No `OPENAI_API_KEY` | Set the key to enable those surfaces |