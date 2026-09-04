# Technical Task — Part 1: Product Definition and Functional Requirements

**Project working title:** NGM — Next-Generation Marketplace (warehouse-free, seller-shipped)
**Document version:** 1.0
**Date:** 2026-09-04
**Status:** For review and approval
**Primary market:** Republic of Uzbekistan, with an architecture portable to neighbouring CIS markets

---

## 1. Purpose of this document

This Technical Task (TZ) defines the business model, scope, functional and non-functional requirements, architecture, integrations, delivery phases and acceptance criteria for a new online marketplace whose defining property is:

> **The platform owns no warehouses and never takes title to goods. Sellers store, pack and ship every order from their own premises — a shop, a bazaar stall, a workshop, a home, or their own warehouse — and the platform provides the demand, the trust, the money movement, the delivery promise and the logistics orchestration.**

It is written to be directly executable by a product, engineering and operations team, and to serve as the basis for estimation, contracting and acceptance.

The rationale and evidence behind every design decision here are in [Part 0 — Benchmark Research](./00-research-benchmark.md).

---

## 2. Business model

### 2.1 What the platform is and is not

| The platform IS | The platform IS NOT |
|---|---|
| A demand aggregator and storefront | A retailer |
| A trust and identity layer | An owner of inventory |
| An escrow and settlement layer | A warehouse operator |
| A delivery-promise engine | A carrier |
| A logistics broker across third-party carriers | A seller of record |
| A dispute-resolution authority | A price-setter |

Consequence: the platform has **no conflict of interest** with its sellers. It cannot self-preference its own stock because it has none. This is a marketing asset and a regulatory shield, and it must be stated in the public offer.

### 2.2 Fulfillment modes (all seller-origin)

| Code | Name | Description | Who moves the parcel |
|---|---|---|---|
| **SFD** | Seller-Fulfilled Delivery (default) | Seller packs; platform books a third-party carrier; carrier collects from the seller's address | Aggregated carrier |
| **SDD** | Seller Direct Delivery | Seller delivers with own courier/staff in their own zone | Seller |
| **SPU** | Store Pickup | Buyer collects at the seller's own point of sale | Buyer |
| **SDP** | Seller Drop-off to PUDO/locker | Seller drops the parcel at the nearest pickup point/locker; carrier moves it onward | Carrier from PUDO |
| **XDT** | Cross-dock transit (Phase 3, optional) | Parcels consolidated at a rented cross-dock for ≤ 24 h — **transit only, no storage, no title** | Carrier |

XDT is the only concession to physical infrastructure, is explicitly time-boxed to 24 hours, is rented rather than owned, and never stores unsold inventory. It exists to make inter-city consolidation economical, not to become a warehouse.

### 2.3 Revenue model

| Stream | Basis | Notes |
|---|---|---|
| Sales commission | % of item price, by category | Target 4–12%, i.e. structurally below incumbents because there is no storage/FC cost to recover |
| Payment processing | Pass-through at cost + ≤ 0.3% | Published; never bundled into commission |
| Logistics brokerage | Fixed markup per shipment (absolute UZS, **never a % of item price**) | Direct answer to the FAS finding against price-linked logistics tariffs |
| Advertising | CPC / CPM on clearly labelled slots | Density-capped by policy (see §7.4) |
| Subscriptions | Optional seller tiers (analytics, bulk tools, extra ad credits, priority support) | Never affects organic ranking |
| Value-added services | Photo studio, content production, packaging supply, shipment insurance, financing referral | Optional, à la carte |

**Prohibited revenue practices (contractual and enforced in code):**
- No storage fees (nothing is stored).
- No fee tied to the price of the item for a logistics service.
- No platform-imposed discount funded by the seller.
- No retroactive fee changes. Fee schedule changes require **60 days' notice**, are versioned, and are published with a diff.
- No paid authenticity badge. Authenticity signals are earned or verified, never sold.

### 2.4 Unit economics target (illustrative, per average order)

