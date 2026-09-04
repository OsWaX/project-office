# Technical Task — Website, Part A: Structure, Pages and UX

**Project:** NGM — Next-Generation Marketplace (warehouse-free, seller-shipped)
**Document:** Website TZ, Part A of 2
**Version:** 1.0 · **Date:** 2026-09-04 · **Status:** For review and approval
**Companion:** [Website TZ, Part B — Frontend Engineering, SEO, Analytics, Acceptance](./06-website-engineering-and-acceptance.md)
**Depends on:** [Part 1 — Product definition](./01-technical-task.md), [Part 2 — Logistics](./02-logistics-and-fulfillment.md), [Part 3 — Architecture](./03-architecture-and-nfr.md)

---

## 1. Purpose and scope

This document specifies the **web front-end** of the marketplace: every page, its blocks, data, states, interactions and acceptance criteria.

### 1.1 In scope

| Surface | Description | Priority |
|---|---|---|
| **Buyer storefront** (`www`) | Public, SEO-critical shopping site: home, catalogue, search, product, cart, checkout, buyer account | P0 |
| **Seller acquisition site** (`/sell`) | Landing, earnings calculator, fee schedule, registration entry | P0 |
| **Seller cabinet** (`seller.`) | Web dashboard: catalogue, orders, shipments, returns, finance, trust score, ads, settings | P0 |
| **Public policy centre** (`/policies`, `/help`) | Fee schedule + changelog, ranking factors, trust-score formula, buyer protection, returns, transparency reports | P0 (governance commitments G3/G5/G9 are only real if published) |
| **Back office** (`admin.`) | Internal operations UI | P1 — specified at block level here, detailed separately |
| **Carrier / PUDO portal** (`partner.`) | Scan-based status updates for partners without APIs | P1 |

### 1.2 Out of scope

Native mobile applications (separate TZ), the seller Android app, e-mail/SMS template design (owned by `notification`), and the marketing blog CMS beyond the integration contract in §11.

### 1.3 Guiding UX principles

1. **The promise is the hero.** A concrete delivery date appears on every surface where a price appears. Never "3–5 days"; always "Thursday, 10 Sep".
2. **The seller is a named, verified person or company** — visible on the card, the product page and the receipt. Trust is shown, not implied.
3. **No dark patterns.** No fake countdowns, no fake scarcity, no pre-ticked add-ons, no hidden fees at the last step, no unsubscribe mazes. Total-to-pay is honest from the first cart view.
4. **Ads are labelled and capped** (max 2 in the first 10 results, ≤ 20% of any page) — enforced in code, visible in UI.
5. **Low-end device first.** The primary buyer is on a mid-range Android phone on a congested 4G/3G network. Every decision defers to that.
6. **Explain every automated decision.** Why this offer was chosen, why this date, why this fee — one tap away, in plain language.

---

## 2. Audiences, devices and browser support

| Audience | Share (expected) | Primary device | Notes |
|---|---|---|---|
| Buyer, mobile web | 70–80% | Android 8+, 360–430 px | Often the first touch from search/social; must convert without an app install |
| Buyer, desktop | 15–25% | 1280–1920 px | Higher AOV, more comparison behaviour |
| Seller, desktop | — | 1366+ | Bulk operations, finance |
| Seller, mobile web | — | Android | Fallback when the app is unavailable; must at least accept orders and print labels via a shared link |

**Browser matrix (must pass full E2E):** Chrome / Android WebView (last 3 versions), Safari iOS 15+, Firefox (last 3), Edge (last 3), Samsung Internet (last 3), Opera Mini — **graceful degradation only** (server-rendered content readable, checkout not guaranteed).

**Locales:** `uz` (Latin, default), `ru`, `en`. Uzbek Cyrillic is supported **as search input** with transliteration, not as a separate UI locale in v1.

---

## 3. Information architecture and URL scheme

