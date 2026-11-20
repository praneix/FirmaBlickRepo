# FirmaBlick V1 · German manufacturing historical intelligence (Issue #12)

## Implemented
Five industry selectors are available in the original Intelligence website: manufacturing aggregate (WZ2008 C), chemicals (20), basic metals (24), machinery (28), and automotive (29). A monthly production-index chart, accessible HTML table, 12/24/60/120/240-month selectors, missing-data status column and source provenance are rendered from a validated static release JSON. The pre-existing scenario simulator remains expressly illustrative and uses its own synthetic assumptions.

## Data truth and publication boundary
The committed `site/data/historical.json` is explicitly `status: unavailable` with an empty series list. This is the **correct production-safe state** because there is no authenticated Destatis GENESIS snapshot and Issues #10 and #11 retain official-source acceptance gates. No number from test fixtures is included in the committed release.

The browser's historical source-contract validator refuses to render numerical data unless all five source-certified industries are present with a matching WZ2008 classification, identical declared index base and adjustment, genuine source URLs, source hashes, acquisition IDs, verification flags, published status, well-formed ascending monthly periods, and explicit missing-value semantics. This provides a last-mile UI guard; it is **not independent proof of actual Destatis origin**. A malicious or incorrectly configured publisher could fabricate metadata. Full production release must therefore use an approved server-side export/attestation process based on verified source snapshots and official-value parity tests.

Once legitimately validated, a historical release must include for each industry:
- `industry_code`, `dataset_id`, `source: "Destatis GENESIS"`, `source_url`, `geo: DE`, `frequency: M`, `unit: index`, `classification: WZ2008`, `base_year` and `adjustment`
- `retrieved_at` in UTC; `raw_sha256` and `acquisition_id` referencing a stored Issue #9 source; `official_verification: true` and `publication_approved: true` granted by a separate approved release process
- chronological `observations` with `period` YYYY-MM, numeric `value` or null with `missing_reason`, and exact `source_status_flags`.

Top-level fields: `schema_version: 1.0.0`, `status: validated`, `generated_at` UTC, and exactly five `series`. Never directly substitute test fixtures into the committed public JSON. The service should serve a retained last validated release when newer source acquisition fails, with clearly displayed source acquisition time. A source vintage older than 120 days is marked stale; no automatic zero-fill, backfill or undocumented extrapolation.

## Accessibility and interaction
The history widget has keyboard-selectable industry and time-range controls, a polite status region, an SVG chart with descriptive alternative text, explicit empty state, and a semantic HTML table recording each monthly value/status. Missing months break the line into separate segments rather than joining across unknown values. The layout adapts to mobile and avoids horizontal overflow.

## Verification and limitations
- `npm run build && npm test` validates the release contract, source metadata and strict no-fabrication behavior.
- CI has a pinned Playwright Chromium container running `tests/historical-browser.mjs` at 1365×900 and 390×844. It verifies the *actual committed unavailable state* and, separately, an **intercepted synthetic payload only inside the isolated browser test**. No fictional data enters website assets.
- Offline Python GENESIS/Eurostat/statistical tests and missing-token safeguards remain mandatory.
- Actual official data display, numerical comparison against a known Destatis published series, and a fully attested release artifact require authenticated source evidence. Until those gates are complete this issue remains a UI engineering implementation, not a fully released historical-data feature.

No new cloud project, customer session or LLM API. Other ventures' databases are untouched. There is no production merge or DNS change.

Related: GitHub Issues #5, #7–12.
