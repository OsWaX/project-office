# Technical Task — Website, Part B: Frontend Engineering, SEO, Analytics and Acceptance

**Companion to:** [Website TZ, Part A — Structure, Pages and UX](./05-website-technical-task.md)
**Version:** 1.0 · **Date:** 2026-09-04 · **Status:** For review and approval

---

## 1. Technology stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | **Next.js (App Router) + React + TypeScript (strict)** | SSR/ISR for the SEO-critical storefront, streaming, route-level rendering control |
| Styling | CSS Modules or Tailwind + design tokens (decision: ADR-W-001) | Token-driven theming; no runtime CSS-in-JS on the critical path |
| State | Server components by default; TanStack Query for client data; Zustand for cart/UI state | Minimal client JS |
| Forms | React Hook Form + Zod schemas shared with the BFF | One validation contract, client and server |
| i18n | next-intl / ICU MessageFormat, per-locale message bundles | Pluralisation and gender-safe strings for uz/ru/en |
| Maps | Yandex Maps or 2GIS (ADR-W-002) | Local address quality is the deciding factor |
| Search UI | Custom, backed by `search` service | No third-party search widget on the critical path |
| Seller cabinet | React + TypeScript SPA (Vite), no SSR | Behind auth, SEO irrelevant, richer interactivity |
| Back office | Same SPA stack, separate bundle and deploy | Isolation of privilege |
| Testing | Vitest, Testing Library, Playwright, Storybook + test-runner, axe-core, Lighthouse CI | See §11 |
| Delivery | Docker on Kubernetes, CDN in front, GitOps, preview deploy per PR | Matches Part 3 infrastructure |

**Hard constraints:** no jQuery; no runtime-loaded UI framework from a third-party CDN; every third-party script is consent-gated, `async`, and budget-accounted (§4.3).

---

## 2. Rendering strategy per route

| Route | Rendering | Cache |
|---|---|---|
| `/` | ISR, 5 min | CDN, stale-while-revalidate; personalised rails hydrate client-side |
| `/c/{slug}`, `/s` | SSR with edge cache keyed by (path, whitelisted facets, locale, **delivery zone**) | 60 s CDN, SWR 300 s |
| `/p/{slug}-{id}` | SSR + ISR (revalidate on price/stock/promise events via on-demand revalidation) | 120 s CDN, zone-keyed promise fragment |
| `/p/.../offers`, `/seller/*`, `/brand/*`, `/collections/*` | SSR/ISR | 120 s |
| `/policies/*`, `/help/*` | SSG with on-demand revalidation when configuration or CMS changes | Long |
| `/cart`, `/checkout`, `/account/*`, `/track/*` | SSR, `Cache-Control: no-store`, auth-gated | None |
| `seller.*`, `admin.*`, `partner.*` | CSR SPA behind auth | App shell cached, data never |

**Zone-keyed caching is the central performance trick:** the promise depends on the buyer's delivery zone, so pages are cached per zone (roughly 30–60 zones nationally) rather than per user. A cold user without a zone gets a city-level promise and a prompt.

---

## 3. Front-end architecture

```
apps/
  storefront/        Next.js buyer site
  seller/            Seller cabinet SPA
  admin/             Back office SPA
  partner/           Carrier/PUDO portal
packages/
  ui/                Design system components + tokens + Storybook
  api-client/        Generated typed clients from OpenAPI (no hand-written fetch)
  i18n/              Message bundles, formatters, transliteration helpers
  analytics/         Event taxonomy, typed emitters, consent gate
  config/            ESLint, TS, build presets
services/
  bff/               Backend-for-frontend (see §3.2)
```

### 3.1 Rules

- **Typed API clients are generated** from the services' OpenAPI/AsyncAPI specs in CI; a contract change that breaks the front-end fails the pipeline.
- **No business rules in the front-end.** Prices, fees, promises, eligibility, ad density and trust scores are computed server-side and rendered. The front-end may never recompute a total.
- Feature flags come from the flag service, are readable in SSR, and every flag has an owner and an expiry date.
- Errors: typed error envelope from the BFF (`code`, `message_i18n_key`, `retryable`, `trace_id`); the UI always shows an action and the trace ID in support surfaces.
- Every mutating request carries an idempotency key; the checkout `pay` action is idempotent end-to-end.