```
/                                    Home
/c/{category-slug}                   Category listing (PLP), nested: /c/electronics/phones
/s                                   Search results (?q=, facets as query params)
/p/{product-slug}-{productId}        Product page (PDP)
/p/{product-slug}-{productId}/offers All seller offers for the product
/seller/{sellerSlug}                 Seller storefront
/seller/{sellerSlug}/reviews         Seller reviews
/brand/{brandSlug}                   Brand page
/collections/{slug}                  Editorial / campaign landing
/cart                                Cart
/checkout                            Checkout (single page, stepped)
/checkout/success/{orderId}          Order confirmation
/account                             Buyer account hub
/account/orders                      Order list
/account/orders/{orderId}            Order detail + per-shipment tracking
/account/returns                     Returns list
/account/returns/new/{shipmentId}    Return wizard
/account/returns/{returnId}          Return detail
/account/disputes/{disputeId}        Dispute detail
/account/wallet                      Wallet, cashback, refunds
/account/addresses                   Address book
/account/wishlist                    Wishlist
/account/reviews                     My reviews (write / edit)
/account/settings                    Profile, language, notifications, privacy, data export
/auth/login                          Phone OTP (modal-first, page as fallback)
/track/{trackingCode}                Public tracking (no login, code-gated)
/sell                                Seller acquisition landing
/sell/calculator                     Earnings / fee calculator
/sell/register                       Seller registration + onboarding wizard
/policies/fees                       Fee schedule + changelog (G3)
/policies/ranking                    Ranking factors (G5)
/policies/trust-score                Trust score formula (G5)
/policies/buyer-protection           Buyer protection terms
/policies/returns                    Returns policy
/policies/advertising                Advertising policy + density cap (G8)
/policies/transparency               Transparency reports (takedowns, disputes, pool balance)
/policies/offer                      Public offer / terms (uz/ru/en, all versions archived)
/help, /help/{article-slug}          Help centre
/404, /500, /offline                 Error and offline pages
```

**Seller cabinet (`seller.` subdomain, no SEO):**

```
/                     Dashboard
/products             Catalogue (products + offers)
/products/new         Listing creation (3 paths)
/products/import      Bulk import (XLSX/CSV) + job status
/orders               Orders / shipments queue (NEW → ACCEPTED → PACKED → HANDOVER)
/orders/{id}          Shipment detail: pack screen, label, evidence, exceptions
/returns              Returns queue + inspection
/finance              Ledger, payouts, COD reconciliation, fee lines with rule versions
/finance/calculator   Fee quote tool
/trust                Trust Score Card: components, weights, targets, actions, appeals
/ads                  Campaigns
/analytics            Sales, funnel, promise performance, search terms
/settings/locations   Pickup locations, calendars, cutoffs, capacity, delivery zones
/settings/logistics   Carriers, preferred lanes, packaging
/settings/legal       KYB documents, contract versions, fiscal registration
/settings/api         API keys, webhooks, sandbox
/settings/staff       Sub-accounts and roles
```

**Canonical rules:** one product = one canonical URL regardless of the seller a buyer arrives through; seller-scoped deep links carry `?seller=` and canonicalise to the product URL (see Part B §5).

---

## 4. Global layout

### 4.1 Header (buyer storefront)

| Element | Behaviour |
|---|---|
| Logo | Home link |
| **Deliver-to selector** | City + address pin. Drives the promise on every card. Persisted in cookie + account. First visit: geolocate with permission, else default to Tashkent with a visible "change" affordance. **This control is the second-most-used element on the site after search — it must be in the primary header row on desktop and one tap from the top on mobile.** |
| Category menu | Mega menu (desktop, 2-level + promo slot); full-screen drawer (mobile) |
| **Search** | Always visible. Focus opens suggest overlay. On mobile, search occupies its own header row |
| Language switcher | uz / ru / en, preserves the current route |
| Account | Logged out: "Sign in"; logged in: avatar menu (orders, returns, wallet, wishlist, settings, sign out) |
| Wishlist | Count badge |
| Cart | Count badge + total; hover mini-cart on desktop, direct navigation on mobile |
| Seller entry | "Sell on NGM" link → `/sell` |

