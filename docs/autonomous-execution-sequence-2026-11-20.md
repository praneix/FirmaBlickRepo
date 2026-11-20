# FirmaBlick | Sequential autonomous engineering execution plan
Date: 2026-11-20
Source of authority: Owner explicitly approved carrying out the engineering sequence in conversation, with owner role reduced to approval. This plan is not an independent release authorization.

## Operational guardrails
- Work exclusively in `praneix/FirmaBlickRepo`, isolated feature branches and PRs; do not alter IIA/SER/DesiPlat.
- Keep `main`, public production, DNS and domain unchanged until the specific release candidate passes quality/security/legal acceptance and owner gives final go-live approval.
- No paid infrastructure, third-party spend or expansion of credential scope without approval.
- No fake numbers or simulation in published history, comparison or forecast; preserve immutable source bytes, snapshots and vintages.
- Engineering can proceed automatically through source verification, tests and protected previews. Stop only on unavailable credentials/permissions, external expenditure, legally consequential decisions or the final irreversible public launch.
- Do not use broad agent-dispatch labels; use isolated PRs with tests and review.

## Strict execution order and artifacts

### T01 — Establish evidence baseline [#10]
- Confirm current integration SHA, last green CI, existing schema, published/unpublished status and exact raw artifact provenance from Actions run 44693586709, artifact 14609502111.
- Verify hash and manifest of both original 42153-0001 and 42153-0002 tables; keep copies immutable; record downloadable archive retention expiry.
- Deliver `evidence/source-acquisition-inventory.md` or comparable machine-readable inventory. Fail closed if raw bytes are inaccessible or checksums do not match.

### T02 — Acquire sufficient authentic history [#8, #9, #10, #13]
- Request authoritative monthly production indexes from Jan 2015 or earliest defensibly comparable available period to latest official vintage, both aggregate C and sectors C20/C24/C28/C29.
- Identify actual GENESIS API pagination/selection, date-range and rate-limit behavior; retain original full source responses and SHA256, UTC retrieval, queries and metadata, never credentials.
- Target at least 60 months available for training plus a 24-month locked holdout and sufficient rolling-origin samples. If unavailable, document the resulting evaluation limitation instead of weakening protocol after seeing results.
- Preserve original vs calendar vs seasonal adjustment and 2021=100 base, explicit WZ coding; never concatenate inconsistent definitions.
- Deliver archive + coverage report + missing-period report.

### T03 — Independent official-value parity [#10]
- Verify at least one selected month per year and per sector where practical against an independently viewed official Destatis table/download (not just a round trip through same normalizer); include earliest/latest and revision-sensitive periods.
- Exact decimal comparison of source official published value vs normalized observation, row/column, raw SHA, source vintage, period, series dimensions, adjustment.
- Distinguish source status absent from status unknown and from actual provisional/revised codes. Derive source release/revision policy only from named official documentation and preserve raw source flags.
- Fail publication for any unexplained discrepancy. Deliver machine-readable golden check report and human-facing evidence note.

### T04 — Eurostat cross-source parity [#11]
- Fetch actual `sts_inpr_m` JSON-stat 2.0 geo=DE frequency=M, discover dimensions, inspect unit, indicator, NACE and adjustment, and store immutable response/version.
- Construct independently vetted WZ2008/NACE Rev2 mapping and compare matching months/series only after definition and base equality.
- Report exact, within-tolerance and unacceptable differences; unmatched dates/dimensions and revisions without overwriting Destatis.
- Keep 2028 NACE Rev2.1 transition quarantined without approved crosswalk/backcast.
- Deliver 5-industry reconciliation ledger with source references and as-of dates.

### T05 — Freeze historical source package [#10, #11, #12]
- Publish internal, content-addressed, validated five-series historical artifact, fixed contract and manifest; include observation-level data vintages, source statuses, lineage, adjustment/base and no missing→zero.
- Require T03 and T04 evidence; if Eurostat differences are unresolved, explicitly decide on historical Destatis-only availability with disclosure, never silently sign off equality.
- Deliver reproducible fixture, snapshot digest and stale-source fallback.