### 3.2 Backend-for-frontend (BFF)

A thin BFF exists to keep the browser fast and the domain services clean:

- **Composition:** one PDP request fans out to `pim`, `offer`, `promise`, `review`, `trust-score`, `ads` and returns a single view model.
- **Batch promise quoting:** one call per result page, not one per card (NFR-P-03).
- **PII minimisation:** the browser never receives fields it does not render; addresses and phones are masked in list responses.
- **Session and token handling:** HttpOnly, `Secure`, `SameSite=Lax` cookies; access tokens never reach `localStorage`.
- **Resilience:** per-dependency timeouts and circuit breakers; a failed non-critical dependency (ads, recommendations, reviews) degrades its block, never the page.
- **Rate limiting and bot mitigation** at the BFF edge (§9).

---

## 4. Performance budgets

### 4.1 Field targets (Core Web Vitals, p75, mobile, real users)

| Metric | Target | Page scope |
|---|---|---|
| LCP | ≤ 2.5 s | Home, PLP, PDP |
| INP | ≤ 200 ms | All interactive pages |
| CLS | ≤ 0.05 | All |
| TTFB | ≤ 0.6 s | SSR routes |

### 4.2 Lab budgets (enforced in CI, fail the build)

| Budget | Limit |
|---|---|
| JS transferred, first load (storefront route) | ≤ 170 KB gzipped |
| CSS transferred, first load | ≤ 60 KB gzipped |
| Total first-view transfer (PDP) | ≤ 900 KB |
| Requests, first view | ≤ 45 |
| Third-party JS total | ≤ 60 KB gzipped and ≤ 3 origins |
| Lighthouse Performance (mobile, throttled) | ≥ 85 Home/PLP/PDP, ≥ 80 checkout |
| Lighthouse Accessibility / Best Practices / SEO | ≥ 95 / ≥ 95 / ≥ 95 |

### 4.3 Techniques (requirements, not suggestions)

- Route-level code splitting; no shared vendor mega-bundle; dynamic import for map, gallery zoom, charts, editor.
- Images: AVIF → WebP → JPEG fallback, responsive `srcset`, explicit dimensions, LCP image `fetchpriority="high"` and preloaded, everything else `loading="lazy"` + `decoding="async"`.
- Fonts: self-hosted, subset per script, `font-display: swap`, preloaded for the primary weight only; no more than 3 weights total.
- Skeletons instead of spinners for content areas; reserved space for every async block (CLS = 0 by construction).
- Service worker: offline shell, cached recently-viewed products, background sync for wishlist and review drafts. **Never** cache prices, promises or totals.
- Third parties: consent-gated, lazy, and each one has a named owner and a documented business justification; a third party that breaches the budget is removed, not optimised.
- Prefetch on intent (hover/viewport) for PLP → PDP; never speculative-prefetch checkout.

---

## 5. SEO

### 5.1 Indexation policy

| Surface | Policy |
|---|---|
| Home, categories, product pages, brand, seller storefronts, collections, help, policies | Indexable |
| Search results `/s?q=` | `noindex, follow` |
| Facet combinations | Indexable **only** for a curated whitelist (single-attribute facets with demand, e.g. brand, one key attribute, price band); all others `noindex, follow` with a canonical to the clean category |
| Sort, pagination params, session params | Canonical to page 1 of the clean URL; `rel=prev/next` not relied upon, real crawlable links to paginated pages |
| Cart, checkout, account, tracking, seller/admin/partner subdomains | `noindex, nofollow` + robots disallow |
| Out-of-stock product pages | Remain indexable with `availability: OutOfStock` and offers from other sellers surfaced |

### 5.2 Requirements