Sticky behaviour: header collapses to a compact bar (logo + search + cart) on scroll ≥ 120 px.

### 4.2 Footer

Four column groups + legal strip:

1. **Buyers** — how to order, delivery and pickup, payment methods, buyer protection, returns, track an order, help.
2. **Sellers** — sell on NGM, fee schedule, fee calculator, seller help, API docs, status page.
3. **Transparency** — ranking factors, trust-score formula, advertising policy, transparency reports, fee changelog. *(This block is a product feature, not boilerplate: it is the public proof of governance commitments G3, G5, G8, G9.)*
4. **Company** — about, contacts, careers, press, public offer.

Legal strip: legal entity name, registration number, address, tax ID, consumer-rights notice, e-commerce registry notice, payment-system logos, language notice.

### 4.3 Cross-cutting UI elements

- **Promise badge** (`<PromiseBadge>`): "Arrives Thu, 10 Sep" + mode icon + optional "from Chilanzar, 4 km". Tap → popover explaining how the date is computed (handling time + collection + transit) and the buyer's options if it is late.
- **Trust tier chip**: Bronze/Silver/Gold/Platinum with a tooltip and a link to `/policies/trust-score`.
- **Fulfillment mode icon set**: courier (SFD), seller courier (SDD), store pickup (SPU), pickup point/locker (SDP).
- **Ad label**: `Reklama · Реклама · Sponsored`, always rendered, never lighter than body text contrast ratio 4.5:1.
- **Price block**: current price, strike-through original **only** when a genuine prior price existed for ≥ 30 days (anti-dark-pattern rule, validated server-side).
- **Cookie/consent banner**: granular, no pre-ticked non-essential categories, decline is one click.

---

## 5. Buyer storefront — page specifications

Each specification uses: *Purpose · URL · Blocks · Data · States · Interactions · Mobile · SEO · Acceptance*.

### 5.1 Home — `/`

- **Purpose:** orient a first-time buyer, prove the model's differentiators, route to categories and campaigns.
- **Blocks (in order):**
  1. Deliver-to nudge (if no address set) — inline, dismissible.
  2. Hero: campaign slot (CMS-managed, max 3 slides, no autoplay faster than 7 s, pause control required).
  3. **"Arriving fastest to you"** rail — products with the earliest promise for the buyer's location. This rail is the model's signature: nearby sellers beat distant warehouses.
  4. Category tiles (top 12, CMS-ordered).
  5. **"Only here"** rail — categories FC-based competitors cannot carry: bulky, fragile, made-to-order, hazardous, ultra-premium.
  6. Recently viewed / recommended (personalised; hidden for anonymous cold users).
  7. New sellers near you (exploration quota surfaced to buyers, FR-O-02).
  8. Trust strip: escrow, buyer protection, verified sellers, fiscal receipt — each linking to the corresponding policy page.
  9. Editorial/campaign collections.
  10. SEO text block (CMS, collapsible on mobile).
- **Data:** CMS layout document + personalised rails from `recommend`, promises from `promise` (batch quote for the visible rail).
- **States:** anonymous cold (no personalisation, no promise rail if no location → show location prompt instead); logged-in; error (rail fails → rail is omitted, page still renders).
- **Mobile:** rails are horizontal scrollers with snap; hero one slide.
- **SEO:** ISR, 5-min revalidate; Organization + WebSite/SearchAction structured data.
- **Acceptance:** LCP ≤ 2.5 s on Moto G-class / 4G; no layout shift from rails (reserved heights); no rail renders more than one ad slot.

### 5.2 Category listing (PLP) — `/c/{slug}`

