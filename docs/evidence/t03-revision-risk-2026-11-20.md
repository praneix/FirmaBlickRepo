# T03 | Official source-status and revision-risk research (2026-11-20)

Status: documentary research; **not** an individual observation's official release-status attestation or numerical parity certificate.

## Official producer evidence
1. Destatis production index quality report: https://www.destatis.de/EN/Methods/Quality/QualityReports/Industry-Manufacturing/production-index-industry.pdf?__blob=publicationFile&v=5 . The report states that original series' annual revision is typically published in June of the following year at the latest and then becomes final; rebasing triggers retrospective changes. General source policy does not automatically identify the specific quality status of a row without accompanying status data.
2. Official general revisions policy: https://www.destatis.de/EN/Methods/Quality/PrinciplesGoverningRevisions_of_Published.pdf?__blob=publicationFile . Routine monthly revisions occur, with changes to seasonal adjustments as additional new periods enter estimation.
3. Destatis September 2026 press release: https://www.destatis.de/EN/Press/2026/11/PE26_389_421.html . It documents a technical correction affecting Division 30 and aggregates involving it, retrospectively from January 2021. Because manufacturing C can include that division, any 2026 acquisition must be treated as a revised **vintage**; previous months' numeric values must not be represented as if known at earlier forecast origins.
4. Official interactive 42153-0001 table: https://genesis.destatis.de/datenbank/online/table/42153-0001 . It labels the original and X13-JDemetra+ adjustment columns and shows `p` and `r` for certain displayed values. Search indexing may show alternative query/custom-view scopes; extract primary displayed series keys and a date-stamped official snapshot before declaring individual numeric parity.
5. Official Eurostat industry dataset: https://ec.europa.eu/eurostat/databrowser/product/view/sts_inpr_m . The monthly comparator has independently discoverable `indic_bt=PRD`, `unit=I21`, `nace_r2`, `s_adj`, `geo=DE` dimensions, to be validated from live JSON-stat metadata.

## Interpretation rules
- `WERTORG`: original, `X13JDKB`: calendar-adjusted X13, `X13JDKSB`: calendar + seasonal adjusted X13. The `BV4TB` method requires exact title/status verification from the original source metadata before any corresponding output.
- The underlying FFCsv observed in November 2026 contains no dedicated `quality` column; absence must be preserved as `source_quality_field_not_provided` and must never be converted to `final`, `provisional` or `revised` without separate source evidence.
- Separate `publication_rule`, `current_snapshot_status`, `observed_vintage_revision`. Do not infer past-as-of values by applying current-vintage revisions backwards.
- For the rolling-origin evaluation, the single November 2026 snapshot can support a **retrospective revised-series forecast diagnostic**; it cannot prove real-time forecaster performance over 2015–2026. Missing historical vintages require explicit downgrading of retrospective claims. The 2026 technical correction makes this especially material.

## Outstanding evidence
- Independently checked precise table-42153 official values and their exact adjustments/industry selectors against normalized row values (all five).
- Revision/status code legend and durable source snapshots for future comparison.
- True as-of vintages earlier than 2026, or a formally approved evaluation labelled retrospective diagnostic.
- Authentic Eurostat comparator response and numerical differences.

Release decision: **BLOCKED** until the individual observation quality/revision and golden parity steps are independently resolved.
