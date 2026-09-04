# Part 0 — Benchmark Research: What Existing Marketplaces Got Right and Wrong

> Input research for the Technical Task of a next-generation, warehouse-free marketplace.
> Compiled September 2026. Sources are listed at the end of this document.

---

## 1. Scope of the review

| Platform | Market | Fulfillment model | Why it is in the benchmark |
|---|---|---|---|
| Amazon | Global | FBA (own warehouses) + FBM/SFP (seller-fulfilled) | Reference architecture for the whole industry; also the reference set of seller grievances |
| Uzum Market | Uzbekistan | FBO (own fulfillment centers) + DBS (seller delivers) since June 2025 | Home market leader; its constraints define our competitive gap |
| Wildberries / Ozon | RU/CIS | FBO + FBS + DBS | Closest operational analogue to UZ; a live case study of what regulators punish |
| eBay / Etsy | Global | 100% seller-fulfilled | Proof that a warehouse-free marketplace can scale; also shows where it breaks |
| Trendyol / Shopee / Allegro | TR / SEA / PL | Hybrid, heavy carrier aggregation | Best-in-class multi-carrier orchestration and PUDO networks |

---

## 2. What works — patterns worth copying

1. **Single trusted checkout.** One basket, one payment, one guarantee, regardless of how many sellers are involved. This is the marketplace's real product.
2. **A delivery promise on the product card.** Conversion is driven by a concrete date ("Thursday, 8 Sep"), not by a shipping-method name.
3. **Escrowed money.** The buyer's money is held until delivery is confirmed. This is what allows a stranger to be trusted.
4. **Reputation as an operating system.** Search ranking, badges, payout terms and program eligibility all derive from measurable seller behaviour.
5. **Hard fulfillment SLAs with published thresholds.** Amazon's Seller Fulfilled Prime shows that seller-fulfilled logistics *can* be premium if metrics are explicit and enforced: On-Time Delivery ≥ 93.5%, Valid Tracking ≥ 99%, Order Defect Rate < 1%, Pre-Fulfillment Cancel Rate < 0.5%, Late Shipment Rate < 4%, reviewed weekly.
6. **Aggregated logistics.** Rate-shopping across carriers, label generation, pickup booking and normalised tracking inside the seller's dashboard.
7. **PUDO and locker networks.** In Uzbekistan, Fargo already operates parcel lockers and API integration; BTS Express covers 34 settlements around the clock. Pickup infrastructure exists and can be rented instead of built.
8. **Structured catalogue (PIM).** Category-specific attributes make search, filtering and comparison possible; free-text listings do not.
9. **Marketplace-funded promotions and A-to-Z-style buyer guarantees.** They convert a risky purchase into a safe one.
10. **Seller mobile app first.** In markets with bazaar-based retail, the seller's only computer is a phone.

---

## 3. What is broken — the grievance list that defines our product

### 3.1 Fee inflation and unpredictability (Amazon)

- FBA fulfillment fees rose again from 15 January 2026, averaging **+$0.08 per unit**; a seller shipping 20,000 units/year absorbs ~$1,600 from that single line item.
- A **new surcharge on FBA items priced under $15** was introduced in July 2026, hitting exactly the low-ticket SKUs typical of an emerging market.
- **Long-term storage surcharges now start at day 181 instead of day 271** — 90 days earlier.
- Result: sellers such as Haus of Brilliance are actively moving *away* from FBA back to self-storage and self-fulfillment. The market is already drifting toward the model we intend to build natively.

**Design conclusion:** the storage/fulfillment fee line is the most hated and least predictable cost in the industry. A platform that structurally does not have it starts with a permanent 8–20 p.p. margin advantage per order.

### 3.2 Commission + logistics + storage stacking (Uzum Market)

- Category commission reported **up to ~35%** of retail price.
- **Logistics fee** on top: ~2,000–6,000 UZS for small items, up to ~20,000 UZS for large ones.
- **Storage**: free for 30 days for a new SKU, then 30–300 UZS/day depending on size, penalising slow-moving and seasonal goods.
- Physical constraints of a central FC exclude whole categories — Uzum itself justified launching DBS (Delivered by Seller, from 2 June 2025) precisely to admit "products previously unavailable on the platform due to size restrictions or special storage and delivery requirements": bulky goods, construction materials, batteries, premium items. Under DBS **no logistics fee is charged, only sales commission**, and the seller sets their own delivery zones and timelines.