- **Purpose:** browse and narrow a category.
- **Blocks:** breadcrumb; H1 + item count; subcategory chips; **filter panel**; sort control; **result grid**; pagination; SEO text; related categories.
- **Filters (facets):** price range (histogram), **delivery speed ("arrives by")**, fulfillment mode, seller trust tier, seller location/region, COD available, rating, brand, plus category-specific attributes from the PIM schema. Applied filters shown as removable chips with "clear all".
- **Sort:** Recommended (default, = offer-selection score), Price ↑/↓, Fastest delivery, Rating, Newest. **Sponsored is never a sort option.**
- **Card contents:** image (lazy, AVIF/WebP, fixed aspect box), title (2 lines max), price + optional honest strike-through, **promise badge**, mode icon, seller name + trust chip, rating + review count, wishlist toggle, "N offers from X" when multi-seller.
- **Ad slots:** positions 3 and 8 maximum on the first page, then at most one per 10 cards; each labelled; **the grid component asserts the density cap and drops overflow ads rather than rendering them** (Part B §10 covers the test).
- **States:** loading (skeleton cards, no spinner), empty ("no results" + relaxed-filter suggestions + popular in category), error (retry, keep filters), no-location (promise badges show "set address for exact date").
- **Interactions:** filters apply without a full reload (URL updated, history entry per filter set); infinite scroll on mobile with a "load more" fallback and a real paginated URL for crawlers.
- **Mobile:** filters in a bottom sheet with a sticky "Show N results" button; sort as a chip row.
- **SEO:** SSR/ISR; canonical without volatile params; only whitelisted facet combinations indexable (Part B §5); `BreadcrumbList` + `ItemList` structured data.
- **Acceptance:** filter round-trip p95 ≤ 400 ms; TTFB p95 ≤ 400 ms; ad-density assertion covered by an automated test; grid usable with keyboard only.

### 5.3 Search — `/s?q=`

- Same grid and facets as PLP, plus:
  - **Suggest overlay:** recent queries, popular queries, category shortcuts, product suggestions with thumbnails, brand and seller matches; debounce 150 ms; keyboard navigable; results within 200 ms p95.
  - **Query understanding feedback:** "Showing results for *X*. Search instead for *Y*" when a correction is applied.
  - **Zero-results page:** spelling suggestion, broadened query, popular in the detected category, and a "notify me" capture.
  - Cross-script input: Cyrillic Uzbek input finds Latin Uzbek content and vice versa.
- **Acceptance:** null-result rate tracked as a guardrail metric; suggest works with the keyboard alone; `q` is never rendered unescaped (XSS).

### 5.4 Product page (PDP) — `/p/{slug}-{id}`

The highest-value page on the site. Block order (mobile), desktop is a two-column derivative:

1. **Gallery** — zoom, video support, thumbnails, swipe; first image is the LCP element and must be preloaded.
2. **Title, brand, rating anchor** (jumps to reviews), product code.
3. **Chosen-offer panel** — the commercial core:
   - price, optional honest strike-through, instalment hint;
   - **promise block**: date, mode, shipping cost, and *"Why this date?"* disclosure;
   - **seller row**: legal name (verified), trust chip, rating, distance/region, response time, link to storefront;
   - authenticity signals: brand-authorised badge (earned, never purchasable), marking-code presence, warranty;
   - return policy summary with a link to full terms;
   - stock/capacity hint only when genuinely scarce ("2 left at this seller") — never fabricated;
   - primary CTA **Add to cart**, secondary **Buy now**, tertiary wishlist/share;
   - payment methods incl. **COD availability for this offer and address**.