| Line | Incumbent FBO model | NGM model |
|---|---|---|
| Commission | 20–35% | 4–12% |
| Logistics fee to seller | 2,000–20,000 UZS | Actual carrier cost + fixed brokerage |
| Storage | 30–300 UZS/day after 30 days | 0 |
| Return handling | Charged to seller | Shared via return-insurance pool |
| **Seller take-home uplift** | baseline | **+8 to +20 p.p. of GMV** |

The whole go-to-market message is this table.

---

## 3. Goals, KPIs and non-goals

### 3.1 North-star metric

**DOP — Delivered-On-Promise orders**: share of orders delivered on or before the date promised at checkout.
Target: ≥ 92% by end of Month 12; ≥ 95% by Month 24.

### 3.2 KPI tree

| Layer | Metric | Year-1 target |
|---|---|---|
| Demand | MAU (buyers) | 300,000 |
| Demand | Conversion (session → order) | ≥ 2.5% |
| Supply | Active sellers (≥ 1 order/30 d) | 5,000 |
| Supply | Live SKUs | 1,500,000 |
| Supply | Seller onboarding time (registration → first live listing) | ≤ 60 min, median |
| Fulfillment | DOP (north star) | ≥ 92% |
| Fulfillment | On-Time Pickup Rate (carrier collects when promised) | ≥ 95% |
| Fulfillment | Seller Late Shipment Rate | < 4% |
| Fulfillment | Order Defect Rate | < 1% |
| Fulfillment | Cancellation by seller (out of stock) | < 1.5% |
| Trust | Counterfeit takedown time | < 24 h from verified report |
| Trust | Dispute resolution time (median) | < 72 h |
| Money | Seller payout time (default tier) | ≤ T+3 after delivery |
| Money | COD reconciliation break rate | < 0.1% |
| Platform | Take rate (all-in) | 9–15% |

### 3.3 Guardrail metrics (must not degrade)

Ad density on search page 1; share of organic clicks; seller complaint rate about fee predictability; buyer refund success rate; p95 search latency.

### 3.4 Non-goals for v1

Own warehouses; own courier fleet; private-label goods; B2B wholesale; cross-border import/export flows; a full-blown ERP for sellers; groceries and fresh food; pharmaceuticals; regulated categories requiring per-order licence checks (Phase 3+).

---

## 4. Actors and roles

| Actor | Description | Interface |
|---|---|---|
| **Buyer** | Consumer, guest or registered | Web, iOS, Android |
| **Seller (individual entrepreneur / YaTT)** | Small merchant, bazaar or single-shop | Android app first, web |
| **Seller (legal entity / LLC)** | Company with own logistics | Web dashboard, API |
| **Seller staff** | Packer, courier, manager — scoped permissions under one seller account | Seller app |
| **Carrier** | Third-party logistics provider (BTS, Fargo, Yandex Delivery, Uzpost, regional couriers) | API integration + carrier portal |
| **PUDO operator** | Pickup point / locker network | API + point app |
| **Brand owner / rights holder** | Submits authorisations and IP complaints | Brand portal |
| **Category manager** | Platform staff: catalogue, attributes, moderation | Back office |
| **Trust & Safety officer** | Moderation, counterfeit, fraud, appeals | Back office |
| **Support agent** | Buyer/seller support, disputes | Back office + CRM |
| **Finance operator** | Payouts, COD reconciliation, tax reporting | Back office |
| **Admin** | Configuration, roles, feature flags | Back office |
| **Auditor (read-only)** | Regulator/internal audit access to immutable logs | Back office, read-only |

---

## 5. Buyer-facing functional requirements

### 5.1 Discovery and search

