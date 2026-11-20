# Issue #11: Eurostat STS production comparator and reconciliation

## Preflight
GitHub repository write access and prior prototype branch pipeline verified. PR #22 for Issue #10 merged. The connected Supabase account contains IIA only; no FirmaBlick project or live storage exists. This issue uses separate local Eurostat archive and modifies no other product's database. No tokens or purchases needed for public Eurostat API. Public site and original Destatis source remain unchanged.

## Primary statistical contracts
- Eurostat official statistics API JSON-stat v2: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started/api
- Dataset sts_inpr_m, geo DE, freq M, industrial production indicator PRD, NACE C/C20/C24/C28/C29, s_adj NSA/CA/SA/SCA and explicitly identified index base.
- Official dataset: https://ec.europa.eu/eurostat/databrowser/product/view/sts_inpr_m
- NACE Rev. 2 remains in short-term business statistics through 2027, NACE Rev.2.1 is required from 2028: https://ec.europa.eu/eurostat/web/short-term-business-statistics/legislation
- Official guide for JSON-stat categories, dimensions, sparse values and source status: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started/api

## Read-only ingestion and snapshots
Run python3 -m ingestion.eurostat fetch --since 2021-01 --output artifacts/eurostat to request the official public REST endpoint; it stores the exact response bytes and their SHA-256 in a private local path artifacts/eurostat/firmablick/v1/eurostat/objects, with separate append-only SQLite events recording UTC acquisition time and safe request/response metadata. Repeated identical responses reuse bytes but record a distinct acquisition event. Revised bytes remain available using EurostatArchive.events(as_of=...). Source-reported dataset updated timestamp is distinct from acquisition timestamp. Source data is never marked published. A standalone history command uses python3 -m ingestion.eurostat history --output artifacts/eurostat. No other application's database or secrets are touched.

The parser discovers JSON-stat dimensions, size/order/category indices, sparse value and status positions, preserves original source dimensions and flags, rejects unknown dimensions and nonnumeric cells, and will not infer a missing value to be zero. It does not interpret status flags as provisional without confirmation. A request to treat NACE_REV2_1 as REV2 is rejected.

## Reconciliation
Use ingestion.eurostat.reconcile(destatis_observations,eurostat_observations), which returns a report only. It never updates primary Destatis data. It accepts only matched country DE, monthly series, explicit WZ2008-versus-NACE_REV2 two-digit category correspondence, equal adjustment, index-unit/base and period, and nonmissing source observations. Exclusions include source and period coverage gaps, classification, unit/base/adjustment/geography mismatches and missing values. Numeric differences are reported in absolute index points with an explicit tolerance; a deviation is not automatically a source error because vintages, methodologies and revisions can differ.

## Limits and live acceptance
CI fixtures are synthetic JSON-stat 2.0 examples with recognized source dimension names. The adapter fetches real public Eurostat content only when the user invokes its command in an environment with internet access. Live five-industry coverage, index-base availability and exact mapping of official dataset dimensions remain external integration checks. Until reconciled against authenticated official Destatis snapshots and an independently validated Eurostat release, no claims of full statistical correspondence or usable public forecasts are authorized.

NACE Rev. 2.1 transition from January 2028 requires separate documented mapping/backcasting and source series identification. Current version rejects mixing Rev2 and Rev2.1 and never silently rebases index years. Hosted data archival, backups and secured service operation require a dedicated FirmaBlick project approved separately.

## Automated validation
Run: python3 -m unittest discover -s tests -p 'test_*.py' -v ; npm ci && npm run build && npm test. Tests exercise dimensions, sparse values, flags, HTTP fetch, raw snapshot revisions, retention, checksums, strict comparisons and mismatches.

Related GitHub Issues: #5 #7 #8 #9 #10 #11