4. **"Why this offer was chosen"** — one sentence + link to the full offer list (FR-O-01).
5. **Other offers preview** — top 3 alternatives (cheapest, fastest, highest-rated) with a link to `/offers`.
6. **Delivery and pickup panel** — per mode: courier date and cost, PUDO/locker options on a map, store pickup address and hours.
7. **Description and attributes** — structured attribute table first, prose second.
8. **Marking / compliance block** for regulated categories.
9. **Reviews** — verified-purchase only, rating distribution, photo/video reviews, filters (with photos, by rating, by variant), seller replies, helpfulness voting, report abuse. Explicit note: *"Only buyers who received this item can review it."*
10. **Q&A** — questions to the seller with the seller's median response time shown.
11. **Similar / complementary products**.
12. Sticky mobile bar (price + promise + Add to cart) appearing after the chosen-offer panel scrolls out.
- **States:** in stock / out of stock at chosen offer (auto-switch to next best offer with an explanation) / no offers (page still indexable, shows "notify me") / no address set (promise shows city-level estimate + prompt).
- **SEO:** SSR; `Product`, `Offer` (with `priceValidUntil`, `availability`, `shippingDetails`, `hasMerchantReturnPolicy`), `AggregateRating`, `Review`, `BreadcrumbList`.
- **Acceptance:** LCP ≤ 2.5 s; promise block never renders a date without a source explanation; the seller's verified legal identity is always visible without interaction (traceability, NFR-C-04); zero CLS from gallery or sticky bar.

### 5.5 All offers — `/p/{slug}-{id}/offers`

Sortable, comparable table/list of every seller offer: price, shipping cost, **total to pay**, promise date, mode, trust tier, seller location, return policy strength, COD support, "select" CTA. Default sort = offer-selection score, with the published weights linked. Filter by mode, tier, COD, arrival date. **Acceptance:** total-to-pay is computed for the buyer's address before any selection is made — no surprise shipping at checkout.

### 5.6 Seller storefront — `/seller/{slug}`

Header with legal name, verified badge, trust tier and score link, location(s), working hours, response time, cumulative metrics (on-time rate, orders delivered, member since), policies; then their catalogue with the standard grid and facets; then reviews. **Acceptance:** all mandatory trader-identity fields rendered server-side; on-time rate shown is the same number that feeds the trust score.

### 5.7 Cart — `/cart`

- **Grouping by seller-shipment** is the defining feature: each group shows seller, mode, promise date, shipping cost, free-shipping progress (seller-funded, labelled as such), and per-item controls.
- Order summary: items total, shipping per shipment, discounts (with funding source labelled), **total to pay** — identical to the checkout total.
- Warnings surfaced in cart, not at checkout: item became unavailable, price changed, promise changed, seller paused, COD unavailable for a group, address needed for exact dates.
- Saved-for-later, wishlist move, quantity limits per offer capacity.
- Anonymous carts persist by cookie for 30 days and merge on sign-in (no silent overwrite — conflicts are shown).
- **Acceptance:** the number of shipments and every promise date shown in cart equal those written into the order; cart total equals checkout total in 100% of E2E runs.

### 5.8 Checkout — `/checkout`

Single page, four collapsible steps, progress preserved on reload; guest checkout allowed with phone OTP.

1. **Contact** — phone (OTP-verified), name, e-mail (optional, for the receipt).
2. **Delivery** — address book or new address: region → district → mahalla/landmark → **map pin (authoritative)**; per shipment, the buyer picks the mode offered by that seller (courier / PUDO map / locker / store pickup / seller courier), with the date and price for each; delivery-window preference where the carrier supports it; comment to courier.
3. **Payment** — Uzcard/Humo, Visa/Mastercard, Payme, Click, Uzum wallet, platform wallet, **COD** (shown only where every shipment supports it, with the reason displayed when it is unavailable), instalment/BNPL (Phase 2). Card entry is a PSP-hosted iframe/redirect — no card data touches our DOM.
4. **Review and pay** — per-shipment summary with frozen promise dates, full cost breakdown, fiscal-receipt notice, links to the public offer and buyer-protection terms, explicit consent checkbox (not pre-ticked), and the single **Pay** CTA.
- **Rules:** no new costs may appear after step 1; no upsell that changes the total without an explicit action; no pre-selected paid add-ons; errors are field-level and never lose entered data; the pay button is idempotency-keyed and disabled during processing with a visible state.
- **Failure handling:** payment declined → same page, cart intact, alternative method suggested; PSP timeout → order held in `PAYMENT_PENDING` with a status-polling screen and an e-mail/SMS follow-up; offer becomes unavailable mid-checkout → explicit block with substitution options.
- **Acceptance:** completion of a multi-seller, mixed-mode, COD-eligible order in ≤ 90 s on mobile in usability testing; zero unlabeled cost lines; PCI scope confined to the PSP frame (Part B §9).

