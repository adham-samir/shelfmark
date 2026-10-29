# UML Logical Component View

```mermaid
flowchart TB
    customer[Customer browser]
    operator[Back-office browser]

    subgraph ui[Frontend — Next.js / React / Tailwind]
        storefront[Storefront]
        backoffice[Back-office UI]
    end

    subgraph application[Application boundary — Python / FastAPI]
        api[FastAPI API and authorization]
        commerce[Catalog, cart, checkout, order and shipment services]
        events[Interaction event capture]
        orchestration[Job scheduler / orchestration]
    end

    subgraph intelligence[AI and analytics components]
        rec[Collaborative + content recommendations]
        assistant[AI shopping assistant]
        search[Image + voice search]
        forecast[Demand forecast + reorder policy]
        price[Dynamic pricing]
        rfm[RFM segmentation]
        fraud[Pre-completion fraud assessment]
        bi[BI metric queries]
    end

    relational[(PostgreSQL operational database)]
    catalog[(MongoDB product catalog)]
    artifacts[(Model artifacts / evaluation records)]
    external[Payment, shipment, supplier, OpenAI and processing integrations]

    customer --> storefront
    operator --> backoffice
    storefront --> api
    backoffice --> api
    api --> commerce
    api --> events
    api --> rec
    api --> assistant
    api --> search
    api --> bi
    commerce --> fraud

    orchestration --> forecast
    orchestration --> price
    orchestration --> rfm

    commerce --> relational
    events --> relational
    rec --> relational
    rec --> catalog
    assistant --> catalog
    assistant --> commerce
    search --> catalog
    forecast --> relational
    price --> relational
    rfm --> relational
    fraud --> relational
    bi --> relational

    rec --> artifacts
    search --> artifacts
    forecast --> artifacts
    fraud --> artifacts
    assistant --> external
    search --> external
    commerce --> external
    forecast --> external
```

Arrows show required communication/data dependencies, not mandated deployment units. The accepted starting arrangement is one Next.js application and one modular Python/FastAPI backend; background execution can share domain code. Docker and AWS are selected; service placement remains deployment work.
