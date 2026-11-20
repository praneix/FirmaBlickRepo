# T02 | Extended GENESIS original-series acquisition accepted (2026-11-20)

Authenticated GitHub Actions run: https://github.com/praneix/FirmaBlickRepo/actions/runs/44702970458
Artifact ID: `14613832495` (`genesis-extended-original-unpublished-44702970458`, retention until 2026-12-20). Run conclusion: **success**.

## Independently recomputed archive integrity
- Outer artifact ZIP size: **596,015 bytes**.
- Outer SHA256: `568b6d514643c85a777dc21e9cecf6aa36d2d8fe12bdf4a1e5ebef986a80d3de` (matches GitHub artifact digest).
- Four content-addressed raw objects retained (two source metadata JSON and two original source tablefile ZIP). The SHA256 of each object equals its content-addressed path name.
- The aggregate table source FFCsv contains **31,020 source rows across all categories/adjustments**; division source FFCsv **16,356 source rows**. These are whole table rows, not just selected sectors.

## Real target-series coverage
Explicit filter: `WERTORG` original adjustment, WZ codes exact, `JAHR` year plus `MONATxx` month. No interpolation and no missing-period fabrication.

| Sector | First month | Last month | Observations |
|---|---|---|---:|
| C manufacturing aggregate | 2015-01 | 2026-09 | 141 |
| C20 chemicals | 2015-01 | 2026-09 | 141 |
| C24 basic metals | 2015-01 | 2026-09 | 141 |
| C28 machinery | 2015-01 | 2026-09 | 141 |
| C29 automotive | 2015-01 | 2026-09 | 141 |

The period count 141 equals 11 years and 9 months. No missing calendar month appears in the filtered period set. This is enough *chronological* coverage to attempt the protocol with at least 60 months training and 24 months final holdout, subject to authentic release-date constraints, point-in-time source availability, validation of individual observations and compatible methodology. It is **not** evidence of archived point-in-time vintages for each historical origin; do not claim genuine historical real-time evaluation.

## Acceptance
**T02 source coverage and archive integrity PASS.** Statistical golden-value verification (T03), revision/quality per cell, Eurostat parity (T04), and historical-publication gate remain OPEN. This artifact is unpublished and must not be treated as an authorized statistical website feed.