### 5.9 Order confirmation — `/checkout/success/{orderId}`

Order number; per-shipment cards with promise dates, modes and tracking placeholders; payment status; **fiscal receipt** links (per seller, as issued); what happens next timeline; "track order" CTA; add-to-calendar for promise dates; support entry point.

### 5.10 Buyer account

| Route | Contents |
|---|---|
| `/account` | Hub: active orders with live status, wallet balance, pending reviews, quick links |
| `/account/orders` | Filterable list (active / delivered / cancelled / disputed) |
| `/account/orders/{id}` | Per-shipment **tracking timeline** (normalised events, carrier-agnostic, with a map for the last mile where available), promise vs actual, proof-of-delivery photo, receipt links, actions: contact seller, cancel (where permitted), return, open dispute, rate |
| `/account/returns/new/{shipmentId}` | Return wizard: item selection → reason (taxonomy) → photo/video evidence → **return method** (in-store / PUDO drop-off / courier pickup / refund-without-return where eligible) → label/QR → confirmation |
| `/account/returns/{id}` | Status, evidence, inspection result, refund status and ETA |
| `/account/disputes/{id}` | Evidence timeline (packing photo, handover scan, POD, inspection), messages, SLA countdown, decision and **its stated reasoning** |
| `/account/wallet` | Balance, cashback, refunds in flight with ETA, transaction history |
| `/account/addresses` | Address book with map pins, default address |
| `/account/wishlist` | With price-drop and back-in-stock alert toggles |
| `/account/reviews` | Write/edit reviews for delivered items only |
| `/account/settings` | Profile, language, notification channels (push/SMS/e-mail/Telegram, granular), privacy consents, **data export**, account deletion |

**Acceptance:** every state a buyer can be in has a next action; refund ETA is always shown as a date, never as "soon"; the dispute page shows the decision reasoning, not just the outcome.

### 5.11 Public tracking — `/track/{code}`

No login. Code-gated (order number + phone last 4, or a signed link). Shows the shipment timeline and promise only — no PII beyond a masked recipient name and city.

### 5.12 Policy centre — `/policies/*`

Not marketing pages; **product surfaces with data**:

- `/policies/fees` — current fee schedule by category, rendered from `fee-engine` configuration (never hand-written), plus a **changelog** with effective dates, diffs, and the notice date proving the 60-day rule (G3).
- `/policies/ranking` — the ranking and offer-selection factors with current weights, and a statement that ad spend is not an organic input (G5).
- `/policies/trust-score` — the STS formula, component weights, thresholds and tier benefits (G5).
- `/policies/advertising` — labelling rules and the density cap (G8).
- `/policies/transparency` — quarterly numbers: counterfeit takedowns and median takedown time, disputes and outcomes, return-insurance-pool inflow/outflow/balance, ranking-policy changes.
- `/policies/buyer-protection`, `/policies/returns`, `/policies/offer` — legal texts in uz/ru/en with all historical versions archived and addressable.

**Acceptance:** fee and ranking pages are generated from live configuration; a fee-rule change publishes here automatically on its notice date; every legal document is available in all three languages (NFR-C-03).

### 5.13 Error, empty and offline pages

`/404` with search and category suggestions; `/500` with an incident/status link; `/offline` served by the service worker with cached recently-viewed products; a maintenance page with a per-service degradation notice ("checkout is available; reviews are temporarily read-only").

---

## 6. Seller acquisition site — `/sell`

