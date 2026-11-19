# FirmaBlick V1 | Source registry and observation contract
## Boundary
Germany manufacturing aggregate plus WZ2008 division 20 chemicals, 24 basic metals, 28 machinery and equipment, 29 motor vehicles. Output is **industrial production volume index**, not euros of sector revenue, physical steel usage or demand in tonnes.

## Source selection
Primary **Destatis GENESIS** table 42153-0001 supplies manufacturing aggregate C (verify source's precise aggregate dimension). Table 42153-0002 supplies divisions 20, 24, 28, 29. Source metadata identifies the exact original/working-day-adjusted/seasonally-adjusted series; never choose based on a guessed dimension key.
- https://genesis.destatis.de/datenbank/online/table/42153-0001
- https://genesis.destatis.de/datenbank/online/statistic/42153
- https://www.destatis.de/EN/Service/OpenData/api-webservice.html
- https://genesis.destatis.de/datenbank/online/docs/GENESIS-Webservices_Introduction.pdf

Independent comparator Eurostat **sts_inpr_m** (geo=DE, monthly industrial production). First inspect the dimensions (indicator, unit, s_adj, NACE classification and period). Mapping WZ 2008 to NACE Rev.2 for two-digit divisions is **candidate mapping to validate against dimension descriptions**, not permission to mix classification revisions:
- https://ec.europa.eu/eurostat/databrowser/product/view/sts_inpr_m
- https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction

## Source metadata and lineage
Every observation carries original source dataset/key/dimensions, geography, month, index unit/base year, adjustment, classification version, industry code, source-status flags, observation type, immutable raw snapshot id and SHA-256 digest, acquisition timestamp, and transformation version.
Source released **provisional** status is indicated *only by upstream flags*. Status "estimated", "nowcast", "forecast", "derived", "customer_adjusted" must be assigned by processing/publishing stage and never confused with official source observations. Store provenance for all calculated data and historical backtests.
Published series currently commonly use **2021=100**, but verify dynamically; reject a rebasing mismatch. Missing numeric values remain null and require a missing reason; suppression, break in series, not available, and not applicable may carry distinct source codes.

## Quality and publication rules
- Require canonical sector ↔ source table ↔ classification compatibility; unknown or contradictory values fail.
- Preserve exact decimal values of the selected official source vintage. Do not impute, rescale, smooth or zero-fill in the official historical layer.
- Store raw bytes separately and immutably, retaining all acquisition vintages including revised official data; retrieval time is distinct from official release date.
- Compare Eurostat only for matched geography, adjustment, unit, index base, classification, series definition and month; disparities are explained, not automatically fixed.
- The NACE Rev.2.1 short-term business statistics transition starting in **2028** is a known schema risk. Review backcasting and explicit conversion maps.
- Never apply source-derived authorization, licensing or trademarks assumptions without verifying current provider terms.

## Authentication / legal
Destatis GENESIS web services may require credentials or a user token depending on endpoint and access mode; discover and test first, store keys in provider secret management only. Eurostat dissemination API is publicly accessible subject to published usage rules. Check provider terms of reuse, citation/attribution and cache limits prior to redistribution. These statements are planning constraints, not legal clearance.

## Fixture provenance
Fixtures in `tests/fixtures/` are **synthetic**, created to test schema and validation; they MUST NOT be published as German industrial observations. No live API data is included in this issue. Issue #8 will perform actual endpoint discovery and ingest representative real raw snapshots.

## Integration
`data-contracts/source-registry.v1.json` defines the five target views; `data-contracts/industrial-observation.v1.schema.json` defines the interchange contract. `scripts/validate-observation.mjs` enforces essential schema and source mapping constraints without external dependencies; its logic is covered by `tests/source-contract.test.mjs`. Future implementation should run a full Draft 2020-12 JSON Schema validator in addition to these domain assertions.