**Design conclusion:** the incumbent has already conceded that seller-fulfilled is necessary — but it is a bolt-on for large sellers with existing logistics. Nobody has built the tooling that makes seller-fulfilled viable for a *small* seller. That is the opening.

### 3.3 Opaque, unilateral and retroactive rule changes (Wildberries, Ozon)

Russia's FAS opened proceedings and issued warnings in Q1–Q2 2026 over:

- **Longer payout cycles** — revenue for sold goods remitted later and later.
- **Tariffs detached from real cost** — delivery and return fees tied to *the price of the goods* rather than to actual logistics cost, so sellers cannot compute unit economics at all.
- **Platform-imposed discounts** — promotions applied to sellers' goods without prior consent, at the seller's expense; treated by the regulator as possible abuse of dominance.
- **Paid "Original" badge (Ozon)** — a badge that implies verification the platform does not actually guarantee.
- **Stock-rating systems (Wildberries, from September 2025)** — low-rated sellers forced to pay more for storage, join discount campaigns, or urgently remove stock.

**Design conclusion:** the single most valuable feature we can ship is not technical — it is a *contractual and technical guarantee of predictability*: published formulas, notice periods, no retroactive changes, no forced discounts, appealable decisions. Encode it in the product, not only in the offer document.

### 3.4 Consumer-side failures (Uzum, sector-wide)

- Uzbekistan's Competition Committee found **26 violations** in the public offer of Uzum Tezkor (March 2026): refusal to exchange or refund defective goods, incomplete or inaccurate consumer information, missed delivery deadlines, and non-compliance with language requirements for official contracts.
- The Ministry of Justice identified **200+ counterfeit items** on Uzum Market; the platform responded with an "Original" badge and mandatory brand authorisation for 200+ popular brands.
- Sector-wide 2026 picture: Amazon blocked 250M+ suspected fake reviews and is suing review brokers; the FTC is actively litigating fake-review cases; counterfeiters increasingly evade keyword detection with image-only listings and AI-generated content.

**Design conclusion:** trust must be engineered at the *source* (identity, brand authorisation, marking codes, mystery shopping) rather than patched at the badge layer — and the badge must never be purchasable.

### 3.5 Search quality degradation

Ad load creep, sponsored placements indistinguishable from organic results, and rankings that reward ad spend over fulfillment quality. Regulators are converging here too: the EU DSA imposes ranking-transparency obligations, and Article 30 requires marketplaces to collect and *verify* trader identity, address, payment account and trade-register data, display the trader's identity on the listing, and suspend traders whose data does not hold up.

**Design conclusion:** cap ad density by policy in the ranking service itself, label ads unambiguously, publish the ranking factors, and make organic position unbuyable.

### 3.6 The returns black hole

Returns are the hardest part of any warehouse-free model, and the part every incumbent solves with a warehouse. Refusal to refund is the #1 consumer complaint in the local regulator's findings. Without an FC, we need a designed answer: PUDO-mediated returns with an inspection protocol, a return-insurance pool, and abuse scoring.

---

## 4. Structural comparison of fulfillment models

| Dimension | Marketplace-owned FC (FBO/FBA) | Seller-fulfilled (our model) |
|---|---|---|
| CAPEX / OPEX | Very high; multi-year payback | Near zero warehouse capex |
| Time to enter a new city | 6–18 months (build an FC) | Days (sign a carrier lane) |
| Assortment breadth | Limited by FC physics (size, temperature, hazmat, high-value) | Effectively unlimited |
| Delivery speed | Best-in-class in covered cities | Depends on seller; can be *faster* intra-city (seller is nearer than the FC) |
| Delivery consistency | High | **The core risk — must be engineered** |
| Unit economics for seller | Commission + logistics + storage + returns fees | Commission + actual shipping cost |
| Quality control | At intake into the FC | **Must move to source + audit** |
| Returns | Trivial (returns to FC) | **Hard — the main design problem** |
| Conflict of interest | Platform also sells / self-preferences its own stock | Structurally impossible — platform never owns inventory |
| Capital efficiency | Poor | Excellent |
| Regulatory exposure | High (dominance, self-preferencing) | Low by construction |

