# CV1-03 official-source commercial reuse preflight — 2026-11-20

## Scope and status
**Review:** primary-authority general licensing pages inspected on 2026-11-20. The precise five original production-index series and Eurostat comparison dataset must still be checked against any dataset-specific notices and the eventual deployed web / paid-report use. This is a recorded technical reuse preflight, **not legal signoff or publication authorisation**.

### Destatis / GENESIS
- Authority: https://www.destatis.de/EN/Service/OpenData/api-webservice.html
- General programme: https://www.destatis.de/EN/Service/OpenData/opendata-einleitung.html
- Destatis states GENESIS-Online data can be used without charge under **Data Licence Germany – Attribution 2.0**; cite the publisher, GENESIS dataset/table, retrieval period and any modifications.
- Required proposed attribution on the historical UI: `© Statistisches Bundesamt (Destatis), GENESIS-Online 42153-0001 / 42153-0002 · Data Licence Germany – Attribution 2.0 · retrieved [exact UTC]`.
- Source-reported per-cell revision/finality flags are absent from these acquired GENESIS FFCsv objects: show the absence, never label all values final or unrevised. Versioned source vintage and original-unadjusted adjustment status must stay visible.

### Eurostat
- Authority: https://ec.europa.eu/eurostat/help/copyright-notice
- Eurostat permits commercial and non-commercial reuse of its own data and metadata with source acknowledgement, subject to exceptions for third-party material, some non-EU-country data, and some specific trade sets. This comparator concerns Germany original industrial production index, `sts_inpr_m`, with no directly identified exception in the general policy.
- For customised dataset use, Eurostat recommends citing the dataset code link and access date: https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table .
- Explain that any transformations or modifications are FirmaBlick's responsibility; official sources do not endorse the visualisations.
- The current source is an exact numeric comparison in the November 2026 vintage. It does not certify that 2015–2025 released values were identical to those available then.

### Proposed UI copy and release condition
- Show Destatis source, licence, retrieval vintage, adjustment and original base year; cite Eurostat `sts_inpr_m` as independent exact comparator.
- Distinguish observation from illustrative scenario and independently unapproved forecast. Show latest observed 2026-09 and warn when data-vintage age exceeds 120 days.
- Any commercial production launch requires (a) final dataset-level rights check, (b) approved operator legal notices and privacy disclosure, (c) trusted source-release data/provenance manifests, (d) exact Vercel protected preview verification, and (e) owner publication approval for exact SHA. All are currently blocked.

## Risks and exclusions
- Fonts, stock imagery and corporate marks have different licensing concerns from statistical datasets. Rights to republish outside source statistics must be reviewed separately in #47.
- The public GitHub repository must retain no unpublished source ZIPs or source-backed generated 705-observation JSON until explicitly approved.
- The 2026 vintage's absence of per-cell source revision flags limits conclusions. Do not treat commercial reuse eligibility as evidence of numeric forecast validity or data quality.

## Sources consulted
- https://www.destatis.de/EN/Service/OpenData/api-webservice.html
- https://www.destatis.de/EN/Service/OpenData/opendata-einleitung.html
- https://ec.europa.eu/eurostat/help/copyright-notice
