# Technical Task — Part 4: Delivery Plan, Team, Risks and Acceptance

---

## 1. Delivery strategy

The model's core risk is **fulfillment consistency**, not software. Therefore the plan front-loads the promise/logistics subsystem and deliberately launches narrow: one city, few categories, hand-picked sellers, two carriers — and expands only when DOP holds.

Sequencing principle: *prove the promise before scaling the catalogue.*

---

## 2. Phases

### Phase 0 — Foundation (weeks 1–6)

| Deliverable | Detail |
|---|---|
| Discovery and validation | 30+ seller interviews (bazaar, single-shop, online-native), 10+ carrier and PUDO commercial conversations, buyer research on delivery-promise sensitivity |
| Legal and fiscal design | Public offer, seller contract, fiscal agency model for ChEK, escrow/split-payment structure with a licensed payment organisation, personal-data compliance plan |
| Commercial pre-agreements | ≥ 2 carriers with API integration paths; ≥ 1 PUDO/locker network; PSP with split + holding |
| Architecture decision records | ADR-001 mobile stack, ADR-002 backend language, ADR-003 escrow structure, ADR-004 fiscal integration, ADR-005 search engine, ADR-006 event backbone |
| Design system + key flows | Buyer checkout, seller pack-and-ship, returns |
| Environment and CI/CD | Kubernetes, IaC, pipelines, observability baseline |

**Exit criteria:** signed LOIs with 2 carriers and 1 PSP; fiscal integration approach validated with a provider; ADRs approved.

### Phase 1 — MVP, closed pilot (weeks 7–22, ~4 months)

Scope — the minimum that can honestly promise a delivery date and pay a seller correctly:

- Buyer web + Android; seller Android app + minimal web dashboard; back office.
- Identity, KYC/KYB (manual-assisted), single-category-tree PIM with 3–5 categories, offers with stock and capacity.
- Search with facets and location-aware ranking (v1, rules-based ranking; no ads).
- **Promise Engine v1**: declared handling time + lane statistics + conservative buffers; P80 rule; promise frozen into the order.
- Cart with multi-seller split, checkout with card + wallet + COD.
- Escrow via PSP holding; ledger; fee engine with versioned rules; fee calculator.
- **Fiscal receipts live** (non-negotiable for legal launch).
- Logistics orchestrator with 2 carrier adapters + SDD + SPU; label service; tracking normalisation; exception manager v1.
- Returns v1: PUDO drop-off + courier pickup, inspection protocol, refunds.
- Disputes v1 with evidence timeline.
- Trust Score v1 (subset of components) with a visible score card.
- Notifications (push/SMS/Telegram).
- Analytics: DOP, funnel, seller economics.

**Pilot shape:** Tashkent, 100–200 hand-picked sellers, 5,000–10,000 SKUs, invite-only buyers.
**Exit criteria (all must hold for 4 consecutive weeks):** DOP ≥ 88%; seller cancellation rate < 3%; COD break rate < 0.3%; fiscal receipt failure rate < 0.1%; median dispute resolution < 96 h; NPS(seller) ≥ 30.

### Phase 2 — Public launch, Tashkent + 3 regional cities (weeks 23–40)

- iOS app; buyer web SEO hardening; guest checkout.
- Photo-first AI-assisted listing creation; bulk import; seller API + webhooks + sandbox.
- Promise Engine v2 (learned handling-time and lane models, adaptive buffers, promise-at-risk playbooks).
- Trust Score full model, tiers, tier-based payout speed, appeals workflow.
- Returns v2: routing decision engine, refund-without-return, return-insurance pool, abuse scoring.
- Ads (labelled, density-capped), self-serve campaigns.
- Reviews + Q&A with integrity controls; brand authorisation registry; rights-holder portal.
- 3rd–4th carrier, locker integration, partner PUDO points.
- Risk/fraud engine; COD limits; attribution engine v1.
- Instalment/BNPL; loyalty and wallet cashback.

**Exit criteria:** DOP ≥ 92%; 1,500+ active sellers; 300k+ SKUs; take-rate model validated on real cohorts; unit economics per order positive before marketing.

### Phase 3 — Scale and differentiate (weeks 41–72)

- Nationwide lane coverage; regional seller onboarding programme.
- Cross-dock transit (XDT) for inter-city consolidation (≤ 24 h, rented).
- "Return redirect to next buyer" flow.
- POS/1C stock synchronisation; seller financing referral (data-backed underwriting from platform history).
- Mystery-shopper programme at scale; advanced counterfeit detection (image + graph based).
- Portable reputation certificates; public transparency reports (takedowns, disputes, pool balance, ranking changelog).
- B2B/wholesale exploration; cross-border seller pilots.

---

## 3. Team and effort

