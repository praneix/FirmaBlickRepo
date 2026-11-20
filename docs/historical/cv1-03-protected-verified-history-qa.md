# CV1-03: Source-backed historical intelligence in protected QA (20 November 2026)

## Ground truth and acceptance status
- A real-source protected-preview generator already exists in `scripts/build-verified-history-preview.py`. It verifies two authentic GENESIS acquisitions and an independent Eurostat JSON-stat source object, with **705/705 exact observations** for WZ2008 C, C20, C24, C28, C29.
- The original raw files exist as GitHub Actions artifacts `14613832495` / `14612934209` expiring 2026-12-20. The exact original ZIPs have also been restored, independently SHA-verified and saved in restricted Google Drive (issue #55).
- Existing source vintages are November 2026. All observations are `original` (unadjusted), 2021=100 monthly index, 2015-01 through 2026-09. **No per-cell status flag** in GENESIS FFCsv; never infer provisional/final status from recency.
- Commercial/public source publication is **blocked**. Original source archive bytes and authenticated/generated historical JSON **must not be committed to public GitHub**, uploaded as public CI artifacts, or included in a non-protected Vercel deployment.

## New engineering artifacts
- `scripts/verify-protected-history.py` rejects missing/duplicated sectors, periods, changed data definitions, source SHA mismatch, malformed flags, authorisation changes and modified comparator identity. Writes a manifest in `/tmp` with source hash linkage and generated JSON hash.
- `tests/verified-historical-browser.mjs` checks the *real reconstructed data*, with five sectors ×141 numeric table rows, industry selection, SVG chart, citations, 2021=100 labelling and no forecast release. Runs on 1365×900 and 390×844 Chromium.
- `.github/workflows/cv1-03-protected-history-qa.yml` downloads verified source artifacts into ephemeral runner storage, reconstructs the generated JSON, checks 705 cross-source parity, runs the real-data browser assertions, ensures no artifact upload of raw data, and sanitises generated files before the job completes.

## Source release controls
The site repository intentionally retains `site/data/historical.json` with status `unavailable`, because the owner and legal licence reviewers have not authorised public use. Source archives remain private from GitHub repo clones.

**Next production step after owner approval:** a reviewed source licence/rights decision and a trusted, version-pinned release manifest; build an approved `validated` release only after source golden-file and final product gates. The 2026-11 vintage is an original-source snapshot, not the basis for point-in-time forecasting claims.

## Revision-aware refresh design
- Source retrieval must produce an immutable source object hash and new acquisition event. Old vintages stay available in restricted backup, including original bytes and provenance metadata.
- Run metadata/classification/unit and Eurostat comparator equivalence checks; abort with quarantine reason if a source dimension or value changes unexpectedly.
- Generate a new candidate and compare period-by-period across all 5 sectors. Revisions are recorded as differences with old/new object SHA and retrieval dates, never rewritten as previously observed truth.
- A newly verified source snapshot may be used for a fresh **protected preview**; a public refreshed release requires the same licence and owner release controls. On refresh failures, keep the last separately *approved public* release with correct vintage/stale flag or display the fail-closed unavailable state. Never substitute synthetic data.

## Remaining blocked gate
A **live authenticated Vercel browser test of the ephemeral source-backed build** is still required before issue #41 is fully accepted. Prior Vercel CLI deployment failed from missing VERCEL_TOKEN and daily quota; the present workflow intentionally performs GitHub Actions real-data Chromium tests without publishing any data. Owner-supplied secure deployment credentials and authorised protected-target execution will be considered only when safe, and actual SSO access/HTTP headers must be verified. No production/DNS or paid report release is implied.

## Evidence
- Source parity: earlier PR #33 and protected source original-run logs.
- Original archive integrity, Drive backup and tamper rejection: PR #56.
- This PR's CI logs show the current exact-source reconstruction and responsive browser QA.
