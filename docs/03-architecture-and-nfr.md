# Technical Task — Part 3: Architecture, Data, Integrations and Non-Functional Requirements

---

## 1. Architectural principles

1. **Domain-oriented services** with clear ownership; no shared database between services.
2. **Event-driven core.** Order, shipment, payment and trust events are published to an append-only log (Kafka); services subscribe rather than call each other synchronously wherever latency permits.
3. **Idempotency everywhere** — every externally triggered command carries an idempotency key; every carrier/PSP webhook is replay-safe.
4. **The ledger is the truth for money**; the event log is the truth for logistics; both are immutable and reconcilable.
5. **API-first.** The seller API and the internal API are the same API with different scopes. No private back doors for first-party clients.
6. **Configuration over code** for tariffs, fees, categories, policies, SLAs — all versioned with effective dates.
7. **Explainability as a feature.** Every automated decision (promise, ranking, score, hold, moderation) stores its inputs and its reason, retrievable through an API.
8. **Graceful degradation.** Search, checkout and order intake must survive the loss of ranking personalisation, ads, recommendations, or any single carrier.

---

## 2. Service map

| Domain | Service | Responsibility |
|---|---|---|
| Identity | `identity` | Buyers, sellers, staff, roles, sessions, OTP, e-signature |
| Identity | `kyc` | KYB/KYC verification, registry lookups, document vault, re-verification cycles |
| Catalogue | `pim` | Products, categories, attribute schemas, brands, media |
| Catalogue | `offer` | Seller offers, prices, stock, capacity, pickup locations |
| Catalogue | `moderation` | Automated + manual review, prohibited items, brand authorisation |
| Discovery | `search` | Indexing, query understanding, ranking, facets (OpenSearch) |
| Discovery | `recommend` | Personalisation, similar items, complementary items |
| Discovery | `ads` | Campaigns, auction, budget, labelled placements |
| Promise | `promise` | Delivery-date computation, capacity, risk detection, backtesting |
| Ordering | `cart` | Basket, shipment splitting, shipping-cost calculation |
| Ordering | `order` | Order lifecycle, cancellations, order-level saga orchestration |
| Logistics | `logistics-orchestrator` | Routing, rate shopping, bookings, labels, exceptions |
| Logistics | `carrier-gateway` | Carrier adapters, webhook ingestion, status normalisation |
| Logistics | `pudo` | Points registry, availability, inspection protocol |
| Money | `payment` | PSP integrations, authorisation, capture, refunds, escrow |
| Money | `ledger` | Double-entry accounting, fees, payouts, COD reconciliation |
| Money | `fee-engine` | Versioned fee rules, calculator API |
| Money | `fiscal` | Online ChEK issuance, e-invoices, tax reports |
| Trust | `trust-score` | STS computation, tiers, explanations, appeals |
| Trust | `risk` | Fraud, abuse, device fingerprinting, COD risk |
| Trust | `attribution` | Fault attribution across seller/carrier/buyer/platform |
| Aftersales | `returns` | Return lifecycle, routing engine, insurance pool |
| Aftersales | `dispute` | Arbitration workbench, evidence assembly, SLAs |
| Content | `review` | Verified-purchase reviews, Q&A, integrity checks |
| Comms | `notification` | Push, SMS, e-mail, Telegram, in-app; template and locale management |
| Ops | `backoffice` | Admin UI backends, audit log, feature flags |
| Data | `analytics` | Event pipeline, warehouse, dashboards, seller analytics API |

### 2.1 Client applications

| Client | Stack | Notes |
|---|---|---|
| Buyer web | Next.js (SSR for SEO), TypeScript | Core SEO surface; must be fast on 3G |
| Buyer mobile | React Native or native (decision in ADR-001) | iOS + Android |
| Seller app | **Android-first**, offline-tolerant | Barcode/datamatrix scanning, camera evidence, works in bazaars with weak connectivity |
| Seller web | React + TypeScript | Bulk operations, analytics, finance |
| Back office | React + TypeScript | Role-scoped |
| Carrier/PUDO portal | Lightweight web + Android scanner app | For partners without APIs |

### 2.2 Reference technology stack (proposed, subject to ADRs)

- Backend: Java/Kotlin (Spring Boot) or Go for high-throughput services; Python for ML services (promise, ranking, risk).
- Data stores: PostgreSQL (per service), Redis (cache, locks, rate limits), OpenSearch (search), ClickHouse (analytics), S3-compatible object storage (media, evidence), Kafka (event backbone).
- Infrastructure: Kubernetes, IaC (Terraform), GitOps, OpenTelemetry + Prometheus + Grafana + Loki, feature flags (Unleash/Flagsmith).
- ML: feature store, batch training pipeline, model registry, shadow deployment for the promise and ranking models.

