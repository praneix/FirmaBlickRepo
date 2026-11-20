# FirmaBlick Issue #10: Normalization, quality gates, lineage and quarantine

## Status and scope
The normalization pipeline consumes only existing immutable acquisition records from Issue #9. It emits validated **unpublished** observation packages or append-only quarantines. It cannot publish data to the website or set any acquisition publication flag. No Supabase project or GENESIS credential is necessary for offline testing; existing IIA infrastructure remains untouched.

## Explicit source profile
Each table requires an independently confirmed profile with value_variable_code, adjustment_variable_code, adjustment_attribute_code, adjustment classification, base-year, and quality_map. confirmed_against_official_metadata must be true, which is an asserted operator configuration rather than independent proof. This profile must be derived from an authenticated real GENESIS download before live acceptance. No profile is shipped as production-approved and there is no permissive fallback to an inferred series.

The pipeline distinguishes original, calendar-adjusted, seasonally-adjusted and seasonal+calendar-adjusted series, selects only an exact value variable and an exact adjustment attribute, and rejects cross-table adjustment mixing. It validates original WZ codes, sector coverage C/C20/C24/C28/C29, one canonical monthly period per industry/series, comparable period sets within a table, a unique and explicitly confirmed index base, quality flags, and strict source numeric syntax. Missing indicators yield null only with an explicit confirmed reason. Neither missing symbols nor source suppression flags turn into zero.

## Provenance
Each canonical observation follows the Issue #7 JSON schema and refers to its immutable acquisition UUID, SHA-256 of the exact raw ZIP, original source dimensions, series key, retrieved UTC, classification, index basis and a versioned transformation identifier. Its adjacent lineage record captures the original CSV row (header is row 1), value column, original text, exact Decimal value, raw quality code, source metadata SHA-256 and same acquisition UUID. The canonical numeric index is validated against its exact decimal representation before serialization; no normalization arithmetic, rebasing or smoothing is performed.

## Fail-closed processing
run_quality_gate(store, profiles) checks both latest table acquisitions. On success it writes an append-only run result in quality/validated/ and labels it VALIDATED_UNPUBLISHED. On a quality, metadata or storage problem it writes a separate QUARANTINED report with a machine-readable reason code; no partial validated result is written. Files are created with no-overwrite atomic hard links and 0600 permissions, under a 0700 directory. The original ZIP/metadata blobs and acquisition ledger are never mutated.

Tests verify repeated runs reproduce identical result payloads (except run IDs/timestamps), and failure-injection tests verify tampered source blobs are rejected. The profile is not a substitute for source metadata verification; no actual Destatis live-data connection is claimed.

## Usage
Run npm ci && npm run build && npm test; run python3 -m unittest discover -s tests -p 'test_*.py' -v.
The Python API is ingestion.normalize.run_quality_gate(SnapshotStore(path), profiles). It requires both tables to be archived first, and the caller must pass one fully confirmed profile per table. See tests/test_normalize.py for synthetic profile examples; these are NOT validated production mappings.

## Acceptance boundary
Synthetic official-format golden fixtures exercise byte-preserving source-to-canonical decimal equality. Actual official-source golden checks against published Destatis snapshots require a configured GENESIS personal token, a sanitized official reference fixture and confirmation of the live tablefile dimensions/quality/status codes. These remain outstanding external evidence. Do not promote source-normalized data to a public release or claim that production historical figures have been independently validated until that gate is completed.

Related GitHub Issues: #5 #7 #8 #9 #10.
