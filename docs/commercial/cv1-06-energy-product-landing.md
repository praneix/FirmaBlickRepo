# CV1-06 · Energy flagship catalogue and product landing

Date: 2026-11-22 · Issue [#44](https://github.com/praneix/FirmaBlickRepo/issues/44)
Status: **engineering candidate; public distribution, paid checkout, advisory intake and sample PDF release not yet authorized**.

## Buyer journey implemented
- Homepage `#research` now has one evidence-backed energy research listing, and homepage hero points to it.
- Production-like deep link: `/research/germany-industrial-energy-decision-report-2026/` with public canonical URL reserved for `firmablick.com`.
- Dedicated navy/ivory/controlled terracotta editorial landing page: German market decision problem; industrial CFO/plant/energy procurement audience; four source-backed executive insights; illustrative BESS NPV sensitivity bars; five report chapter summaries; 2025 SMARD and H1-2026 Eurostat links; sample/full edition description; clear publication/checkout/legal status.
- Vector abstract chart is explicitly labelled `ILLUSTRATIVE LINEWORK · NO MARKET VALUES PLOTTED`. The numerical exhibit represents the deterministic V4 battery economic model, not actual plant results or a deployable recommendation.
- Distinct CTA to read **on-page executive preview**. The five-page PDF sample and full report are held in private owner review, unapproved. No PDF links, signed URLs, published price, live checkout or purchased entitlement exists in the public site.
- “See advisory enquiry status” points to the existing homepage demo form and directly states that it cannot send messages. Actual qualified lead intake belongs to issue #46.
- Automotive and Supply Chain hypothetical report cards removed. The old topic-filter JavaScript was removed rather than leaving unused controls.
- Semantic HTML, landmark navigation, responsive CSS, keyboard-accessible anchors, descriptive meta, fixed dimensions on hero abstract SVG, protected review `noindex,nofollow` and source attribution.
- The page remains unlisted by search engines while review-only. SEO indexing, merchant price and product structured data must be enabled only after approved facts, company operator disclosures and transaction terms are in place.

## Reused verified claims; no new proprietary data
- 2025 DE–LU day-ahead price mean approximately €89.32/MWh from previous source assurance (PR #62).
- Eurostat `nrg_pc_205` H1 2026 DE/FR/ES IC–IG exact-currency/tax-band comparison and preliminary German source statuses.
- Illustrative ten-year BESS NPV +€69,938 base, −€147,600 (−20% benefits) and −€256,369 (−30% benefits) from deterministic model.
- Published SMARD negative hour count 573 versus independent reconstructed negative hourly means 576 remains **unreconciled and disclosed**.
- The official historic industrial production site view remains unpublished and the scenario tool synthetic.
- Marketing text does not represent editorial or legal approval as complete.

## Explicit commercial feature gate
| Capability | V1 implementation state | Follow-on |
|---|---|---|
| Single genuine research card & deep-link landing | Implemented locally | #44 |
| On-page executive insight and illustrative exhibit | Implemented | Final claim assurance #42 |
| Five-page sample PDF download | Disabled; private owner review only | #42 / #43 |
| Live price, tax, licence, refund text | Not released | #39 / #47 |
| Buy/report checkout | Disabled button and accurate status | #45 |
| Functional diagnostic enquiry | Demo-only linked with disclosure | #46 |
| Secure full PDF after verified purchase | Backend isolated CI only | #43 / #45 |
| Search indexing and full merchant metadata | Intentionally suppressed | #47 / #48 |
| Final live protected Vercel preview | Pending | #48 / #54 |

## Acceptance checks
- `npm run build && npm test` verifies existing website and new catalogue assertions.
- Browser script `tests/report-landing-browser.mjs` runs on a local built preview via the existing Chromium CI. Tests real link navigation from homepage, exact one report card, 4 insights, 5 sections, approved-source links, disabled buy control, no public unapproved price, no PDF/download URLs, no unexpected page errors, responsive chart and horizontal overflow at desktop, 390px and 320px widths.
- Existing `tests/historical-browser.mjs`, `tests/scenario-browser.mjs`, `tests/beta-browser.mjs` must stay green.
- Source and product contract acceptance for full paid release remains **open**. A successful browser check does not imply a working payment flow or authorised public distribution.

## Deployment restrictions
This PR targets only `agent/fb-v1-integration-20261120` and never merges into `main`. Vercel preview protection must not be lowered. The V4 paid PDF, sample PDF, personal data, customer tokens and service-role credentials remain outside static site assets. No DNS, payments or live enquiries were enabled.

## Remaining launch gaps
Complete owner-approved final source/rights editorial edition (#42), dedicated private storage and live entitlement verification (#43), true enquiry backend (#46), payment activation and post-payment fulfillment (#45), regulatory disclosures (#47), protected Vercel live QA and exact SHA production approval (#48/#54). Only then replace the disabled controls with actual working links.
