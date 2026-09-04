# Technical Task — Part 2: Logistics and Fulfillment Without Warehouses

This part specifies the subsystem that replaces the warehouse. It is the technical heart of the project: everything an incumbent solves by owning a fulfillment centre, we must solve with orchestration, data and incentives.

---

## 1. Logistics architecture overview

```
                         ┌──────────────────────────────┐
                         │      Promise Engine          │
                         │  (P80 delivery date, risk)   │
                         └──────────┬───────────────────┘
                                    │ lane stats, capacity
┌───────────┐   order    ┌──────────▼───────────┐   booking   ┌──────────────────┐
│  Buyer    ├───────────►│ Logistics            ├────────────►│ Carrier adapters │
│  checkout │            │ Orchestrator (LO)    │◄────────────┤ BTS / Fargo /    │
└───────────┘            │ - routing            │  webhooks   │ Yandex / Uzpost /│
                         │ - rate shopping      │             │ regional / self  │
┌───────────┐  pack/scan │ - label service      │             └──────────────────┘
│  Seller   ├───────────►│ - tracking normaliser│
│  app      │◄───────────┤ - exception manager  │             ┌──────────────────┐
└───────────┘  pickup    │ - COD reconciliation │◄───────────►│ PUDO / lockers   │
                         └──────────┬───────────┘             └──────────────────┘
                                    │ events
                         ┌──────────▼───────────┐
                         │ Attribution + Trust  │
                         └──────────────────────┘
```

The platform is a **logistics broker and control tower**, not a carrier. It owns the parcel identity, the promise, the evidence chain and the money; carriers own the vehicles.

---

## 2. Carrier integration layer

### 2.1 Requirements

- **FR-L-01** Carrier Adapter SPI: every carrier is integrated behind one internal interface with the operations `quote`, `create_shipment`, `book_pickup`, `cancel`, `label`, `track`, `cod_report`, `return_shipment`, `proof_of_delivery`.
- **FR-L-02** Adapters normalise carrier statuses into the canonical shipment state machine (§4). No carrier-specific status ever leaks into the buyer UI.
- **FR-L-03** Every adapter must degrade gracefully: on carrier API failure, the LO falls back to the next-best carrier for the lane; if none is available, the offer's fulfillment mode is downgraded (e.g. SFD → SDP or SDD) or the offer is temporarily hidden for that destination.
- **FR-L-04** Manual/offline carriers (small regional couriers with no API) are supported through a lightweight **Carrier Portal** (web + Android) providing scan-based status updates, so coverage is never blocked by a partner's IT maturity.
- **FR-L-05** Carrier contract data (lanes, cut-offs, tariffs, volumetric rules, max dimensions, COD support, insurance limits) is stored as structured, versioned configuration — not hard-coded.
- **FR-L-06** Idempotency on every carrier call; every request/response stored for 1 year for dispute and reconciliation purposes.

### 2.2 Rate shopping and routing

**FR-L-07** For every shipment the LO computes candidate routes and selects by a configurable objective function:

```
route_score = α·normalised_cost
            + β·(1 − P(on_time | lane, carrier, hour, weekday))
            + γ·carrier_scorecard_penalty
            + δ·buyer_preference_match      (locker vs door, time window)
            − ε·consolidation_bonus         (same seller → same destination cluster)
```

- **FR-L-08** Routing respects hard constraints first: dimensions/weight limits, prohibited-content rules, COD support, destination coverage, insurance limits, promised date feasibility.
- **FR-L-09** Sellers may pin a preferred carrier; the platform may override only when the pinned carrier cannot meet the promise, and must log the reason.
- **FR-L-10** **Consolidation**: multiple shipments from one seller collected in a single pickup; multiple parcels to one destination cluster combined into one carrier manifest.

### 2.3 Carrier scorecards

**FR-L-11** Per carrier, per lane, tracked weekly: on-time pickup rate, on-time delivery rate, damage rate, loss rate, scan-completeness, COD remittance timeliness, exception-response time, API availability. Scorecards drive routing weights automatically and are shared with the carrier.