- **URLs:** lowercase, transliterated Latin slugs, no locale in the path for the default locale; `/{locale}/…` for `ru` and `en`.
- **hreflang:** reciprocal `uz` / `ru` / `en` + `x-default` on every indexable page.
- **Titles/meta:** templated per page type with per-page CMS override; product titles include brand, model and key attribute; no duplicate titles across paginated pages.
- **Structured data (JSON-LD):** `Organization`, `WebSite` + `SearchAction` (home); `BreadcrumbList` (all); `ItemList` (PLP); `Product` + `Offer`/`AggregateOffer` incl. `shippingDetails` and `hasMerchantReturnPolicy`, `AggregateRating`, `Review` (PDP); `FAQPage` (help); `LocalBusiness` for seller storefronts with a physical pickup point. All validated in CI.
- **Sitemaps:** index + per-type sitemaps (categories, products, sellers, brands, collections, content), regenerated on a schedule with `lastmod`, split at 50k URLs; excluded URLs never appear.
- **Crawl budget:** parameter handling declared, faceted traps blocked in `robots.txt`, soft-404s eliminated (a zero-result page returns 200 with `noindex`, an unknown product returns a real 404).
- **Content:** every category and collection has unique, human-written intro/outro copy in all three locales; no doorway pages; no scraped or auto-spun text.
- **Performance is an SEO requirement:** the CWV targets in §4.1 are part of the SEO acceptance criteria.

---

## 6. Internationalisation and localisation

- Locales: `uz` (Latin, default), `ru`, `en`. All strings externalised; **zero hard-coded user-visible text** — enforced by a lint rule.
- ICU MessageFormat for plurals and cases; Russian requires 3 plural forms, Uzbek 2 — the message API must not assume English rules.
- Locale-aware formatting for dates ("Pay, 10-sen" / "Чт, 10 сен" / "Thu, 10 Sep"), numbers and currency (UZS, no decimals, thousands separator per locale).
- **Cross-script search:** Uzbek Cyrillic input is transliterated to Latin (and vice versa) client-side for suggest and server-side for search.
- Legal documents are stored per locale with independent version history; a missing translation blocks publication of that document version (NFR-C-03).
- Locale switching preserves the current route and query state; the choice persists in a cookie and in the account profile.
- Content that cannot be machine-translated (legal, fee schedule, policy pages) is flagged in the CMS as translation-required.

---

## 7. Accessibility (WCAG 2.1 AA)

- Semantic landmarks; one `h1` per page; logical heading order.
- Full keyboard operability: search suggest, facet panel, bottom sheets, modals (focus trap + restore), gallery, map picker (with a non-map address entry fallback — the map is never the only way to give an address).
- Visible `:focus-visible` on every interactive element; skip-to-content link.
- Contrast ≥ 4.5:1 for text and ≥ 3:1 for UI boundaries in both themes; ad labels are held to the same standard.
- Form fields have persistent labels (never placeholder-only), programmatic error association, and `aria-live` announcements for async validation and cart/price updates.
- Images: meaningful `alt` (product name + variant), decorative images `alt=""`.
- `prefers-reduced-motion` honoured everywhere; no content conveyed by colour alone (fulfillment modes carry an icon **and** a text label).
- Screen-reader smoke tests on the five critical flows each release (NVDA + VoiceOver iOS).

---

## 8. Analytics and event taxonomy

Events are typed in `packages/analytics`, validated against a schema registry, and emitted server-side where accuracy matters (orders, payments) and client-side for interaction.

| Event | Key properties |
|---|---|
| `page_view` | route, page_type, locale, delivery_zone, is_logged_in, ab_variants |
| `search_performed` | query, corrected_query, results_count, has_zero_results, latency_ms |
| `suggest_used` | query_prefix, suggestion_type, position |
| `filter_applied` / `sort_changed` | facet, value, results_count |
| `product_card_impression` | product_id, offer_id, position, is_sponsored, promise_date, page_type |
| `product_view` | product_id, chosen_offer_id, seller_id, promise_date, p_on_time, offers_count |
| `promise_explained_opened` | product_id, offer_id — *measures trust in the promise* |
| `offer_switched` | from_offer_id, to_offer_id, reason (price / speed / trust) |
| `add_to_cart` / `remove_from_cart` | offer_id, qty, price, promise_date |
| `checkout_started` | shipments_count, modes[], total, payment_methods_available |
| `checkout_step_completed` | step, duration_ms |
| `delivery_option_selected` | shipment_index, mode, cost, promise_date |
| `payment_method_selected` | method, is_cod |
| `order_placed` (server) | order_id, gmv, shipments, modes[], payment_method, promise_dates[] |
| `payment_failed` | reason_code, method, retry_count |
| `promise_at_risk_shown` | shipment_id, option_chosen |
| `return_started` / `return_completed` | shipment_id, reason_code, return_method |
| `dispute_opened` | order_id, type |
| `review_submitted` | product_id, rating, has_media |
| `seller_calculator_used` | category, price, mode, net_proceeds |
| `seller_registration_step` | step, duration_ms, drop_off |
| `ad_impression` / `ad_click` | campaign_id, position, page_type |