| Role | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Product manager | 2 | 3 | 4 |
| Product designer / UX researcher | 2 | 3 | 3 |
| Backend engineer | 8 | 12 | 16 |
| Frontend (web) | 3 | 4 | 5 |
| Mobile (Android/iOS) | 3 | 5 | 6 |
| Data engineer | 2 | 3 | 4 |
| ML engineer (promise, ranking, risk) | 1 | 3 | 4 |
| QA / SDET | 3 | 4 | 6 |
| DevOps / SRE | 2 | 3 | 4 |
| Security engineer | 0.5 | 1 | 2 |
| Analyst | 1 | 2 | 3 |
| **Engineering total (FTE)** | **~27** | **~43** | **~57** |
| Ops: seller onboarding, support, T&S, logistics ops, finance ops | 10 | 35 | 80+ |

Indicative build effort to Phase 2 exit: **≈ 420–520 engineering man-months**. Phase 1 alone: ≈ 110–130 man-months.

---

## 4. Risk register

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | Sellers cannot hold the delivery promise → buyer churn | Critical | High | Promise Engine with honest, adaptive buffers; capacity limits; pilot with vetted sellers; stock-freshness demotion; DOP gates on expansion |
| R2 | Stock inaccuracy (item sold offline in the shop) | High | High | Daily one-tap confirmation, POS sync, cancellation-rate-driven demotion, auto-pause thresholds, buffer-stock guidance |
| R3 | Carrier dependency / poor carrier performance | High | Medium | ≥ 2 carriers per lane, scorecard-driven routing, manual-carrier portal for long-tail coverage, no exclusivity contracts |
| R4 | Returns become economically unbearable for small sellers | High | Medium | Return-insurance pool, refund-without-return rule, in-store returns, fault-based cost allocation |
| R5 | Counterfeits damage trust early | High | Medium | KYB, brand authorisation registry, marking codes, mystery shopping, 24-h takedown, no purchasable authenticity badge |
| R6 | Fiscal/receipt non-compliance | Critical (legal) | Medium | Certified provider, P0 alarms, automatic retry queue, daily compliance report, penalty exposure modelled |
| R7 | COD leakage and cash fraud | High | Medium | Three-way daily reconciliation, carrier scorecards, COD limits and risk scoring |
| R8 | Incumbent price war / seller exclusivity pressure | High | Medium | Non-exclusivity by design, lower take rate, data portability, multi-homing tooling so sellers can run both platforms cheaply |
| R9 | Cold-start: no buyers without sellers and vice versa | Critical | High | Category-narrow launch, hand-picked supply, "only here" categories that FC models cannot carry (bulky, fragile, made-to-order, hazardous, ultra-premium) |
| R10 | Fraudulent sellers exploiting a warehouse-free model (never shipping) | High | Medium | Escrow, staged payout tiers, new-seller reserves, packing-evidence requirements, velocity limits |
| R11 | Promise model bias against new/low-volume sellers | Medium | Medium | Bayesian shrinkage, exploration quota for new offers, category-level priors |
| R12 | Regulatory change (commissions, marking, data) | Medium | Medium | Configuration-driven policy, versioned fee rules, legal watch, transparency-first posture |
| R13 | Peak-season collapse | High | Medium | Peak protocol, pre-booked carrier capacity, buffer widening, load tests at 10× |
| R14 | Team execution risk on a broad scope | High | Medium | Strict phase gates, thin-slice MVP, buy-not-build for payments/fiscal/carriers |

---

## 5. Critical user journeys (must be covered by end-to-end automated tests)

1. Buyer finds a product, sees a promise, buys from one seller by card → delivered on time → receipt issued → seller paid.
2. Multi-seller basket → split into three shipments with different promises and modes → all delivered → split settlement correct.
3. COD order → delivered → cash collected by carrier → reconciled → commission netted → seller paid.
4. Seller accepts, packs with scan evidence, carrier pickup fails, shipment rerouted, still delivered on promise; seller metrics unaffected (attribution).
5. Out-of-stock cancellation → automatic full refund → seller metric and ranking impact → stock-freshness demotion.
6. Return via PUDO with neutral inspection → refund released → cost allocated to the faulting party.
7. Refund-without-return under the low-value rule, with pool accounting.
8. "Not as described" dispute resolved using packing photo + inspection evidence.
9. Counterfeit report by rights holder → listing down within 24 h → seller sanction → appeal.
10. Fee-rule change published with 60 days' notice; orders before the effective date are settled at the old rule.
11. Promise-at-risk detected → buyer notified with options → buyer cancels → full refund within SLA.
12. Seller data export including signed reputation certificate; account closure with obligations settled.

---

## 6. Acceptance criteria

### 6.1 Functional acceptance