- **FR-B-01** Full-text search over the catalogue in Uzbek (Latin **and** Cyrillic input), Russian and English, with cross-script transliteration, typo tolerance, synonym dictionaries and category-aware query understanding.
- **FR-B-02** Faceted filtering on category-specific attributes, price, seller trust tier, delivery speed ("arrives by ..."), fulfillment mode, location of the seller, availability of COD, rating.
- **FR-B-03** **Location-aware results.** The buyer's delivery address (or detected city) is a first-class ranking input: an offer that can arrive tomorrow from a seller 3 km away outranks an identical cheaper offer arriving in six days from another region. Distance is an advantage of this model and must be exploited.
- **FR-B-04** Every result card shows: price, delivery promise date, fulfillment mode icon, seller name + trust tier, and — when the item is sold by several sellers — an explicit "N offers from X UZS" entry point.
- **FR-B-05** Sponsored results are visually distinct, labelled "Reklama / Реклама / Sponsored", and limited to a maximum of **2 slots in the first 10 results and 20% of any result page** (hard-coded policy, see NFR-P-03).
- **FR-B-06** The ranking factors are published in the Help Centre, and the ordering logic must not include ad spend as an organic signal.

### 5.2 Product page and offers

- **FR-B-07** One product (PIM record) can carry many seller offers. The default offer is chosen by an **Offer Selection Algorithm** (§7.3), which is transparent and explains itself ("Chosen for: fastest delivery + high seller rating").
- **FR-B-08** Offer list shows per-seller: price, delivery promise, shipping cost, return policy, trust tier, distance/region, fulfillment mode.
- **FR-B-09** Authenticity block: brand-authorised badge (earned, verifiable, never purchasable), marking-code presence for regulated categories, document-backed claims.
- **FR-B-10** Reviews are **verified-purchase only**, tied to a delivered order, with photo/video support, seller replies, and a public "review integrity" policy. Incentivised reviews are prohibited and detectable.
- **FR-B-11** Q&A with the seller, SLA on first response shown publicly (median response time is a seller metric).

### 5.3 Cart, checkout and payment

- **FR-B-12** **Multi-seller basket** with automatic split into shipments, each with its own promise date, shipping cost and fulfillment mode; the buyer sees the split explicitly before paying.
- **FR-B-13** Shipping-cost consolidation rules: per-shipment cost, with configurable free-shipping thresholds (seller-funded, seller-controlled) and platform-funded campaigns (platform pays the delta — never the seller, unless the seller opted in).
- **FR-B-14** Address book with map-pin selection, landmark field (essential in UZ addressing), phone verification, and delivery-window preferences.
- **FR-B-15** Payment methods: Uzcard/Humo via the national schemes, Visa/Mastercard, Payme, Click, Uzum wallet, platform wallet balance, **cash on delivery**, and instalment/BNPL via bank partners (Phase 2).
- **FR-B-16** **Escrow by default.** Funds are authorised/captured at checkout and held by the platform (or the licensed payment partner) until delivery confirmation + the return window trigger defined in §6.6.
- **FR-B-17** Fiscal receipt (online ChEK) issued per seller, per shipment, at the legally correct moment, delivered to the buyer in-app and by SMS/e-mail, containing seller data, item names, quantities, prices, VAT, unique transaction number, QR code and fiscal mark (see INT-06).
- **FR-B-18** Guest checkout with phone-OTP identity, upgradeable to a full account.

### 5.4 Post-purchase

- **FR-B-19** Unified tracking timeline per shipment, normalised across carriers, with push/SMS/Telegram notifications on each state change and proactive alerts when the promise is at risk.
- **FR-B-20** Delivery confirmation by OTP code, signature or QR scan; photo proof-of-delivery stored for 180 days.
- **FR-B-21** Returns: self-service initiation within the statutory window, reason taxonomy, photo/video evidence, return method selection (PUDO drop-off, courier pickup, in-store return to the seller), printable/QR return label.
- **FR-B-22** **Buyer Protection**: full refund if the item is not delivered, not as described, counterfeit, damaged or arrives after the promise beyond a tolerance threshold. Refund SLA: ≤ 3 business days from resolution, to the original payment instrument; instant to platform wallet.
- **FR-B-23** Dispute centre with a clock: seller must respond within 48 h; platform arbitration decision within 72 h; both sides see the evidence trail and the reasoning of the decision.

### 5.5 Accounts and engagement

