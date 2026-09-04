# NGM — Next-Generation Marketplace (warehouse-free, seller-shipped)

Research and full Technical Task for an online marketplace that owns **no warehouses**: sellers store,
pack and ship every order directly from their own premises, while the platform provides demand, trust,
money movement, a reliable delivery promise and third-party logistics orchestration.

Primary market: Republic of Uzbekistan. Architecture portable to neighbouring CIS markets.

## Documents

| # | Document | Contents |
|---|---|---|
| 0 | [Benchmark research](docs/00-research-benchmark.md) | Pros and cons of Amazon, Uzum Market, Wildberries/Ozon, eBay/Etsy and others; regulator findings; local constraints; the ten design principles derived from them |
| 1 | [Technical Task, Part 1 — Product definition](docs/01-technical-task.md) | Business model, fulfillment modes, revenue and fee rules, KPIs, roles, buyer and seller functional requirements, platform algorithms, governance commitments |
| 2 | [Technical Task, Part 2 — Logistics without warehouses](docs/02-logistics-and-fulfillment.md) | Carrier aggregation, PUDO/lockers, state machines, the Promise Engine, returns routing and neutral inspection, COD reconciliation, evidence chain |
| 3 | [Technical Task, Part 3 — Architecture and NFRs](docs/03-architecture-and-nfr.md) | Service map, data model, API contracts, external integrations, performance/availability/security/compliance requirements, data platform |
| 4 | [Technical Task, Part 4 — Delivery plan](docs/04-roadmap-and-acceptance.md) | Phases, team and effort, risk register, critical journeys, acceptance criteria, open questions |
| 5 | [Website TZ, Part A — Structure, pages and UX](docs/05-website-technical-task.md) | Sitemap and URL scheme, global layout, page-by-page specifications for the buyer storefront, seller acquisition site and seller cabinet, component library, responsive and content rules |
| 6 | [Website TZ, Part B — Frontend engineering](docs/06-website-engineering-and-acceptance.md) | Stack, rendering strategy, BFF, performance budgets, SEO, i18n, accessibility, analytics taxonomy, web security, testing, delivery plan, definition of done and launch gate |

## The idea in one table

| | Warehouse marketplace (FBO/FBA) | This project |
|---|---|---|
| Inventory | Held by the marketplace | Never held; seller keeps it |
| Seller cost | Commission + logistics + storage + return fees | Commission + actual shipping cost |
| Assortment | Limited by warehouse physics | Unlimited (bulky, fragile, made-to-order, hazardous, premium) |
| New city | 6–18 months and a capital project | Days — a carrier lane and a tariff |
| Conflict of interest | Platform sells its own stock too | Structurally impossible |
| Hard problems | Capital, storage cost | **Delivery consistency, quality control, returns** |

The whole Technical Task is organised around engineering away those three hard problems, with five
systems: the **Promise Engine**, the **Logistics Orchestrator**, the **Evidence Chain**, the
**Trust Score**, and the **Returns Routing Engine**.