- All requirements marked **FR-*** in Parts 1–3 are implemented, demonstrable, and covered by tests; any deferral is explicitly accepted in writing with a target phase.
- All 12 critical journeys pass in the staging environment and in a production smoke suite.
- Back-office roles, audit log and four-eyes controls verified by an internal audit walkthrough.

### 6.2 Non-functional acceptance

- Performance targets (NFR-P-*) demonstrated under a load test at 10× expected average traffic.
- Failover drill executed: RPO ≤ 5 min, RTO ≤ 60 min evidenced.
- Penetration test completed with no open Critical or High findings.
- Fiscal receipt success rate ≥ 99.9% over a 30-day window with alerting proven.
- Degradation matrix verified by chaos tests (kill a carrier adapter, a PSP, the ads service, the promise service).

### 6.3 Business acceptance (gate to public launch)

| Gate | Threshold |
|---|---|
| DOP over 4 consecutive weeks | ≥ 88% (MVP) / ≥ 92% (public) |
| Seller-caused cancellation rate | < 3% (MVP) / < 1.5% (public) |
| Order defect rate | < 1% |
| COD reconciliation break rate | < 0.1% |
| Median dispute resolution | < 72 h |
| Refund SLA compliance | ≥ 98% within 3 business days |
| Seller onboarding time (median) | ≤ 60 min to first live listing |
| Governance controls G1–G10 | 100% implemented and audited |

### 6.4 Governance acceptance

Each of the ten commitments in Part 1 §9 must be demonstrated as an **enforced control**, not a policy statement:
a test that proves a platform-owned seller cannot be created; a test that a promotion without seller opt-in is rejected; a test that a fee change cannot take effect before its notice period; a test that a logistics fee rule with a price-based term is rejected; a test that the search page never exceeds the ad-density cap; a nightly job report showing no holds past their release date.

---

## 7. Deliverables

1. Running system: buyer web, buyer mobile (iOS/Android), seller mobile + web, back office, carrier/PUDO portal.
2. Public seller API with documentation, sandbox and client examples.
3. Operational runbooks: incident management, peak protocol, carrier onboarding, seller onboarding, dispute arbitration guidelines, COD reconciliation.
4. Published policy set: fee schedule and changelog, ranking factors, trust-score formula, return policy, buyer protection terms, advertising policy, transparency report template.
5. Data platform with the mandatory dashboards (Part 3 §7).
6. Test artefacts: automated suites, load-test reports, penetration-test report, chaos-test results.
7. Architecture documentation: ADRs, service map, data model, integration contracts, threat model.

---

## 8. Open questions for the business owner

These block or reshape parts of the specification and should be answered before Phase 1 starts:

1. **Legal structure of escrow** — will funds be held by a licensed payment organisation (recommended, faster) or by the platform under its own licence (slower, more control)?
2. **Fiscal agency** — will the platform issue ChEK on behalf of sellers as their technical agent, or will each seller connect their own virtual cash register (with the platform enforcing compliance)? This changes INT-06 substantially.
3. **Launch categories** — recommended: bulky/heavy goods, furniture, construction materials, made-to-order and handmade, high-value electronics, and other categories that FC-based competitors structurally cannot serve well. Confirm.
4. **Target commission band** by category, and the initial return-insurance-pool contribution rate.
5. **Carrier strategy** — pure brokerage, or brokerage plus a small owned last-mile crew in Tashkent for premium lanes?
6. **Cross-dock (XDT)** — accept it in Phase 3, or hold the "zero physical footprint" line absolutely as a brand position?
7. **COD policy** — allowed everywhere from day one, or restricted to trusted buyers/lanes initially?
8. **Brand position on ads** — is the ad-density cap a permanent public commitment (recommended, it is the strongest differentiator against incumbent search-page degradation) or a launch-phase setting?
9. **Geography of Phase 2** — which three regional cities, based on carrier lane cost and seller density?
10. **Multi-homing stance** — will the platform actively build tools that make it cheap for a seller to run on this platform *and* on incumbents (recommended: it is how a challenger acquires supply), or pursue exclusivity incentives?

---

## 9. Summary

The model's advantage is structural: no warehouses means no storage fees, no size limits, no capital burn, no inventory conflict of interest, and the ability to enter any city with a contract rather than a construction project. Its weakness is equally structural: consistency, quality control and returns are no longer solved by a building.

This Technical Task converts that trade explicitly. The building is replaced by five engineered systems — the **Promise Engine**, the **Logistics Orchestrator**, the **Evidence Chain**, the **Trust Score**, and the **Returns Routing Engine** — and by a governance model that makes predictability and transparency the product's defining feature, precisely where every incumbent studied in Part 0 is currently losing the trust of its sellers, its buyers, and its regulators.
