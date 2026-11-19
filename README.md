# FirmaBlick website prototype

A static, responsive first cut based on the approved Stitch export. The institutional masthead, editorial hero, imagery, scenario panel, research cards and contact section draw from the export. Mock statistics, author credits and service claims were replaced with prototype copy.

## Run locally

Use Node.js 20 or later. No npm dependencies are required.

```sh
npm test
npm run build
python3 -m http.server 4173 --directory dist
```

Open http://localhost:4173. The Vercel configuration builds and serves the same `dist/` directory. A PR preview requires the GitHub repository to be connected to a Vercel project.

## What’s available

- **Home** presents FirmaBlick’s European industrial focus and links to the demo and catalogue.
- **Intelligence** updates an illustrative production index through 2030 as the scenario, productivity gain, start year and energy deviation change. The optional comparison uses its selected scenario’s unadjusted assumptions. The chart has a matching accessible table.
- **Research** filters example reports by topic and expands their preview details.
- **Methodology** explains source classifications, traceability and calibration principles.
- **Contact** previews form validation and confirmation in the browser. The fields are for sample details and submission sends and stores nothing.

The five destinations are sections of one page with shareable fragment links. The simulator uses a synthetic starting index and simple growth assumptions. Report cards are examples and have no downloadable dossiers. The FB monogram is the prototype brand mark. Privacy, Terms, Imprint and Disclaimer copy is pending legal review.

The Stitch export references remotely hosted images and fonts. The site uses those URLs and includes image descriptions and fallback fonts. The tracked Stitch archive remains the source for the extracted design reference.

## Verification

The static build and JavaScript syntax checks passed. A Node smoke check with a stub DOM exercised scenario controls, catalogue filtering and the form handler. Real-browser layout, keyboard and validation checks, remote image and font loading, and the Vercel preview are unverified in the restricted build environment.

## CI and engineering acceptance

Issue #6 adds GitHub Actions CI for pull requests that change website code or tests, and a manual workflow dispatch option. CI uses Node.js 22 and performs `npm ci --ignore-scripts`, `npm run build`, and `npm test`, followed by checking deployment artifacts.

Regression tests use the Node built-in test runner and a deterministic DOM fixture. They cover interactive scenario assumptions, index response to energy assumptions, comparison visibility, research filtering, preview contact behavior, and the generated `dist/` entry point. Run in this order: `npm ci`, `npm run build`, `npm test`.

These tests prove basic interface behavior, not real-browser mobile rendering or statistical correctness. Production deployment, DNS and GitHub merge remain manual.

CI registration is tracked on the repository default branch; this feature branch carries the same regression suite for review and reproducibility.