---

## 3. Pickup, drop-off and the PUDO network

The absence of warehouses is compensated by **borrowed physical nodes**:

| Node type | Owner | Role |
|---|---|---|
| Seller's own premises | Seller | Origin of every parcel; also a pickup point for SPU |
| Carrier PUDO / parcel locker | Carrier (e.g. Fargo lockers, BTS offices) | Seller drop-off, buyer collection, return intake, dispute inspection |
| Partner retail points | Third parties (pharmacies, minimarkets, mobile shops) | Extended PUDO network under a platform-branded agreement (Phase 2) |
| Rented cross-dock | 3PL | ≤ 24 h transit consolidation only (Phase 3) |

Requirements:

- **FR-L-12** PUDO registry with geodata, opening hours, capacity, accepted parcel sizes, COD capability, return-intake capability, and live availability.
- **FR-L-13** PUDO selection in checkout on a map with walking distance and opening hours; locker size compatibility validated against the parcel's dimensions.
- **FR-L-14** Parcel dwell-time management at PUDO: storage limit, reminders to the buyer, automatic return-to-seller flow on expiry, and cost attribution for the wasted leg.
- **FR-L-15** PUDO inspection protocol (see §6.3) with a standardised photo/video capture app used by point staff.

---

## 4. Canonical state machines

### 4.1 Order

```
CREATED → PAYMENT_PENDING → PAID/COD_CONFIRMED → SPLIT_INTO_SHIPMENTS
       → PARTIALLY_FULFILLED → FULFILLED → CLOSED
       ↘ CANCELLED (by buyer / by seller / by system)
       ↘ DISPUTED → RESOLVED_REFUND | RESOLVED_SELLER_FAVOUR | RESOLVED_PARTIAL
```

### 4.2 Shipment (the canonical logistics object)

```
NEW
 → ACCEPTED_BY_SELLER            (acceptance clock; auto-cancel on expiry)
 → PACKED                        (requires item scan + parcel photo)
 → LABEL_ISSUED
 → AWAITING_HANDOVER             (pickup booked / drop-off pending)
 → IN_TRANSIT_FIRST_MILE
 → AT_SORTING / AT_PUDO
 → OUT_FOR_DELIVERY
 → DELIVERED                     (OTP / signature / QR + photo proof)
 → CLOSED                        (after return window)

Exception branches at any point:
 → PICKUP_FAILED → RESCHEDULED | REROUTED
 → DELIVERY_ATTEMPT_FAILED (n ≤ 3) → RETURN_TO_SELLER
 → LOST | DAMAGED → CLAIM_OPENED
 → CANCELLED_BEFORE_HANDOVER
```

**FR-L-16** Every transition is an immutable event with actor, timestamp, geo (where applicable), source system and evidence references. The shipment event log is the legal record for disputes and the data source for all metrics.

### 4.3 Return

```
RETURN_REQUESTED → APPROVED (auto or manual)
 → LABEL_ISSUED → AWAITING_DROPOFF/PICKUP
 → RECEIVED_AT_PUDO (inspection protocol)
 → IN_TRANSIT_TO_SELLER → RECEIVED_BY_SELLER
 → INSPECTED_OK → REFUND_RELEASED
 ↘ INSPECTED_DISPUTED → ARBITRATION → REFUND | PARTIAL | REJECTED
 ↘ REFUND_WITHOUT_RETURN (low-value rule)
```

---

## 5. The promise: turning "seller ships it" into a reliable date

### 5.1 Components of the promise

```
promise_date = cutoff_adjusted_order_time
             + handling_time(seller, category)        ← modelled, not declared
             + first_mile_lag(carrier, origin_zone)
             + line_haul(lane)                        ← distribution, use P80
             + last_mile(destination_zone, mode)
             + calendar_effects(weekends, holidays)
             + adaptive_buffer(seller_DOP, carrier_score)
```