- **FR-B-24** Wishlist, price-drop and back-in-stock alerts, order history with re-order, saved cards (tokenised, PCI scope confined to the PSP).
- **FR-B-25** Loyalty programme: cashback into wallet, tiers, referral. Funded from the platform's margin, never charged to the seller without opt-in.
- **FR-B-26** Full account/data export and deletion (personal-data compliance).

---

## 6. Seller-facing functional requirements

### 6.1 Onboarding and identity

- **FR-S-01** Registration by phone OTP; then KYC/KYB: PINFL/passport for individuals, STIR/INN + trade-register data for legal entities, bank account for payouts, and verification through the state registries where available; e-signature (ERI) support for contracts.
- **FR-S-02** Identity data is **verified, displayed on the listing** (legal name, registration number, contact and address channel) and re-verified periodically — mirroring the DSA Art. 30 traceability standard as a market-leading practice rather than waiting for local regulation.
- **FR-S-03** Contract acceptance is a versioned event; every offer version the seller ever accepted is retained and retrievable.
- **FR-S-04** Guided onboarding wizard with a **time-to-first-listing target of 60 minutes**, including: pickup addresses, working calendar, handling time, delivery zones, return address, payout details, fiscal registration.
- **FR-S-05** Seller staff sub-accounts with role-based permissions (packer, courier, manager, accountant).

### 6.2 Catalogue and listings

- **FR-S-06** Three listing paths: (a) attach an offer to an existing PIM product by barcode/GTIN or search; (b) create a new product via a category attribute form; (c) **photo-first AI-assisted creation** — the seller photographs the item in the mobile app and the platform proposes category, title, attributes and a description draft for confirmation. Path (c) is mandatory for bazaar-scale onboarding.
- **FR-S-07** Bulk operations: XLSX/CSV import-export, API, and integrations with common local accounting/POS systems (Phase 2).
- **FR-S-08** Moderation pipeline: automated checks (prohibited items, brand terms, image quality, duplicate detection, price-anomaly detection) plus human review for flagged items. Moderation SLA ≤ 4 working hours; every rejection states the exact rule and offers an appeal.
- **FR-S-09** Brand authorisation registry: rights holders upload brand ownership; sellers upload distribution authorisation; listings in protected brands require a valid authorisation or are restricted to a "no brand claim" state.
- **FR-S-10** Marked-category support: the listing declares whether it carries an ASL BELGISI datamatrix; codes are scanned and bound at packing (§6.4).
- **FR-S-11** Pricing is entirely seller-controlled. The platform may *recommend* a price and *show* competitiveness, but must never change it. Any platform promotion requires an explicit, revocable opt-in with a funding split stated up front.

### 6.3 Inventory and capacity — the critical subsystem

Because stock sits in shops that also sell offline, **stock accuracy is the #1 failure mode of this model**. Requirements:

- **FR-S-12** Stock is per offer per pickup location, with reservation on order placement and an audit trail of every movement.
- **FR-S-13** **Cutoff-aware capacity model**: each seller declares, per location, working days/hours, order cutoff time, handling time, and a maximum number of orders per day ("daily capacity"). The Promise Engine will never promise beyond declared capacity.
- **FR-S-14** **Stock freshness scoring.** Offers whose stock has not been confirmed within N days, or whose seller shows a rising out-of-stock cancellation rate, are automatically demoted in ranking and given a longer promise buffer — and, past a threshold, are auto-paused. This replaces the incumbents' punitive fines with a mechanism that fixes the buyer experience directly.
- **FR-S-15** One-tap daily stock confirmation in the mobile app ("Still in stock?"), plus quick actions: pause offer, pause all offers (vacation mode), reduce capacity for today.
- **FR-S-16** Optional integrations to POS/1C/uzum-style inventory files for automatic stock sync (Phase 2).

### 6.4 Order fulfillment workflow (seller side)