- **Landing:** the value proposition is the comparison table from Part 1 §2.4 — *no storage fees, no size limits, ship from your own shop, keep 8–20 p.p. more of every order*. Sections: how it works (4 steps), fulfillment modes explained, fee transparency with a link to `/policies/fees`, trust-score and payout-speed explanation, seller testimonials, coverage map, FAQ, sticky "Start selling" CTA.
- **`/sell/calculator`** — the honesty weapon: the seller enters category, price, weight/dimensions, destination and mode; the page calls `GET /v1/finance/fee-quote` and returns **exact expected net proceeds**, itemised by fee line with the rule version, plus a side-by-side "what an FBO marketplace would charge" comparison using published competitor tariffs (clearly sourced and dated). No sign-up wall.
- **`/sell/register`** — wizard: phone OTP → legal type (individual/YaTT/LLC) → tax ID + registry lookup → documents upload → **e-signature (ERI)** for legal entities → bank details → first pickup location (map pin, calendar, cutoff, capacity, delivery zones) → fiscal registration → contract acceptance (versioned) → first listing prompt. Progress saved between sessions; every step states why the data is needed and how long verification takes.
- **Acceptance:** registration→first live listing median ≤ 60 min (NFR-U-03); the calculator's output matches the ledger's actual fee lines for an equivalent real order to the tiyin.

---

## 7. Seller cabinet (web) — page specifications

| Page | Must contain | Acceptance |
|---|---|---|
| **Dashboard** | Today's orders by state, orders needing acceptance (with the acceptance clock), promise-at-risk shipments, payout countdown, trust score delta with reasons, stock-confirmation prompt | Every alert is actionable in ≤ 2 clicks |
| **Products / offers** | Table with search, bulk edit, status filters, stock and capacity inline edit, moderation status with the exact rejection rule and an appeal button, offer health (promise competitiveness, stock freshness) | Rejection always names the rule and offers appeal (FR-S-08) |
| **Listing creation** | Three paths: attach by barcode/GTIN, category attribute form, photo-first AI-assisted draft; live preview of the buyer-facing card | Draft autosave; validation is inline, never on submit only |
| **Import** | XLSX/CSV template download, upload, per-row validation report, job progress, rollback | Errors are downloadable as an annotated file |
| **Orders / shipments** | Kanban or queue by state; pack screen with **scan fields** (barcode + datamatrix) and **parcel photo upload**; label print (PDF + ZPL); pickup booking and rescheduling; exceptions | Pack cannot be completed without required scans and photo (FR-S-18/19) |
| **Returns** | Queue, inspection screen with PUDO evidence side-by-side with the seller's original packing photo, accept/dispute, restock/write-off | Both evidence sets shown on one screen (FR-L-26) |
| **Finance** | Ledger with every line traceable to an order and a **fee rule version**; payouts with countdown and schedule reason; COD reconciliation; holds/reserves with reason, amount, release date and appeal button | No hold may render without all four fields (G6) |
| **Trust Score Card** | Every component, weight, current value, target, trend, the events that moved it, and the concrete actions to improve; appeal flow with SLA countdown | Score is fully explained; no hidden components (FR-S-35) |
| **Ads** | Campaign creation, budget caps, auction explanation, ad-attributed vs organic reporting | Organic and ad-attributed sales always reported separately |
| **Analytics** | Sales, funnel, promise performance (DOP), cancellations, return reasons, search terms, price/promise competitiveness | Exportable to CSV |
| **Settings → locations** | Map pin, working calendar, cutoff, handling time, daily capacity, delivery zone polygons, return address | Capacity changes recompute promises within 60 s |
| **Settings → API** | Keys, scopes, webhook endpoints with delivery logs and replay, sandbox toggle, **full data export incl. signed reputation certificate** | Export downloadable without contacting support (FR-S-37) |
| **Settings → staff** | Sub-accounts, roles (packer/courier/manager/accountant), activity log | Least-privilege by default |

---

## 8. Back office and partner portal (block-level)

