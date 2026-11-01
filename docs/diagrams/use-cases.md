# UML Use-Case View

```mermaid
flowchart LR
    customer[Customer]
    operator[Back-office user]
    worker[Background worker]

    subgraph system[Shelfmark]
        discover((Discover and filter products))
        recommend((Receive personalized recommendations))
        assistant((Ask questions and choose products))
        track((Track own shipment))
        checkout((Checkout with pre-completion risk assessment))
        inventory((Forecast demand and automatically reorder))
        pricing((Automatically update prices))
        segment((Calculate and select RFM segments))
        risk((Review transaction risk results))
        dashboards((Explore consumer and financial dashboards))
    end

    customer --> discover
    customer --> recommend
    customer --> assistant
    customer --> track
    customer --> checkout

    operator --> inventory
    operator --> pricing
    operator --> segment
    operator --> risk
    operator --> dashboards

    worker --> inventory
    worker --> pricing
    worker --> segment

    checkout -. includes .-> risk
    assistant -. uses authorized lookup .-> track
    discover -. records interactions for .-> recommend
```

The diagram defines the two accepted human access boundaries from DEC-006: ownership-scoped customers and capability-scoped back-office users. It does not invent a larger role hierarchy.