- **FR-S-17** New order → push + SMS + (optional) Telegram alert with an **acceptance clock**; the seller must accept or reject within the configured window (default 60 min during working hours).
- **FR-S-18** Pick list and packing screen: item, quantity, photos, buyer notes; **mandatory packing scan** — barcode/GTIN of the item and, for marked categories, the datamatrix code, binding physical goods to the order.
- **FR-S-19** Packing evidence: the seller photographs the sealed parcel; the photo is stored and becomes the primary evidence in any "wrong/damaged item" dispute. This is the warehouse-free substitute for FC intake QC.
- **FR-S-20** Label generation: the platform prints/produces the carrier label (thermal 100×150 or A4 4-up) with the platform's own parcel ID as the primary key and the carrier's tracking number as a secondary key.
- **FR-S-21** Handover: carrier pickup booking (auto-booked at accept time), pickup window shown, handover confirmed by scan on both sides. For SDD, the seller's courier is tracked in-app; for SPU, a pickup code is issued to the buyer; for SDP, the drop-off is confirmed by the PUDO scan.
- **FR-S-22** Exception handling: reschedule pickup, report a damaged item, split a shipment, partial cancellation with automatic partial refund.
- **FR-S-23** Seller-side return processing: inspection screen, accept/dispute with evidence, restock or write-off.

### 6.5 Money

- **FR-S-24** Wallet ledger per seller: double-entry, immutable, every entry traceable to an order, fee, adjustment, refund or payout. Every fee line names the rule and the rule version that produced it.
- **FR-S-25** **Fee calculator** available in UI and as an API endpoint, giving the exact expected net proceeds for a hypothetical sale before the seller lists it.
- **FR-S-26** Payout schedule tied to trust tier (see §7.2): T+0/T+1 for top tiers, T+3 default, T+7 for new sellers, with the rule visible in the dashboard and a countdown to the next payout.
- **FR-S-27** COD settlement: the platform reconciles cash collected by carriers against orders, nets its commission, and pays out on the same schedule; discrepancies open an automatic reconciliation case.
- **FR-S-28** Holds and reserves: a rolling reserve may be applied only per published rules (new seller, high dispute rate, chargeback risk), always with the reason, the amount, the release date and an appeal button. **No unexplained, indefinite fund freezing** — this is the single most damaging incumbent behaviour we are displacing.
- **FR-S-29** Fiscal: the platform acts as the seller's technical agent for online ChEK issuance and stores fiscal documents; support for e-invoices (EHF/ЭСФ) between platform and seller for commission and services.

### 6.6 Returns and disputes (seller side)

- **FR-S-30** Return routing decision engine: for each return, choose the cheapest compliant path — direct courier back to the seller, PUDO drop-off with consolidated return leg, in-store return, or **"refund without return"** when the return cost exceeds the item value (an explicit, seller-configurable rule with a monthly cap).
- **FR-S-31** Independent inspection protocol at PUDO for disputed returns: standard photo/video capture at drop-off, timestamped, geotagged, immutable — the evidence base for arbitration.
- **FR-S-32** **Return-Insurance Pool**: a small per-order contribution (published %) forms a pool that covers the logistics cost of no-fault returns, so that no single small seller is bankrupted by return costs. Pool balance and payout rules are published quarterly.
- **FR-S-33** Return-abuse scoring on the buyer side: serial returners, wardrobing and fraud patterns lead to graduated restrictions (return-window normalisation, no COD, deposit) with an appeal path.

### 6.7 Analytics and growth

- **FR-S-34** Seller dashboard: sales, funnel (impressions → clicks → cart → order), promise performance, cancellation and defect rates, return reasons, search terms leading to their offers, competitiveness of price and promise.
- **FR-S-35** **Trust Score Card**: every component of the seller's score, its weight, its current value, the exact target, and the concrete actions that would improve it. No hidden reputation.
- **FR-S-36** Self-serve ads with transparent auction mechanics, budget caps, and reporting on ad-attributed vs organic sales.
- **FR-S-37** Public seller API + webhooks (orders, stock, prices, shipments, returns, finance) with sandbox, and a **full data export** including reviews and a signed reputation certificate the seller may present elsewhere. Anti-lock-in by design.