---

## 3. Core data model (essential entities)

```
Party
 ├─ Buyer(id, phone, locale, addresses[], risk_profile, cod_standing, loyalty)
 └─ Seller(id, legal_type, legal_name, tax_id/STIR, registry_data, kyc_status,
           contract_version, trust_score, tier, payout_terms, reserve_policy)
      ├─ SellerLocation(id, seller_id, type[STORE|WAREHOUSE|HOME], geo, address,
      │                 working_calendar, cutoff_time, handling_time_declared,
      │                 daily_capacity, is_pickup_point, is_return_address)
      └─ SellerStaff(id, seller_id, role, permissions[])

Product (PIM)
 ├─ id, category_id, brand_id, gtin[], title_i18n, attributes{}, media[], status
 └─ Category(id, parent_id, attribute_schema, commission_rule_id, policy_flags)

Offer
 ├─ id, product_id, seller_id, location_id, price, currency, stock_qty,
 ├─ stock_confirmed_at, fulfillment_modes[], handling_time_model_ref,
 ├─ return_policy_id, status, marking_required, brand_authorisation_id
 └─ OfferPromiseCache(offer_id, geo_zone, promise_date, p_on_time, computed_at)

Order
 ├─ id, buyer_id, created_at, currency, totals{}, payment_method, status
 ├─ fee_rule_version, promise_snapshot{}, fiscal_docs[]
 └─ Shipment
      ├─ id, order_id, seller_id, location_id, mode, carrier_id, lane_id
      ├─ promised_date, promised_at, actual_delivered_at, tracking_no
      ├─ cod_amount, weight, dims, label_ref, status
      ├─ ShipmentItem(offer_id, qty, unit_price, marking_codes[])
      └─ ShipmentEvent(id, type, actor, ts, geo, evidence_refs[], source)

Return(id, shipment_id, reason_code, path, status, inspection_ref, refund_ref,
       fault_party, cost_allocation{})

Dispute(id, order_id/shipment_id, opened_by, type, evidence[], sla_due_at,
        decision, decision_reason, decided_by, appeal_ref)

LedgerEntry(id, account_id, order_ref, type, amount, sign, fee_rule_ref,
            created_at, immutable)
Account(id, owner_type[SELLER|PLATFORM|BUYER_WALLET|POOL|CARRIER], balance)

FeeRule(id, type, scope, formula, effective_from, effective_to, version,
        notice_published_at)

TrustScoreSnapshot(seller_id, ts, total, components{}, tier, explanation[])

Carrier(id, name, lanes[], tariffs[], sla{}, scorecard{}, api_config)
Lane(id, carrier_id, origin_zone, destination_zone, transit_distribution,
     cutoff, cost_model, cod_supported, max_dims)

PudoPoint(id, operator_id, geo, hours, capacity, sizes[], cod, returns_intake)

EvidenceArtifact(id, kind[PACK_PHOTO|POD_PHOTO|INSPECTION_VIDEO|SCAN],
                 ref, sha256, ts, geo, retention_until)
```

**Invariants:**
- `Seller.legal_type` may never be `PLATFORM` (governance commitment G1).
- An `Order` is always priced by the `FeeRule` version referenced in `fee_rule_version`; later fee changes can never alter a settled order.
- Every `LedgerEntry` referencing a fee must reference a `FeeRule` version.
- `Shipment.promised_date` is immutable after order creation; changes create a new `PromiseRevision` record with a reason.

---

## 4. Key API surfaces (illustrative contract)

### 4.1 Seller API (public, OAuth2 client credentials, scoped)

```
POST   /v1/offers                      create/update offers (bulk supported)
PATCH  /v1/offers/{id}/stock           stock and capacity update
POST   /v1/offers/{id}/pause
GET    /v1/orders?status=NEW           poll (webhooks preferred)
POST   /v1/shipments/{id}/accept
POST   /v1/shipments/{id}/pack         body: item scans, marking codes, parcel photo ref
GET    /v1/shipments/{id}/label        PDF/ZPL
POST   /v1/shipments/{id}/handover
POST   /v1/returns/{id}/inspection
GET    /v1/finance/ledger?from=&to=
GET    /v1/finance/fee-quote?category=&price=&mode=&destination=
GET    /v1/trust/score                 full component breakdown + improvement actions
GET    /v1/export/all                  full data export incl. signed reputation certificate
```