- **FR-L-17** Handling time is **measured, not trusted**: the declared value is used only until 20 shipments of history exist, then the modelled P80 of actual accept→handover time governs.
- **FR-L-18** The promise degrades gracefully: a seller who is chronically late is not fined but automatically shown with a *longer, honest* promise — which costs them conversions and gives them a rational incentive to improve. **Honesty over punishment** is the governing principle of this subsystem.
- **FR-L-19** Real-time capacity: as a seller's daily accepted orders approach declared capacity, the promise for subsequent orders rolls forward one working day.
- **FR-L-20** Force-majeure mode: an operator can flag a region/lane (weather, road closure, holiday surge); promises are recomputed and the affected shipments are excluded from seller and carrier metrics.

### 5.2 Promise-at-risk monitoring

- **FR-L-21** A streaming job evaluates every open shipment against its expected milestone timeline. Missing a milestone by more than the lane's tolerance raises a risk event.
- **FR-L-22** Risk playbooks (configurable): notify seller → auto-rebook pickup → reroute to another carrier → notify buyer with options → offer compensation (wallet credit) → cancel with full refund.
- **FR-L-23** Compensation policy is published: if a shipment is delivered later than promised by more than the tolerance and the fault is the platform's or the carrier's, the buyer receives an automatic wallet credit; the seller is not charged for a fault that is not theirs.

---

## 6. Returns without a warehouse — the designed answer

### 6.1 Problem statement

In an FBO model returns flow back to the marketplace's own FC, which inspects, restocks and refunds. We have no FC. Returns must therefore be (a) routed to the seller, (b) inspected by a neutral party, and (c) economically survivable for a small seller.

### 6.2 Routing decision engine

**FR-L-24** For each return the engine chooses among:

| Path | When |
|---|---|
| **In-store return** to the seller's own point | Buyer and seller in the same city; cheapest and fastest |
| **PUDO drop-off + consolidated return leg** | Default; returns to one seller accumulate at the PUDO and travel back in one movement |
| **Courier pickup from buyer** | High-value, bulky, or a platform-fault return |
| **Refund without return** | Return logistics cost > item value × configurable factor; seller-configurable with a monthly cap and abuse controls |
| **Redirect to next buyer** (Phase 3) | Item verified as intact at PUDO and already reserved by another local buyer — the return leg becomes an outbound leg |

The last option is only possible in a distributed model and is a genuine structural advantage: a returned item sitting at a PUDO is already closer to the next buyer than a warehouse would be.

### 6.3 Neutral inspection protocol

- **FR-L-25** At PUDO intake, staff follow a scripted capture flow: scan return label → photograph the sealed parcel → open → photograph contents, serial/marking code, condition → record completeness checklist → seal and dispatch. All artefacts are timestamped, geotagged and immutable.
- **FR-L-26** This evidence, combined with the seller's original packing photo (FR-S-19), resolves the majority of "not as described" / "wrong item" / "empty box" disputes deterministically.

### 6.4 Economics

- **FR-L-27** Return-Insurance Pool: contribution rate published (initial target 0.5–1.5% of order value, category-dependent), pool covers the logistics cost of no-fault returns and part of the loss on refund-without-return; quarterly public reporting of inflows, outflows and balance.
- **FR-L-28** Fault-based cost allocation: seller-fault returns (wrong item, defect, not as described) are charged to the seller; buyer-fault returns (changed mind) are charged per the statutory allocation and the seller's published return policy; carrier-fault (damage in transit) triggers a carrier claim.
- **FR-L-29** Carrier claims automation: claim creation, evidence packaging, deadline tracking, recovery accounting.

---

## 7. Cash on delivery — a first-class citizen

COD is a majority payment method in the target market and a common source of financial leakage.

