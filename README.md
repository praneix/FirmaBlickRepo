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

## V1 official data contract (Issue #7)

The preliminary five-industry source registry, versioned observation schema, and validation policy are in [docs/source-registry.md](docs/source-registry.md), [data-contracts/source-registry.v1.json](data-contracts/source-registry.v1.json) and [data-contracts/industrial-observation.v1.schema.json](data-contracts/industrial-observation.v1.schema.json).

The current displayed simulator remains **illustrative**. No Destatis/Eurostat production ingestion or live forecast is yet connected. The source contract includes no actual statistical observations, access credentials or private customer information.

`npm run build && npm test` runs the source-contract regression suite alongside the existing website tests. Domain-specific source validation is implemented in `scripts/validate-observation.mjs`. A complete Draft 2020-12 JSON Schema validation engine and live provider integration will be added in the ingestion phase.


## Official-data ingestion prototype (Issue #8)
A read-only, standard-library Destatis GENESIS client now exists in [ingestion/genesis.py](ingestion/genesis.py). It uses authenticated **POST** requests to fetch tables 42153-0001 and 42153-0002, inspect ZIP-wrapped flat-file CSV and source classifications, and record SHA-256-checked local raw source snapshots. It does **not** publish official observations or connect live data to the public website.

Read [the ingestion integration guide](docs/genesis-ingestion.md) for commands, token requirements, tests and live API limitations. CI executes Python official-format synthetic-fixture regression tests and asserts that no-token execution fails with an actionable error. Actual API connectivity requires a personal GENESIS token and is deliberately opt-in.


## Immutable GENESIS acquisition snapshots (Issue #9)
Raw official-source downloads are now archived in a local append-only, SHA-256 content-addressed store with SQLite relational retrieval history. Duplicate source bytes retain distinct retrieval events, while revised bytes retain older vintages. API consumers can query acquisition history as of an exact UTC instant and verify every referenced source object. Storage or integrity failure blocks acquisition completion. Source data remains unpublished and illustrative website forecasts are unchanged. See [storage architecture and acceptance tests](docs/snapshot-store.md). A dedicated FirmaBlick hosted storage environment must be separately configured before production use.


## Forecast benchmark evaluation (Issue #13)
The local, standard-library [rolling-origin benchmark harness](forecast/benchmarks.py) implements last-value, seasonal-naive and drift forecast comparisons. The [predeclared evaluation and holdout protocol](forecast/evaluation-protocol.v1.json) fixes required source provenance, multiple forecast horizons, accuracy metrics, interim quality gates and a protected final holdout. See [benchmark methodology](docs/forecast-evaluation.md). All current benchmark tests are synthetic; **no real-time backtest superiority or public forecast release has been certified**. Authenticated, verified historical acquisition vintages are a prerequisite.