Webhooks: `order.created`, `shipment.state_changed`, `return.requested`, `dispute.opened`, `payout.settled`, `policy.changed`, `fee_rule.published`.

### 4.2 Internal contracts worth specifying up front

```
promise.quote(offer_ids[], destination_zone, at_time)
    → [{offer_id, mode, promise_date, p_on_time, explanation}]

logistics.route(shipment_draft)
    → [{carrier_id, lane_id, cost, eta_distribution, constraints_ok}]

attribution.resolve(shipment_id, failure_type)
    → {party, confidence, evidence_refs[]}

fee.calculate(order_draft, at_time)
    → [{line, amount, fee_rule_id, version, human_explanation}]
```

Every one of these returns a human-readable explanation field. This is a hard requirement, not a nicety: it is what makes the transparency commitments enforceable and auditable.

---

## 5. External integrations

| # | Integration | Purpose | Criticality |
|---|---|---|---|
| INT-01 | Uzcard / Humo acquiring (via licensed PSP) | Card payments | Blocker |
| INT-02 | Payme / Click / Uzum wallets | Wallet payments | Blocker |
| INT-03 | Visa / Mastercard | Cards, incl. foreign | High |
| INT-04 | Payment organisation with **split payments and holding** (escrow) | Multi-seller settlement, escrow | Blocker |
| INT-05 | Bank(s) for payouts and reconciliation statements | Seller payouts, COD | Blocker |
| INT-06 | Online cash register / virtual ChEK provider | Fiscal receipts per transaction, real-time transmission to the Tax Committee | **Legal blocker** |
| INT-07 | ASL BELGISI marking system | Datamatrix validation for marked categories | Legal, category-dependent |
| INT-08 | E-invoicing (ЭСФ) | Commission and service invoices to sellers | High |
| INT-09 | State registries (tax/business registry) | KYB verification of sellers | High |
| INT-10 | E-signature (ERI) | Contract signing by legal entities | High |
| INT-11 | Carriers: BTS Express, Fargo (incl. lockers), Yandex Delivery, Uzpost, regional couriers | Fulfillment | Blocker (≥ 2 at launch) |
| INT-12 | Maps and geocoding | Addressing, zones, routing, PUDO map | Blocker |
| INT-13 | SMS gateway + push (FCM/APNs) + Telegram bot | Notifications | Blocker |
| INT-14 | KYC/AML screening | Sanction and PEP checks for large sellers | Medium |
| INT-15 | Analytics/BI, error tracking, product analytics | Operations | High |
| INT-16 | BNPL/instalment providers | Payment options (Phase 2) | Medium |
| INT-17 | Accounting/POS systems used by local sellers (1C and local equivalents) | Stock sync (Phase 2) | Medium |

**Integration requirements:**
- **FR-I-01** Every external integration sits behind an anti-corruption layer with its own contract tests, sandbox configuration and circuit breaker.
- **FR-I-02** No integration may be a single point of failure for checkout: at least two payment routes and at least two carriers per major lane must be live before public launch.
- **FR-I-03** All fiscal and financial integration traffic is logged immutably for the statutory retention period.

---

## 6. Non-functional requirements

### 6.1 Performance

| ID | Requirement |
|---|---|
| NFR-P-01 | Search response p95 ≤ 300 ms, p99 ≤ 700 ms at 500 RPS |
| NFR-P-02 | Product page (server-rendered, cached) TTFB p95 ≤ 400 ms; LCP ≤ 2.5 s on a 3G-class connection |
| NFR-P-03 | Promise quote for a result page of 48 offers ≤ 120 ms (served from cache; cold compute ≤ 400 ms) |
| NFR-P-04 | Checkout order-creation p95 ≤ 1.5 s including payment authorisation initiation |
| NFR-P-05 | Seller app must function offline for pick/pack/scan and sync on reconnect |
| NFR-P-06 | Peak capacity: 10× average traffic without degradation; load-tested before each peak season |

### 6.2 Availability and resilience

| ID | Requirement |
|---|---|
| NFR-A-01 | Availability: 99.9% monthly for buyer-facing read paths; 99.95% for checkout and payment |
| NFR-A-02 | RPO ≤ 5 min, RTO ≤ 60 min; documented and drilled quarterly |
| NFR-A-03 | Zero-downtime deploys; every service independently deployable |
| NFR-A-04 | Degradation matrix defined per service (e.g. ads down → page renders without ads; promise down → fall back to conservative static promise) |
| NFR-A-05 | Carrier or PSP outage must not block order intake |

### 6.3 Security and privacy