- **Back office** (`admin.`): moderation queues with SLA timers; dispute arbitration workbench with the assembled evidence timeline; finance operations with four-eyes approval; carrier lanes, tariffs and scorecards; **fee/policy change workflow** with the notice-period gate physically enforced in the UI; CMS for home layout and campaigns with a mandatory funding-source field on every promotion; feature flags; immutable audit log with read-only auditor view.
- **Partner portal** (`partner.`): scan-in / scan-out, status update, exception reporting, COD remittance declaration, PUDO inspection capture flow — designed for a low-end Android browser and a barcode scanner or camera.

---

## 9. Component library (design system)

**Foundations:** design tokens (colour, type scale, spacing 4 px base, radii, elevation, motion), light and dark themes, three type stacks covering Latin and Cyrillic, iconography set (incl. the four fulfillment-mode icons).

**Components to build (each with: default / hover / focus-visible / active / disabled / loading / error / empty states, RTL-safe layout, and a11y contract):**

`Button`, `IconButton`, `Input`, `PhoneInput`, `OtpInput`, `Select`, `Combobox`, `Checkbox`, `Radio`, `Switch`, `Slider/RangeSlider`, `DatePicker`, `Tabs`, `Accordion`, `Modal`, `Drawer`, `BottomSheet`, `Popover`, `Tooltip`, `Toast`, `Banner/Alert`, `Breadcrumbs`, `Pagination`, `Skeleton`, `Spinner`, `EmptyState`, `ErrorState`, `Rating`, `ReviewCard`, `ProductCard`, `OfferRow`, `PriceBlock`, `PromiseBadge`, `TrustChip`, `ModeIcon`, `SellerCard`, `AdLabel`, `FilterChip`, `FacetPanel`, `SortControl`, `Gallery`, `MapPicker`, `PudoMap`, `AddressForm`, `CartGroup`, `CheckoutStep`, `TrackingTimeline`, `EvidenceViewer`, `LedgerTable`, `ScoreCard`, `DataTable`, `FileUpload`, `ScanField`, `LanguageSwitcher`, `CookieConsent`.

**Rules:**
- No component may render a price without a currency and locale-aware format.
- `ProductCard` and `OfferRow` **cannot** be rendered without a `PromiseBadge` or an explicit "set your address" fallback — enforced by the component's own prop types.
- `AdLabel` is non-optional on any sponsored placement; the grid drops ads beyond the density cap rather than rendering them unlabelled.
- Storybook entry with interaction and a11y tests for every component (Part B §11).

---

## 10. Responsive, motion and content rules

| Breakpoint | Width | Layout |
|---|---|---|
| `xs` | 360–479 | 2-column grid, bottom sheets, sticky CTA |
| `sm` | 480–767 | 2–3 columns |
| `md` | 768–1023 | 3–4 columns, filters as a collapsible rail |
| `lg` | 1024–1439 | 4–5 columns, persistent filter sidebar |
| `xl` | ≥ 1440 | Max content width 1440 px, 5–6 columns |

- Motion: 150–250 ms, ease-out; every animation respects `prefers-reduced-motion`; no motion on price, promise or total.
- Images: fixed aspect ratios, `width`/`height` always set, AVIF/WebP with fallback, responsive `srcset`, LCP image preloaded, everything else lazy.
- Copy: sentence case; dates as "Thu, 10 Sep"; money always with currency; no marketing superlatives on functional elements; error messages state what happened, why, and the next action.

---

## 11. Content management

- **CMS-managed:** home layout and rails order, hero campaigns, category tiles, collections/landing pages, help articles, legal documents (versioned, multi-locale), footer links, SEO text blocks, banners.
- **Never CMS-managed:** prices, promises, fees, trust scores, ranking weights, ad density — these render from services so that the published policy and the running system cannot diverge.
- Headless CMS via API with preview mode, scheduled publishing, per-locale workflow, and a required funding-source field on any promotional block (governance G2).

---

*Continues in [Website TZ, Part B — Frontend Engineering, SEO, Analytics and Acceptance](./06-website-engineering-and-acceptance.md).*