**Requirements:**
- **Consent-gated:** analytics beyond strictly necessary measurement fires only after consent; the consent state is part of every event.
- **No PII in event payloads** — IDs only; phone, address and name never leave the BFF.
- Server-side truth for commerce events; client events are for behaviour, never for revenue reporting.
- **Guardrail dashboards required at launch:** ad share of page-1 clicks, organic vs sponsored click share, promise-explained open rate, zero-result rate, checkout drop-off by step, and CWV by page type — all wired into the experimentation platform's auto-stop rules (FR-D-04).

---

## 9. Security and privacy (web-specific)

| ID | Requirement |
|---|---|
| SEC-W-01 | Strict CSP with nonces, no `unsafe-inline`/`unsafe-eval`; report-only phase before enforcement; violations monitored |
| SEC-W-02 | Security headers: HSTS (preload), `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (geolocation and camera only where used), `COOP`/`CORP` |
| SEC-W-03 | Auth: phone OTP with rate limiting and lockout, HttpOnly/Secure/SameSite cookies, rotating refresh tokens, device list and remote sign-out, re-authentication for payout/bank-detail changes in the seller cabinet |
| SEC-W-04 | **No card data in our DOM** — PSP-hosted iframe or redirect; PCI-DSS SAQ-A scope only (NFR-S-02) |
| SEC-W-05 | Output encoding everywhere; `dangerouslySetInnerHTML` only for CMS content passed through a sanitiser allowlist |
| SEC-W-06 | CSRF: SameSite cookies + per-session token on state-changing non-GET requests |
| SEC-W-07 | File uploads (review photos, evidence, KYB documents): type and size validation, image re-encoding to strip metadata, malware scan, served from a separate origin with `Content-Disposition` |
| SEC-W-08 | Anti-scraping and bot mitigation: rate limits per IP/session/API key, adaptive challenges on search and PDP, no price data in an unauthenticated bulk endpoint |
| SEC-W-09 | PII masking in all list views and in the public tracking page; full data visible only to the owner and to authorised staff, with access logged |
| SEC-W-10 | Consent management with granular categories, no pre-ticked non-essential boxes, one-click decline, and a durable consent log |
| SEC-W-11 | Self-service data export and account deletion in `/account/settings` (NFR-C-06) |
| SEC-W-12 | Subresource integrity and a pinned allowlist for the ≤ 3 permitted third-party origins; dependency scanning and lockfile enforcement in CI |

---

## 10. Governance controls enforced in the front-end

Part 1 §9 commitments that the website is responsible for proving:

| Commitment | Web enforcement | Test |
|---|---|---|
| G2 — no forced discounts | Any promotional badge requires a `funding_source` field from the API; missing → the badge does not render | Component test with a null funding source |
| G3 — 60-day fee notice | `/policies/fees` renders live `fee-engine` config plus the changelog with notice and effective dates | Snapshot test against a seeded rule change |
| G5 — transparent ranking and scoring | `/policies/ranking` and `/policies/trust-score` render live weights; PDP shows "why this offer" | E2E asserting the explanation exists on every PDP |
| G8 — ad density cap | `ResultGrid` drops sponsored items beyond 2-in-first-10 and 20%-of-page | Unit + E2E over 50 seeded result pages |
| G9 — data portability | Export available self-service in both buyer and seller settings | E2E download assertion |
| No dark patterns | No pre-ticked consent, no fake countdowns, strike-through price requires a verified prior-price flag from the API | Lint rule (no `defaultChecked` on consent inputs) + E2E |

---

## 11. Testing and quality

| Layer | Scope | Gate |
|---|---|---|
| Unit (Vitest) | Formatters, hooks, view-model mappers, validation schemas | ≥ 80% on `packages/ui` and mappers |
| Component (Testing Library + Storybook test-runner) | Every component's states + a11y via axe | Zero serious/critical axe violations |
| Contract | Generated clients vs service OpenAPI specs | Breaking change fails CI |
| Visual regression | Storybook snapshots, both themes, 3 breakpoints | Diff review required |
| E2E (Playwright, 3 browsers × mobile/desktop) | The 12 critical journeys from Part 4 §5, plus the web-specific journeys below | 100% pass required to deploy |
| Performance | Lighthouse CI on Home/PLP/PDP/Checkout + bundle-size budgets | Budgets in §4.2 fail the build |
| SEO | Structured-data validation, hreflang reciprocity, sitemap integrity, meta uniqueness | Fails the build |
| Load | 10× average traffic against SSR routes and the BFF | Before each peak season |
| Manual | Screen-reader smoke, real low-end Android device, throttled 3G, cross-browser matrix | Each release |

**Web-specific E2E journeys (in addition to Part 4 §5):**

1. Anonymous → set delivery address → promise dates update across home, PLP and PDP consistently.
2. Multi-seller cart with three fulfillment modes → checkout → totals identical to cart → order confirmation shows three shipments with the frozen promise dates.
3. COD-ineligible item added to a COD cart → clear explanation → resolution path offered.
4. Offer becomes unavailable during checkout → substitution flow → order completes.
5. Payment declined → retry with another method → success, no duplicate order (idempotency).
6. Guest checkout → account upgrade → historical order visible.
7. Locale switch mid-session preserves route, cart and filters.
8. Return wizard on a delivered shipment → PUDO drop-off selected → label/QR issued.
9. Seller registration wizard completed on desktop → first listing published within the session.
10. Seller pack screen blocks completion without barcode/datamatrix scan and parcel photo.
11. Ad density cap holds across 50 seeded search/category pages.
12. Offline mode: previously viewed PDP renders from the service-worker cache with prices explicitly marked stale.

---

## 12. Delivery plan (website workstream)

Aligned to the phases in [Part 4](./04-roadmap-and-acceptance.md).

| Sprint (2 wks) | Deliverable |
|---|---|
| W1–W2 | Repo, monorepo tooling, CI/CD, preview deploys, design tokens, first 15 components, BFF skeleton, i18n scaffolding |
| W3–W4 | Header/footer/global layout, delivery-zone selector, home (static), category tree navigation, error pages |
| W5–W6 | PLP + facets + result grid with ad-density enforcement; search + suggest |
| W7–W8 | PDP incl. chosen-offer panel, promise block, offers list, seller card; structured data |
| W9–W10 | Cart with per-seller shipment grouping; address book + map picker |
| W11–W12 | Checkout (all 4 steps), payment integrations, COD rules, confirmation page, fiscal receipt surfacing |
| W13–W14 | Buyer account: orders, tracking timeline, wallet, addresses, reviews |
| W15–W16 | Returns wizard, dispute page, public tracking page |
| W17–W18 | Seller acquisition site, fee calculator, seller registration wizard |
| W19–W22 | Seller cabinet v1 (dashboard, products, orders/pack, returns, finance, trust card, settings) |
| W23–W24 | Policy centre generated from live config; a11y and performance hardening; SEO pass; pilot launch readiness |
| Phase 2 | Ads UI, reviews/Q&A at scale, bulk import, analytics pages, API/webhooks settings, partner portal, back-office UI, PWA/offline |

**Team (website workstream):** 1 PM, 1 UX + 1 UI designer, 4–5 front-end engineers (2 storefront, 2 cabinet/admin, 1 design system), 1 BFF engineer, 1 SDET, 0.5 SEO specialist, 0.5 content/localisation manager.
**Indicative effort to pilot launch (W24):** ≈ 75–90 front-end man-months.

---

## 13. Definition of done (per page)

A page is done only when **all** of the following hold:

1. All specified blocks implemented, with loading / empty / error / offline / no-address states.
2. Responsive at all five breakpoints; verified on a real low-end Android device.
3. Accessibility: keyboard-complete, axe-clean, screen-reader smoke passed, contrast verified in both themes.
4. All three locales complete — no missing keys, no hard-coded strings, correct plural forms.
5. Performance budgets met in Lighthouse CI; no CLS from any async block.
6. SEO block complete where applicable: title/meta, canonical, hreflang, structured data validated, sitemap inclusion correct.
7. Analytics events emitted per §8 and verified in the debug view.
8. Security review points applied: CSP-clean (no inline violations), no PII over-fetch, output encoded.
9. Tests: component tests for new components, E2E for any journey the page participates in, visual snapshots approved.
10. Content reviewed by the localisation manager; legal texts approved by counsel where applicable.
11. Governance controls (§10) that apply to the page are covered by an automated test.

---

## 14. Website acceptance criteria (launch gate)

| # | Criterion | Threshold |
|---|---|---|
| A1 | Core Web Vitals, field data, p75 mobile | LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.05 on home, PLP, PDP |
| A2 | Lighthouse (mobile, throttled) | Perf ≥ 85, A11y ≥ 95, Best Practices ≥ 95, SEO ≥ 95 |
| A3 | All 12 platform journeys + 12 web journeys | 100% pass on the full browser matrix |
| A4 | Accessibility | Zero serious/critical axe issues; WCAG 2.1 AA audit report signed off |
| A5 | Localisation | 100% key coverage in uz/ru/en; all legal documents published in all three |
| A6 | SEO technical audit | No critical or high findings; structured data valid on 100% of sampled PDPs |
| A7 | Cart↔checkout total parity | 100% of E2E runs |
| A8 | Ad-density cap | Never exceeded across 50 seeded result pages |
| A9 | Security | Penetration test with no open Critical/High; CSP enforced without violations for 7 days |
| A10 | Checkout completion (usability testing, mobile, multi-seller order) | ≥ 90% task success, median ≤ 90 s |
| A11 | Seller registration → first live listing | Median ≤ 60 min in supervised sessions |
| A12 | Governance controls G2, G3, G5, G8, G9 | Each proven by a passing automated test |
| A13 | Analytics | All events in §8 firing with correct schemas; guardrail dashboards live |
| A14 | Load | SSR routes and BFF sustain 10× average traffic within budget latency |

---

## 15. Open questions for the business owner

1. **Map provider** — Yandex Maps or 2GIS? This affects address quality, PUDO map UX and licensing cost (ADR-W-002).
2. **Uzbek Cyrillic** — search input support only (assumed), or a full fourth UI locale?
3. **PWA scope** — install prompt and push notifications on the web, or keep push exclusive to the native apps?
4. **Guest checkout** — allowed at launch (assumed, it raises conversion) or account-required for fraud control?
5. **Competitor comparison in the fee calculator** — publish the side-by-side against FBO marketplace tariffs (strong differentiator, some legal exposure) or show only our own numbers?
6. **Seller cabinet on mobile web** — full responsive parity, or the reduced "accept order + print label" subset assumed here, with the Android app as the primary tool?
7. **Domain and locale strategy** — default locale on the bare path with `/ru` and `/en` subpaths (assumed), or locale subdomains?
8. **Reviews with media** — moderated before publication (slower, safer) or published immediately with post-moderation?
9. **Back office** — build in this workstream, or buy/adapt an admin framework and spend the saved capacity on the storefront?

---

## 16. Summary

The website is where the model's structural advantage becomes visible or invisible. Three things decide it:

- **The promise on every card**, honest and explained — the substitute for a warehouse the buyer can trust.
- **The named, verified seller** on every listing — the substitute for a single brand standing behind the goods.
- **The published policy pages generated from live configuration** — the substitute for "trust us", and the thing no incumbent in the benchmark currently offers.

Everything else in this document exists to make those three fast, accessible and honest on a mid-range Android phone.