**Verdict:** the warehouse-free model wins on capital efficiency, assortment, market coverage and neutrality, and loses on consistency, quality control and returns. The entire Technical Task that follows is organised around *engineering away those three losses*.

---

## 5. Non-negotiable local (Uzbekistan) constraints

1. **Fiscal receipts.** Online fiscal cash-register integration has been mandatory for e-commerce since 2023. Every transaction requires a digital ChEK transmitted in real time to the Tax Committee, containing seller data, product name, quantity, price, VAT and a unique transaction number, with QR code and fiscal mark. Cloud/virtual cash registers are permitted. Penalty for failing to issue a ChEK: 5–10 BHM per transaction (~$130–260). **In a seller-fulfilled model the receipt must be issued for the seller, at the moment of the seller's sale — this is a first-class platform service, not an afterthought.**
2. **Product marking (ASL BELGISI).** Datamatrix codes must be readable and validated for marked categories; virtual cash registers already support 2D/datamatrix scanning.
3. **Payments.** Two national card systems (Uzcard, Humo) and ~49 payment organisations (Payme, Click, Uzum and others), each with its own protocol. Aggregators such as ATMOS provide acquiring plus **payment splitting and holding** — i.e. escrow and split settlement are procurable rather than buildable from scratch. Unified integration libraries (e.g. PayTechUZ) exist for Payme/Click/Uzum.
4. **Cash on delivery** remains a large share of orders and must be a first-class, fully reconciled payment method — including COD collected by a third-party courier on the seller's behalf.
5. **Languages.** Uzbek (Latin), Russian, English. Official contracts must satisfy linguistic requirements — a point the Competition Committee explicitly cited.
6. **Data.** Personal data of citizens must be processed on servers located in Uzbekistan.
7. **Geography.** Coverage beyond Tashkent is a differentiator: BTS reaches 34 settlements; Fargo runs lockers and offers fast API integration. Regional sellers currently sit outside FC-based platforms entirely.

---

## 6. The ten design principles this research produces

1. **No inventory, ever.** The platform is never the seller of record and never takes title. Neutrality is structural, not promised.
2. **The promise, not the warehouse, is the product.** Invest in delivery-date accuracy instead of square metres.
3. **Predictability is a feature.** Published formulas, 60-day notice on fee changes, no retroactive charges, no forced discounts.
4. **Trust is earned and transparent.** One published score drives ranking, payouts, COD limits and program access; the seller can see every component.
5. **Fees must map to real costs.** Never tie a logistics fee to the price of the item — that was the exact FAS finding.
6. **Quality at source.** Verified identity, brand authorisation, marking-code binding at packing, mystery shopping, fast takedowns.
7. **Returns are a designed subsystem, not an exception path.**
8. **Ads never buy organic rank**, are always labelled, and are density-capped.
9. **Mobile-first for sellers**, because the seller is a bazaar merchant with a phone.
10. **Open by default**: public APIs, full data export, exportable signed reputation. No lock-in.

---

## Sources