### T06 — Prepare five historical production-index charts in protected preview [#12]
- Render C/C20/C24/C28/C29 as verified index values, with selection/time-range, units/2021=100, source-date and adjustment labels, original-vs-adjusted distinctions, accessible table and mobile/keyboard behavior.
- Preserve clearly marked illustrative scenario demo independently.
- Run Node/Python/Chromium CI and actual protected Vercel preview checks; do not publish to production.
- Deliver screenshots/test logs and a chart-by-chart parity spot check against T05.

### T07 — Run genuine aggregate benchmark evaluation [#13, #14]
- Freeze protocol `forecast/evaluation-protocol.v1.json` before holdout exposure; verify point-in-time vintage availability per rolling origin or explicitly downgrade retrospective claims.
- Run naive last, seasonal naive, drift and predeclared candidate on identical origin/target pairs, horizons 1/3/6/12; record MAE, MASE, sMAPE, bias, counts, stability, interval coverage.
- Require at least 60 months training, 24 reserved holdout and predeclared counts; do not fabricate real-time vintage history when unavailable.
- Deliver pinned inputs, commands, code SHA, full evaluation ledger and independent model-release recommendation.

### T08 — Aggregate manufacturing publication decision [#14]
- Evaluate candidate versus frozen gate (at least 5% lower MAE at every horizon, acceptable interval coverage/counts, independent review) and determine release status.
- If gate fails, preserve five historical charts while holding aggregate forecasts as benchmark-only or unavailable. Long trajectory to 2030 needs separate justified model/uncertainty.
- Deliver versioned recommendation and release flag, no unsupported precision claim.

### T09 — Genuine independent sector evaluations [#16]
- Test C28 machinery first, then C29 automotive, C24 metals and C20 chemicals, each with independently pinned observations/vintages and the same frozen evaluation protocol.
- Evaluate shock/structural breaks, baseline comparisons and uncertainty separately. No aggregate pass can auto-release a sector.
- Deliver four independent run reports and release flags; keep failed sectors historical-only.

### T10 — Scenario control integrity and content QA [#15, #17]
- Preserve deterministic Central/Transformative/etc UI and controls: productivity 0–5%, start year 2027/28/29, energy -3% to +3%, comparison selection, supported-command parser.
- Clearly distinguish empirical forecasts from exploratory scenario overlays; don't imply causal calibration until validated.
- Validate no unsupported scenario claim in tables/plots/chat.

### T11 — Protected preview acceptance & legal/privacy/security [#17]
- Pin Git SHA, data snapshot, model versions; test protected Vercel directly with authorized browser, preview URLs/response headers, desktop/mobile, provenance, navigation, accessibility and invalid data.
- Check no client credentials, data collection, external resources and source licensing; accurately show DesiPlat operator and India-only FirmaBlick trademark position, without claiming EU trademark.
- Prepare legally required operator identity/contact, imprint, GDPR/privacy and third-party resource disclosures for user/legal review. No self-certification of legal compliance.

### T12 — Produce release candidate and explicit decision package [#17]
- Write release manifest with Git/data/model hashes, passed CI/browser checks, five golden checks and reconciliation summary, security/legal review, known limitations.
- Apply fail-closed gate; submit a concise final owner decision packet: preview URL, changes, residual risks, launch/reject.
- Only upon explicit approval for the named final release candidate: merge/promote production and separately configure DNS if authorized. No implied release from generic engineering authorization.

## Acceptance sequencing
T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12.
Tasks T07–T10 may be developed against verified snapshots once T05 succeeds, but do not reorder certification/release gates.

## Current blockers known at plan creation
- Existing 2024-01 to 2026-09 official acquisition contains only 33 months per series, below 60-month training requirement, plus 24-month holdout.
- Actual source FFCsv lacks dedicated quality column; revision status evidence and independent value parity are not complete.
- Live Eurostat numeric comparison not documented as accepted.
- Current historical JSON is unavailable; forecasts and all sector release flags are false.
- Vercel latest deployment READY, SSO protected; authenticated browser verification not yet evidenced.
- Beta manifest BLOCKED; operator legal notice and manual go-live sign-off remain pending.

## Owner interaction policy
No owner interaction for ordinary fetching, coding, fixtures, CI, PRs or preview QA. Ask for action only for credentials blocked by access controls, nontrivial additional spending, authoritative legal identity/contact supplied by owner, or final named release authorization.
