# Data Flow Diagrams

## Level 0 — system context

```mermaid
flowchart LR
    customer[Customer]
    operator[Back-office user]
    platform((Smart-eCommerce platform))
    payment[Payment / risk inputs]
    shipment[Shipment provider/source]
    supplier[Supplier / reorder boundary]
    openai[OpenAI API]

    customer -->|searches, questions, cart, payment token| platform
    platform -->|products, recommendations, answers, order/shipment state| customer
    operator -->|policies, review and analysis requests| platform
    platform -->|forecasts, reorders, prices, segments, risk, BI| operator
    platform <-->|authorization result and tokenized signals| payment
    platform <-->|authorized tracking reference and status| shipment
    platform <-->|idempotent reorder request and status| supplier
    platform <-->|grounded prompt/tool result and response| openai
```

## Level 1 — stores, processes, and integrations

```mermaid
flowchart TB
    customer[Customer]
    operator[Back-office user]

    p1((P1 Catalog, search and assistant))
    p2((P2 Cart, checkout, risk and order))
    p3((P3 Recommendation pipeline))
    p4((P4 Forecast and automatic reorder))
    p5((P5 Dynamic pricing))
    p6((P6 RFM segmentation))
    p7((P7 BI analysis))

    d1[(D1 MongoDB catalog)]
    d2[(D2 Operational relational data)]
    d3[(D3 Interactions and analytical records)]
    d4[(D4 Model artifacts and evaluations)]

    integrations[Payment, shipment, supplier, OpenAI, speech/image boundaries]

    customer -->|query/image/voice/question| p1
    p1 -->|results/help/status| customer
    customer -->|cart and tokenized checkout data| p2
    p2 -->|order outcome| customer
    operator -->|analysis and operations| p4
    operator -->|pricing operations| p5
    operator -->|segment selection| p6
    operator -->|filters| p7

    p1 <-->|catalog content/images| d1
    p1 <-->|price, stock, authorized order/shipment reference| d2
    p1 -->|browsing events| d3
    p1 <-->|provider request/result| integrations

    p2 <-->|pending order, price snapshots, payment/risk, stock, shipment| d2
    p2 <-->|authorization/risk/shipment| integrations
    p2 -->|purchase events| d3

    p3 <-->|purchase and browsing history| d3
    p3 <-->|product features| d1
    p3 <-->|model/version| d4
    p3 -->|ranked recommendations| p1

    p4 <-->|sales, stock, forecasts, reorders| d2
    p4 <-->|model/version| d4
    p4 <-->|reorder dispatch/status| integrations

    p5 <-->|supply, demand, competitor costs, seasons, price history| d2
    p5 -->|authoritative current price| p1

    p6 <-->|eligible orders and RFM snapshots| d2
    p6 -->|segment analytical data| d3

    p7 <-->|consumer behavior| d3
    p7 <-->|financial transactions| d2
    p7 -->|interactive analysis| operator
```

The data-flow views deliberately label external providers as boundaries because provider choices and live/sandbox scope are unresolved decisions.