- [Marketplace Briefing: Amazon sellers brace for higher fulfillment fees in 2026 as tariff costs bite — Modern Retail](https://www.modernretail.co/operations/marketplace-briefing-amazon-sellers-brace-for-higher-fulfillment-fees-in-2026-as-tariff-costs-bite/)
- [Amazon 2026 FBA Fee Changes: What Sellers Need to Know — eFulfillment Service](https://www.efulfillmentservice.com/2026/04/amazon-2026-fba-fee-changes-what-sellers-need-to-know/)
- [Amazon's Low-Price FBA Surcharge (July 2026) — SentryKit](https://sentrykit.com/blog/amazon-low-price-fba-surcharge-july-2026/)
- [Amazon Seller Fulfilled Prime (SFP): Requirements, Benefits and How to Qualify in 2026 — SPS Commerce](https://www.spscommerce.com/community/articles/amazon-seller-fulfilled-prime-sfp-requirements-benefits-and-how-to-qualify-in-2026)
- [Seller Fulfilled Prime 2026: Requirements & How to Keep It — SentryKit](https://sentrykit.com/blog/amazon-seller-fulfilled-prime-sfp-guide-2026/)
- [Uzum Market sellers can now deliver orders themselves — Uzum press centre](https://uzum.com/en/press-center/news-and-press-releases/uzum-market-sellers-can-now-deliver-orders-themselves/)
- [Seller requirements of Uzum Market — Chaika](https://chaika.uz/en/marketplace/uzum)
- [Competition Committee flags Uzum Tezkor and BeeMarket among e-commerce platforms for consumer rights violations — Kun.uz](https://kun.uz/en/news/2026/03/25/competition-committee-flags-uzum-tezkor-and-beemarket-among-e-commerce-platforms-for-consumer-rights-violations)
- [Uzum Market responds to reports of counterfeit products being sold — UzDaily](https://www.uzdaily.uz/en/uzum-market-responds-to-reports-of-counterfeit-products-being-sold/)
- [FAS takes on Wildberries and Ozon: conditions for sellers raise questions — www1.ru](https://www1.ru/en/news/2026/04/18/fas-vzialas-za-wildberries-i-ozon-usloviia-dlia-prodavtsov-vyzvali-voprosy.html)
- [The Federal Antimonopoly Service has issued warnings to Ozon and Wildberries — Magenta Legal](https://www.magenta.legal/en/news/The-Federal-Antimonopoly-Service-has-issued-warnings-to-Ozon-and-Wildberries:-Marketplaces-must-not-impose-promotions-on-retailers-)
- [FAS against marketplaces: Ozon and Wildberries demand to change the rules for sellers — Deliver2](https://deliver-2.com/news/marketplaces/fas-against-marketplaces-ozon-and-wildberries-demand-to-change-the-rules-for-sellers/)
- [What is the Difference Between Dropship and Marketplace? — Mirakl](https://www.mirakl.com/blogs/marketplace/what-is-the-difference-between-dropship-and-marketplace/)
- [Marketplace vs Dropship: Key Differences, Pros & Cons — Carro](https://getcarro.com/blog/marketplace-vs-dropship)
- [DSA decoded #9: The DSA and online marketplaces — Freshfields](https://www.freshfields.com/en/our-thinking/blogs/technology-quotient/dsa-decoded-9-the-dsa-and-online-marketplaces-102lx12)
- [The Marketplace Enforces First: DSA Trader Traceability — Tronvik](https://tronvik.com/insights/dsa-marketplace-dependency-trader-traceability/)
- [Uzbekistan E-Commerce Tax Legal Guide 2026 — 101 Digital](https://101digital.uz/en/blog/uzbekistan-ecommerce-tax-legal-guide-2026/)
- [On measures to ensure the use of online cash registers and the virtual cash system (No. 943, 23.11.2019) — lex.uz](https://lex.uz/en/docs/7237953)
- [Tax Committee: Online cash register usage is mandatory — One.uz](https://one.uz/en/news/uzbekistan/29126-tax-committee-online-cash-register-usage-is-mandatory.html)
- [Regulation of Payment Organizations in the Republic of Uzbekistan — Esplora Legal](https://esploralegal.com/regulation-of-payment-organizations-in-the-republic-of-uzbekistan/)
- [ATMOS — payment organisation, splitting and holding](https://atmos.uz/en)
- [PayTechUZ — unified payment library for Payme/Click/Uzum](https://pay-tech.uz/en/)
- [Fargo — parcel delivery and parcel lockers](https://www.fargo.uz/)
- [BTS Express — courier service across Uzbekistan](https://bts.uz/en/)
- [Counterfeit removal on online marketplaces: complete guide (2026) — Red Points](https://www.redpoints.com/blog/online-marketplaces-complete-guide/)
- [Amazon's crackdown on fake reviews in 2026 — SalesDuo](https://salesduo.com/blog/amazon-crackdown-fake-reviews/)
- [FTC's 2026 enforcement approach to fake reviews — DLA Piper](https://www.dlapiper.com/en-us/insights/publications/2026/07/ftcs-2026-enforcement-approach-to-fake-reviews-takes-shape-takeaways-for-companies)