---

## 7. Platform algorithms and policies (specified as requirements)

### 7.1 Promise Engine (delivery-date promise)

The single most important algorithm in the system.

**Inputs:** seller location + working calendar + cutoff + handling-time distribution (historical, per seller per category); buyer address geo-zone; selected/available carrier lanes with their historical transit-time distributions per origin-destination pair; current time; capacity utilisation for the day; holidays; weather/force-majeure flags.

**Output:** for each offer/mode, a promise date and a confidence.

**Rule:** the published promise is the **P80 of the modelled delivery-time distribution** (i.e. we promise the date we expect to beat 80% of the time), rounded to end-of-day, with:
- a per-seller adaptive buffer that grows when the seller's DOP falls below target and shrinks as it recovers;
- a hard floor at "seller cutoff + handling time + lane P80";
- never a promise the declared daily capacity cannot absorb.

**Requirements:**
- **FR-P-01** The promise is computed server-side, cached per (offer, geo-zone, hour) and recomputed on every capacity or calendar change.
- **FR-P-02** The promise shown at checkout is **frozen into the order** and becomes the contractual commitment used for DOP and buyer compensation.
- **FR-P-03** A promise-at-risk detector runs continuously; when risk crosses a threshold, the buyer is notified proactively with options (wait, switch to another seller's offer, cancel with full refund), and the seller is alerted before the breach.
- **FR-P-04** Backtesting harness: every model change must be evaluated against the last 90 days of shipments before rollout; regression in DOP blocks the release.

### 7.2 Seller Trust Score (STS)

A single published 0–1000 score with visible components:

| Component | Weight | Signal |
|---|---|---|
| Fulfillment reliability | 30% | DOP, late shipment rate, on-time handover to carrier |
| Order integrity | 20% | Seller cancellation rate, out-of-stock rate, stock-confirmation freshness |
| Product conformity | 20% | "Not as described"/damaged dispute rate, return-by-fault rate, counterfeit findings, mystery-shopper results |
| Buyer experience | 15% | Verified-purchase rating, response time, Q&A quality |
| Compliance | 10% | KYC currency, fiscal receipt compliance, marking-code compliance, policy violations |
| Tenure & volume | 5% | Stabilises the score for low-volume sellers (Bayesian shrinkage toward category mean) |

**Requirements:**
- **FR-T-01** Formula, weights and thresholds are **published** and versioned; changes require 30 days' notice.
- **FR-T-02** Tiers (Bronze/Silver/Gold/Platinum) determine: payout speed, promise buffer size, COD limits, eligibility for the "Fast" badge, ad credits and support priority. Never a fine.
- **FR-T-03** Low-volume sellers are protected from statistical noise (minimum sample sizes, shrinkage).
- **FR-T-04** Every score movement produces an explainable event the seller can read ("−12: 2 late shipments in the last 30 days").
- **FR-T-05** Appeal mechanism with a 5-working-day decision SLA, and automatic exclusion of events caused by carrier failure or force majeure from the seller's metrics (attribution engine, §7.6).

### 7.3 Offer Selection ("who wins the default offer")

Score = w1·PriceCompetitiveness + w2·PromiseSpeed + w3·PromiseReliability(STS) + w4·ShippingCost + w5·ReturnPolicyStrength.
Weights are category-configurable and **published**. Ad spend is not an input. Ties are broken by a fair round-robin among comparable offers so that new sellers get real exposure.

- **FR-O-01** The product page must state, in plain language, why the selected offer won.
- **FR-O-02** A "new seller exploration" quota reserves a configurable share of impressions for offers with insufficient data, to avoid a rich-get-richer lock-in.

### 7.4 Ranking and advertising policy

- **FR-R-01** Organic ranking inputs: query relevance, offer selection score, location-adjusted promise, conversion and satisfaction history, stock freshness. **Ad spend is excluded.**
- **FR-R-02** Ad slots: max 2 within the first 10 organic positions; max 20% of any page; always labelled; never on the product page's "chosen offer" slot.
- **FR-R-03** Ranking-factor documentation is public and change-logged.

### 7.5 Trust & Safety

- **FR-TS-01** Counterfeit and IP: rights-holder portal, verified-report fast lane, takedown ≤ 24 h, repeat-infringer policy with escalating sanctions, appeal for sellers.
- **FR-TS-02** Random product audits ("mystery shopper") funded by the platform, targeted by risk score; results feed the STS product-conformity component.
- **FR-TS-03** Review integrity: verified-purchase gating, incentivised-review detection, graph analysis of buyer-seller collusion, public removal statistics.
- **FR-TS-04** Fraud: device fingerprinting, velocity rules, COD abuse detection, address risk scoring, chargeback handling, seller-collusion detection (self-buying to inflate rank).
- **FR-TS-05** Prohibited-goods classifier plus human escalation; category-specific compliance (age-restricted goods, certification-requiring goods).

### 7.6 Fault attribution engine

Every failure (late delivery, damaged parcel, missing item, failed pickup) is attributed to seller / carrier / buyer / platform / force-majeure using scan timestamps, geodata, photo evidence and carrier events.

- **FR-FA-01** Metrics and penalties apply only to the attributed party. A seller must never lose their rating because a carrier missed a pickup — the exact opposite of current incumbent practice.
- **FR-FA-02** Carrier scorecards mirror seller scorecards and drive lane routing decisions (§ Part 2).

---

## 8. Back-office functional requirements

- **FR-A-01** Catalogue administration: category tree, attribute dictionaries, unit systems, category commission and policy configuration with effective dates and mandatory notice periods.
- **FR-A-02** Moderation queues with SLA timers, reason codes, bulk actions and full audit trail.
- **FR-A-03** Dispute arbitration workbench: evidence timeline (packing photo, handover scan, GPS, delivery photo, return inspection), decision templates, decision reasoning stored and shown to both parties.
- **FR-A-04** Finance: payout runs, COD reconciliation, adjustments (four-eyes approval), fee-rule management, ledger reports, tax reports.
- **FR-A-05** Carrier management: lanes, tariffs, SLAs, scorecards, automatic routing rules, incident registry.
- **FR-A-06** Content and campaigns: banners, landing pages, platform-funded promotions with a funding source field that cannot be left blank.
- **FR-A-07** Fee and policy change workflow: draft → legal review → notice publication → effective date. The system physically cannot apply a fee change earlier than the notice period allows.
- **FR-A-08** Feature flags, A/B experimentation, kill switches.
- **FR-A-09** Immutable audit log of every administrative action, with read-only auditor access.

---

## 9. Governance commitments encoded in the product

These are requirements, not marketing. Each maps to a code-enforced control.

| # | Commitment | Enforcement |
|---|---|---|
| G1 | The platform never sells goods | No "platform seller" entity may exist in the seller registry; enforced by schema constraint and audit |
| G2 | No forced discounts | Promotions require a stored seller opt-in event; the promo engine rejects any campaign without one |
| G3 | Fee changes: 60 days' notice, no retroactivity | Fee-rule versioning with effective dates; orders are always priced by the rule version in force at order time |
| G4 | Logistics fees never depend on item price | Fee-rule schema forbids a price-based term for logistics fee types |
| G5 | Transparent ranking and scoring | Published formulas; a public changelog endpoint |
| G6 | No unexplained fund freezes | Every hold record requires reason code, amount, release date and appeal link; nightly job flags any hold older than its release date |
| G7 | Appeals with SLA | Appeal object with a timer; breaches escalate automatically |
| G8 | Ad density cap | Enforced in the search service, covered by automated tests |
| G9 | Data portability | Export API + signed reputation certificate |
| G10 | Fault-based accountability | Attribution engine gates all metric penalties |

---

*Continues in [Part 2 — Logistics and Fulfillment Without Warehouses](./02-logistics-and-fulfillment.md).*