| ID | Requirement |
|---|---|
| NFR-S-01 | OWASP ASVS Level 2 compliance; annual penetration test; SAST/DAST/dependency scanning in CI |
| NFR-S-02 | No card data touches platform infrastructure (PSP tokenisation; PCI-DSS SAQ-A scope) |
| NFR-S-03 | Personal data of citizens stored and processed on infrastructure located in Uzbekistan; documented data map and retention schedule |
| NFR-S-04 | Encryption at rest for PII, documents and evidence; TLS 1.3 in transit; KMS-managed keys with rotation |
| NFR-S-05 | RBAC + ABAC in back office; four-eyes approval for financial adjustments, payout runs, fee-rule publication and mass moderation actions |
| NFR-S-06 | Immutable, tamper-evident audit log for all administrative and financial actions; read-only auditor role |
| NFR-S-07 | Secrets management, least-privilege service accounts, network segmentation between payment/fiscal services and the rest |
| NFR-S-08 | Rate limiting, bot detection and anti-scraping on public surfaces; API quotas per seller client |
| NFR-S-09 | Evidence artefacts (photos, videos, scans) hashed on write; hash chain published per shipment so tampering is detectable |

### 6.4 Compliance

| ID | Requirement |
|---|---|
| NFR-C-01 | A fiscal receipt is issued for every sale, in real time, containing seller data, item names, quantities, prices, VAT, unique transaction number, QR code and fiscal mark; failure is alarmed and queued for automatic retry (penalty exposure of 5–10 BHM per missing receipt makes this a P0 alarm) |
| NFR-C-02 | Marking-code validation for regulated categories at packing time |
| NFR-C-03 | Consumer-rights compliance: statutory return windows, refund deadlines, complete and accurate product/seller information, and contracts available in the required language(s) — the exact points on which the Competition Committee cited existing platforms |
| NFR-C-04 | Seller identity verified and displayed on every listing (DSA Art. 30-grade traceability adopted voluntarily as market-leading practice) |
| NFR-C-05 | Advertising clearly labelled; ranking parameters published |
| NFR-C-06 | Personal-data consent management, subject access, correction and deletion flows |
| NFR-C-07 | Records retention per tax and consumer legislation; legal hold capability |

### 6.5 Usability, localisation, accessibility

| ID | Requirement |
|---|---|
| NFR-U-01 | Full i18n: Uzbek (Latin), Uzbek (Cyrillic) input support, Russian, English; every string externalised; locale-aware formats |
| NFR-U-02 | Address model adapted to local reality: region → district → mahalla/landmark → map pin; the pin is authoritative for routing |
| NFR-U-03 | Seller app usable by a merchant with no e-commerce experience: ≤ 5 taps from "new order" to "label printed"; onboarding completable on a phone in under an hour |
| NFR-U-04 | WCAG 2.1 AA for buyer web |
| NFR-U-05 | Apps must work on low-end Android (Android 8+, 2 GB RAM) and on unstable networks |

### 6.6 Observability and quality

| ID | Requirement |
|---|---|
| NFR-O-01 | Distributed tracing across order → shipment → payment → payout; a single trace ID retrievable from any support screen |
| NFR-O-02 | Business-metric alerting (order drop, promise-breach spike, COD break, fiscal-receipt failures), not only infrastructure alerting |
| NFR-O-03 | Test pyramid: unit ≥ 70% coverage on domain logic, contract tests for every external integration, end-to-end suites for the 12 critical journeys (§ Part 4 §5), load tests before each release train |
| NFR-O-04 | Every algorithmic component (promise, ranking, STS, risk) has an offline evaluation harness and shadow-mode deployment before it affects users |
| NFR-O-05 | Incident management: severity taxonomy, on-call rota, blameless postmortems, public status page |

---

## 7. Analytics and data platform

- **FR-D-01** Event schema registry with versioned, validated events; client and server events unified by a single ID space.
- **FR-D-02** Warehouse layers: raw → cleansed → marts (orders, shipments, promise performance, seller economics, ad performance, trust).
- **FR-D-03** Mandatory data products: DOP dashboard by lane/carrier/seller/category; seller-economics cohort analysis; return-reason analytics; search-quality dashboard (null results, click depth, ad share); COD reconciliation dashboard.
- **FR-D-04** Experimentation platform with guardrail metrics enforced automatically (an experiment that raises ad density beyond policy or degrades DOP is auto-stopped).
- **FR-D-05** Seller-facing analytics API exposing the seller's own data without rate-limit tricks.

---

*Continues in [Part 4 — Delivery Plan, Team, Risks and Acceptance](./04-roadmap-and-acceptance.md).*
