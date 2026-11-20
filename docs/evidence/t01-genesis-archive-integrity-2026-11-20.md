# T01 | Authenticated GENESIS raw archive integrity inventory
Verified: 2026-11-20. Evidence source: GitHub Actions workflow run https://github.com/praneix/FirmaBlickRepo/actions/runs/44693586709 ; artifact 14609502111.

## Integrity
- Artifact file: `genesis-official-raw-discovery.zip`
- Artifact ZIP bytes: 133065
- Artifact SHA-256: `0fc07ab529f268b1b85304a57b116566f2d14ab867aca13ef61fa7445d788b62` (agrees with GitHub artifact digest)
- Contains one acquisition SQLite ledger, one discovery manifest and four immutable source objects.
- Python independently read the ZIP and verified each object contents SHA-256 against its content-addressed basename. All four passed:
  - `109250bdd9ca2b16a8fee500c72ea8474863860d92021bc1d305a79e4cd349cb` 1757 bytes
  - `0326aa368dc9ecf2a6ad3feaf545bdfeb45477bb1b6bdd5024b6633e409ec7ce` 89156 bytes
  - `2110bb228ec9b6aeeed48fc5f09ec34c9cf548ad6cbf68c06f6416e803ef77cf` 1739 bytes
  - `61e5186029e42ab7f6bf2c8e4fa8b49d7c2cf7d06b7407dc975bab3284c099d9` 39006 bytes

## Discovery manifest
- `42153-0001`: dataset C, base year 2021, 132 matched rows, retrieved 2026-11-20T07:15:37.399243Z.
- `42153-0002`: dataset 20/24/28/29, base year 2021, 528 matched rows, retrieved 2026-11-20T07:15:50.084478Z.
- Manifest declares `status=discovery_only_not_published`, `verified_raw_files=4`.
- The confirmed actual source-layout note reports 33 months per selected sector/adjustment, Jan 2024–Sep 2026.

## Scope of completed verification
**PASS:** artifact download/existence, outer digest equality, all four inner content-addressed blob digests, five codes in discovery manifest, official acquisition job completed successfully.
**NOT YET TESTED:** independent official published numerical comparison; interpretation of release/revision statuses; extended date coverage; Eurostat values; source payload-to-observation reconstruction; forecast fitness. Archive evidence must not be promoted to publication by itself.

## Retention risk
GitHub artifact retention is through 2026-12-20 (per artifact metadata). Preserve an immutable approved destination before that date. Do not place raw official data under a publicly accessible website path or publish it without license review.

## Next task
T02: expand the authenticated original-source window sufficiently for >=60 months of training, frozen 24-month final holdout, and rolling-origin backtesting. Validate API date selection and historical metadata before acceptance. This likely needs the already-configured GitHub `GENESIS_TOKEN` in a credential-safe workflow, not exposure of the secret.


## Additional raw CSV inspection
The two nested stored ZIP files contain FFCsv text with respectively 7,260 and 3,828 rows covering the complete source table categories, beyond the five target series. The embedded raw CSV text lengths were 2,565,400 and 1,322,974 bytes. All target observations use index unit `2021=100` and value code `PRO101`. The four observed adjustment codes are `WERTORG`, `X13JDKB`, `X13JDKSB`, and `BV4TB`; semantic verification of `BV4TB` is pending. Raw **original** January 2024 observations are C=90.1, C20=84.0, C24=93.6, C28=82.8, C29=100.2 (index points), extracted directly from the snapshot. They are **not** independently checked against a separate Destatis published display, so they are not golden-file parity evidence. The source CSV omits a standalone quality column, and no per-cell final/revised status is asserted.
