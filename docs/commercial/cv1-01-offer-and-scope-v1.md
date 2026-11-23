# FirmaBlick Commercial V1 — Offer and Scope Contract (PROPOSED)
**Issue:** #39 · **Version:** 1.0.0 · **Date:** 2026-11-20 · **Status:** Pending owner commercial approval
**Machine-readable contract:** `product/contracts/commercial-v1-offer.v1.json`

## Owner's provisional commercial direction — 23 November 2026

The owner explicitly selected the following **provisional** preferences. These guide only nonproduction engineering and market validation; they do **not** constitute final business approval:

| Dimension | Preferred working assumption | Release approval |
|---|---|---|
| Commercial release architecture | **A: Research-first V1**; maintain independent forecast validation workstream | Not yet granted |
| Energy standalone research price | **€149 excluding applicable taxes**; no observed price elasticity or willingness-to-pay evidence yet | Not yet granted |
| Primary target decision-maker | **CFO / Finance Director** | Buyer priority selected for design; market validation pending |

**Consequent design priorities:** Executive summary first; transparent delivered-electricity-cost bridge; gross margin/EBITDA and cash sensitivity; capital-allocation cases and downside; benchmark definition and evidence provenance; decision and 90-day action summary. Secondary audiences remain plant operations and energy procurement. Marketing text may be sharpened for CFOs but must avoid implying expert buy-in or verified willingness to pay.

**Commercial evaluation:** A €149 report requires approximately 67 paid purchases to reach €10,000 in *gross invoice value before fees, refunds, taxes and costs*, assuming all purchases are at full list price. Conversion, CAC, repeat purchasing and downstream advisory revenue remain empirical hypotheses; validate separately. Choosing A improves time-to-market by deferring unvalidated model predictions without changing the standing forecast quality gate or abolishing the original forecasting roadmap.

**Reserved authority:** `commercial_scope_approval=false`, `pricing_approved=false`, `publication_approved=false`, `legal_approved=false`, `checkout_enabled=false`, `production_authorized=false`, `forecast_approved=false`. Payments, legal terms and GO_LIVE decisions stay AWAITING. The PRICE and SCOPE decisions have state `PROVISIONAL_AWAITING_FINAL_APPROVAL`. No unapproved €149 amount may appear as a live offer, invoice or checkout total.

## Executive decision
**Recommended commercial release:** Scope A, research-first. An evidence-led German industrial-intelligence website provides source-backed manufacturing history and transparent illustrative scenarios. A single genuine paid Energy publication opens the first transaction; a free qualified diagnostic enquiry opens the higher-value advisory conversation. This should launch only after owner approval and documented legal/data/payment gates.

**Scope B remains preserved:** Existing epic #5 originally mandates a validated manufacturing forecast. Independent November 2026 benchmark diagnostics failed its publication criteria, including 12-month horizon performance. Delivering A before forecasts constitutes a **business scope change requiring owner approval**. The implementation does not silently delete #5 or represent a synthetic output as predictive research.

## The customer and the decision
**Initial geographic market:** Germany-led DACH industrial buyers; English first, German localisation later if GTM testing supports it. **Customer groups are hypotheses**, pending interview/outreach evidence:
1. CFO / financial controller of an industrial enterprise needs cost competitiveness, investment screening and financial sensitivities with documented assumptions.
2. Plant/operations leader needs a site-specific information checklist, exposure decomposition and prioritised actions.
3. Energy procurement/strategy manager needs apples-to-apples tariff comparisons, intraday flexibility framing and procurement questions.

**Commercial proposition:** `Germany's Industrial Energy Equation: Prices, Exposure and Strategic Options` (working title). Buyer gets source-defined SMARD/Eurostat findings, a correctly labelled illustrative battery financial case, industry archetypes, options and a 90-day management agenda. This is general research; site-tailored advice requires a separate qualified engagement.

## The first saleable SKU
- **SKU:** `FB-ENERGY-DE-2026-01`
- **Free asset:** 4–6 page executive sample, accessible without collecting contact information. Cite sources on sampled exhibits.
- **Paid asset:** Premium, branded, versioned PDF and concise evidence/methodology appendix. Report revision, release date, original sources and source vintages visible in-file and checkout receipt.
- **Distribution:** Downloadable full file only after server-confirmed payment, via expiring signed link. Never bundle the paid asset into the public static build.
- **Target product quality:** Engaging executive thesis; logical integrated chapter narrative; publication-grade SVG exhibits; financial model verified independently; caveats contextual and proportionate. No internal QA status pages, synthetic client anecdotes or unmatched references in paid report.
- **Rights:** Single company/internal evaluation usage is a licensing *proposal* pending legal terms.

## Pricing and payment: proposals, not authorisations
- **Owner's provisional price preference:** **€149** per full report, excluding applicable taxes. This remains a positioning hypothesis, **not** an empirically benchmarked market price and not approved for public sale.
- **Diagnostic:** Free, qualified discovery request, followed by an individually scoped paid advisory quote only when the buyer consents; no fixed diagnostic fee in V1 checkout.
- **Payment:** Investigate existing eligible India-merchant Razorpay international checkout for digital-goods access and provider-specific activation. Skydo is a potential invoice/B2B cross-border collection fallback. Validate eligibility, settlement, payments, tax invoices, export-of-services classification, refund procedures and chargebacks; do not bind provider or enable charging now.
- **Market validation:** Obtain measurable outreach and landing-page conversion evidence for price fit rather than extrapolating from unrelated high-ticket research reports. No revenue guarantee.

