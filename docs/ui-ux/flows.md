# UI flows and state transitions

## Discovery, compare, and cart

```mermaid
flowchart LR
    A[Open catalog] --> B[Search or choose category]
    B --> C[Apply dynamic filters]
    C --> D{Results?}
    D -- No --> E[Explain active filters and clear/retry]
    D -- Yes --> F[Inspect product]
    F --> G[Add to comparison tray]
    G --> H[Compare aligned attributes]
    H --> I[Add selected item to cart]
    I --> J[Recheck authoritative price and availability]
    J --> K{Still valid?}
    K -- No --> L[Explain price/stock change]
    K -- Yes --> M[Cart ready]
```

## Image and voice search recovery

```mermaid
flowchart TB
    A[Choose image or voice mode] --> B{Permission/input valid?}
    B -- No --> C[Explain problem and expose text search]
    B -- Yes --> D[Process input]
    D --> E{Recognized/retrieved?}
    E -- No --> F[Editable transcript or no-match guidance]
    E -- Yes --> G[Catalog results]
    G --> H[Dynamic filters remain available]
```

## Checkout and pre-completion risk

```mermaid
stateDiagram-v2
    [*] --> Cart
    Cart --> PendingPayment: submit valid checkout
    PendingPayment --> PendingRisk: sandbox authorization prepared
    PendingPayment --> PaymentFailed: provider failure
    PendingRisk --> Confirmed: score below threshold
    PendingRisk --> Review: score at/above threshold
    PendingRisk --> Review: assessment failure
    Review --> Confirmed: authorized reviewer allows
    Review --> Cancelled: authorized reviewer declines
    Confirmed --> [*]
    PaymentFailed --> Cart: recover/retry
```

## Catalog publication/reconciliation

```mermaid
flowchart LR
    A[Create PostgreSQL draft ID] --> B[Write MongoDB catalog document]
    B --> C[Write price and inventory]
    C --> D{All counterparts valid?}
    D -- No --> E[Keep draft and show reconciliation action]
    D -- Yes --> F[Activate product]
    F --> G[Public catalog]
```

## Figma status

Figma wireframes and click-through links are pending external tool access. The approved comp, routes, controls, flows, and state requirements in this directory are the source-of-truth implementation specification until a Figma artifact is created and linked here.