- **FR-L-30** COD amount is bound to the shipment; carriers receive it via the adapter and must confirm collection with a fiscal-compliant flow.
- **FR-L-31** Daily automated three-way reconciliation: platform expected COD ⇄ carrier remittance report ⇄ bank credit. Breaks open a case with an owner and an SLA; break rate is a carrier scorecard metric.
- **FR-L-32** COD risk controls: per-buyer COD limits based on history, address risk, and refusal rate; graduated restrictions for serial refusers; COD disabled for high-value orders above a configurable threshold.
- **FR-L-33** COD refusal ("buyer did not collect") is a costed event: the return leg is paid per the fault-attribution rules and the buyer's COD standing is updated.
- **FR-L-34** Fiscal receipt for a COD sale is issued at the moment of payment collection, with the receipt data transmitted in real time as required by law, and delivered to the buyer digitally.

---

## 8. Packaging, evidence and quality at source

Because no one at a warehouse ever sees the goods, the packing moment is the only quality gate. It must be instrumented.

- **FR-L-35** Mandatory scan of item barcode/GTIN at packing; mandatory datamatrix scan for marked categories with online validation of the code.
- **FR-L-36** Mandatory sealed-parcel photo with the parcel label visible; optional short packing video for high-value categories (configurable per category and per seller risk tier).
- **FR-L-37** Tamper-evident platform-branded packaging/seal offered as a paid value-added service, and mandatory for high-value or high-dispute categories.
- **FR-L-38** Weight/dimension capture at handover by the carrier; mismatch vs declared parameters is an automatic exception (it is the classic signal for wrong or missing contents, and for tariff evasion).
- **FR-L-39** Evidence retention: 180 days minimum for standard orders, 1 year for disputed ones, with access strictly logged.

---

## 9. Seller self-delivery (SDD) and store pickup (SPU)

- **FR-L-40** SDD requires a declared delivery zone (polygon on map), price rules, working hours and courier sub-accounts. Courier position is tracked during the delivery leg; delivery is confirmed by buyer OTP.
- **FR-L-41** SDD shipments are held to the same metrics and evidence standards as carrier shipments; a seller who fails SDD SLAs is automatically moved to SFD.
- **FR-L-42** SPU: buyer receives a pickup code and the store's map point and hours; the seller confirms the handover by scanning the code. Reservation hold period configurable (default 72 h) with automatic release.
- **FR-L-43** All modes produce identical canonical events, so metrics, disputes and money flows are mode-agnostic.

---

## 10. Capacity, surge and peak management

- **FR-L-44** Capacity planning dashboard: forecast of parcel volume per lane per day, carrier committed capacity, and gap alerts.
- **FR-L-45** Peak protocol (11.11, New Year, Navruz, Ramadan): automatic promise-buffer widening, carrier capacity pre-booking, seller communication campaign, temporary restriction of new-seller SFD onboarding on saturated lanes.
- **FR-L-46** Regional expansion playbook encoded as configuration: adding a city means adding lanes, PUDO points and tariffs — no capital project, which is the entire point of this model.

---

## 11. Logistics KPIs

| KPI | Definition | Target |
|---|---|---|
| DOP | delivered ≤ promised date / all delivered | ≥ 92% Y1, ≥ 95% Y2 |
| Promise accuracy (MAE) | mean absolute error, promised vs actual, in days | ≤ 0.6 d |
| On-time pickup | pickups completed within the booked window | ≥ 95% |
| First-attempt delivery | delivered on first attempt / all delivered | ≥ 88% |
| Damage rate | damaged shipments / all | ≤ 0.3% |
| Loss rate | lost shipments / all | ≤ 0.1% |
| Return rate | returns / delivered | ≤ 8% (category-adjusted) |
| Return cycle time | request → refund released | ≤ 7 days median |
| COD break rate | unreconciled COD value / total COD | ≤ 0.1% |
| Cost per delivered parcel | total logistics cost / delivered parcels | tracked per lane, target −15% Y2 vs Y1 |

---

*Continues in [Part 3 — System Architecture, Data, Integrations and Non-Functional Requirements](./03-architecture-and-nfr.md).*
