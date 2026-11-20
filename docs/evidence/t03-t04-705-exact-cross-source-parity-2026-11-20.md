# T03/T04 | Exact independent source-value parity: Destatis vs Eurostat (2026-11-20)

## Evidence and provenance
- Authenticated official Destatis GENESIS tables `42153-0001` and `42153-0002`, raw ZIP from run [44702970458](https://github.com/praneix/FirmaBlickRepo/actions/runs/44702970458), artifact 14613832495. Original archive ZIP SHA256: `568b6d514643c85a777dc21e9cecf6aa36d2d8fe12bdf4a1e5ebef986a80d3de`. Every stored content-addressed source object passed hash validation.
- Independent official Eurostat `sts_inpr_m` raw JSON-stat 2.0 from run [44703565920](https://github.com/praneix/FirmaBlickRepo/actions/runs/44703565920), artifact 14612934209. Archive ZIP SHA256: `65906eb5bcd853bf1b6f85c60d16d7d9f60fed9eace673daa4c2b5846e30c694`. Inner JSON source SHA256: `7d2942a3769402645709cc9c06ad93686203661f7ee988d719858d1c352c9866`. Source dataset `updated=2026-11-19T11:00:00+0100`.
- Independent original source bases `2021=100`; Destatis value code `PRO101`, adjustment `WERTORG`, WZ08-**. Eurostat `freq=M`, `indic_bt=PRD` (production volume), `geo=DE`, `s_adj=NSA`, `unit=I21`, `nace_r2=C/C20/C24/C28/C29`.
- Crosswalk matching precise German WZ08-NACE Rev.2 sections/divisions: C→C, 20→C20, 24→C24, 28→C28, 29→C29. Source category mappings, comparison date and official classification correspondence must be retained; no Rev2.1 conversion or rebasing applied.
- Period `2015-01` through `2026-09` inclusive, 141 periods for each of five series. Eurostat source response contains exactly 705 numeric cells and no cell-level status entries in its `status` dimension.

## Independently computed exact numeric comparison

| Matched series | Compared months | Exact matches | Nonmatches | Missing | Maximum absolute delta |
|---|---:|---:|---:|---:|---:|
| Manufacturing C | 141 | 141 | 0 | 0 | 0.0 |
| Chemicals C20 | 141 | 141 | 0 | 0 | 0.0 |
| Basic metals C24 | 141 | 141 | 0 | 0 | 0.0 |
| Machinery C28 | 141 | 141 | 0 | 0 | 0.0 |
| Automotive C29 | 141 | 141 | 0 | 0 | 0.0 |
| **TOTAL** | **705** | **705** | **0** | **0** | **0.0** |

## Methodology

1. Independently read the original archived GENESIS ZIP tablefiles and select strictly coded WZ category, `WERTORG` original adjustment, and `JAHR+MONATxx` monthly period. Parse one-decimal index value, reject duplicate sector-period records.
2. Independently read Eurostat raw archived JSON-stat 2.0 and inspect its actual dimension list, sizes and category indexes, then map the dense `value` position using `nace_r2` ordinal × 141 time slots + month ordinal (other dimensions single-valued).
3. Build both keyed maps `(sector,YYYY-MM)`; compare every value, mark missing and compute max/mean absolute delta for all five industries. This report is produced from two independent official providers and their original bytes, **not** an internally duplicated fixture.
4. Keep archival hashes and source-reported Eurostat update timestamp to permit deterministic replay.

## Acceptance interpretation

**PASS:** Cross-source monthly observed original-index numeric parity for all 705 records in this specific 20 November 2026 snapshot. This independently supports the numerical source contract and is stronger than synthetic regression parity.

**OPEN:** Source-cell provisional/finality semantics, historical source vintage availability at each past forecast origin, a formally pinned production data/lineage JSON with published historical charts, independent chart acceptance, forecasting holdout/interval acceptance, legal/licensing review and protected Vercel browser QA. Exact cross-source values do **not** eliminate the documented November 2026 retrospective revision or imply past information availability.

**RELEASE STATE: BLOCKED.** These figures may be used as a verification input for a protected historical candidate, but cannot automatically enable forecasts/publication or alter the explicit owner launch approval.