## Website information architecture
| Route / section | Role | Commercial action |
|---|---|---|
| `/` | FirmaBlick proposition and latest Energy thesis | Explore Energy intelligence |
| `/intelligence` | Five verified historical index series; clearly labelled synthetic scenario demo | See evidence / report sample |
| `/research` | Actual approved reports catalogue; upcoming reports hidden or labelled planned | Energy flagship product |
| `/research/germany-industrial-energy-decision-report-2026` | Source-backed offer, buyer problems, deliverables, contents, date, licence and price | Read executive sample / buy |
| `/research/germany-industrial-energy-decision-report-2026/sample` | Free excerpt (no lead-capture barrier) | Buy full report |
| `/checkout/FB-ENERGY-DE-2026-01` | Hosted payment adapter, disabled until commercial/legal gates | Secure payment |
| `/orders/receipt` | Order record, receipt, expiring signed-link delivery | Access paid report |
| `/contact/energy-diagnostic` | Work-email + role + decision objective, consent/legal notices | Submit advisory enquiry |
| `/methodology`, `/legal/*` | Source vintages, rights, terms, privacy, provider identity | Trust and compliance |

Existing single-page hash navigation may be incrementally migrated to route-like URLs without full framework replacement; preserve existing mobile/keyboard UX.

## Publication boundaries
- **Official index:** Destatis GENESIS C, C20, C24, C28, C29; Eurostat sts_inpr_m comparator. The 705 matching observations have independent retrieval/parity evidence, but are **not yet authorised for public display**. Use only after #41 publication and licensing gates.
- **Illustrative simulator:** 2026=100 synthetic starting point, user sliders and deterministic command parser. Always display as illustrative. It is separate from real 2021=100 industrial index and unapproved forecast.
- **Forecast:** Genuine forecast and calibrated scenario effects are blocked pending #14/#49; historical-only or labelled illustrative UX where required. No unverified model claim.
- **Energy report:** SMARD intraday wholesale statistics and Eurostat delivered industrial tariff prices are not interchangeable; energy claim definitions, BESS assumptions, unresolved 573/576 count discrepancy and source dates have explicit reconciliation requirements. Report only after #42 signoff.
- **Research expansion:** Automotive, Supply Chain and 50-session webinar content remain out of initial sales release.

## Commercial V1 done (acceptance matrix)
| Gate | Test | Dependency |
|---|---|---|
| A1 | Owner approves A or B, offer, licence and public price | #39 |
| A2 | Historical 5-series source correctness, provenance and licensing passes release gate | #41 |
| A3 | Energy report and free sample pass sources, arithmetic, layout and rights QA | #42 |
| A4 | Versioned full report cannot be downloaded without genuine entitlement | #43 |
| A5 | Landing pages, sample, order, advisory CTA function on mobile and keyboard | #44 |
| A6 | Backend lead intake and notification succeed with antiabuse, consent and retention | #46 |
| A7 | Hosted payment, cancellation, idempotent webhook, invoice and delivery pass sandbox | #45 |
| A8 | Legal operator, privacy, data/asset licences and cross-border transaction position accepted | #47 |
| A9 | End-to-end protected preview, exact SHA, security and rollback signoffs | #48/#54 |
| A10 | First independently observed, genuine paid purchase plus correct delivery after authorised launch | postlaunch |

## Owner decision register
Five decisions remain RESERVED. They are listed as `open_owner_decisions` in the JSON. SCOPE and PRICE are marked `PROVISIONAL_AWAITING_FINAL_APPROVAL`; PAYMENTS, LEGAL and GO_LIVE remain `AWAITING`. The team can advance source, editorial, sample and compliance engineering while they remain pending, and must block commercial activation. No assumed approval from silence or the generic engineering standing mandate.

## Explicit non-goals
No subscriptions, user accounts, private uploads, generic LLM chat agent, simultaneous automotive/supply-chain production, uncalibrated predictive claims, staff-like service promises or irreversible production data changes. The research orchestration engine is a separately gated P1 engineering capability, and V1 report fulfillment can operate using one approved manually frozen Energy artifact.

## Sources and work basis
- Existing FirmaBlick issue #5 and commercial epic #38; integration branch `site/index.html`; evidence PR #33/#35.
- Razorpay international payments official documentation: https://d6xcmfyh68wv8.cloudfront.net/docs/payments/payments/international-payments/
- Skydo international business collection product: https://www.skydo.com/features/receive-international-payments-in-india
- SMARD/Bundesnetzagentur industrial electricity price topic: https://www.smard.de/page/en/topic-article/5892/216044/industrial-electricity-price-trends

Source references above support *feasibility candidates only*, not processor merchant approval, legal advice or observed market price. All customer/price assumptions are explicitly hypotheses.

## Implementation boundaries
Source of truth: `product/contracts/commercial-v1-offer.v1.json`. Release gate MUST fail if pricing_approved=false, commercial_scope_approval=false, legal_approved=false, publication_approved=false or production_authorized=false. Engineering may use this proposal for UI architecture and sandbox tests, but must never surface an unapproved amount as a live actionable checkout price.
