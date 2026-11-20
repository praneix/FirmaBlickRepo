# FirmaBlick Issue #15: deterministic scenario controls

## Preflight and scope
PR #26 is already merged into the isolated FirmaBlick prototype branch. GitHub account has push/admin permission. Node 22, Python and pinned Playwright Chromium CI are available. No new app subscription, provider token, LLM integration, cloud storage, production or DNS change is needed. The unfinished official-data evidence gates for Issues #10–12 and #14 remain explicitly separate.

## Interactive behavior
The new Ask FirmaBlick entry below the existing scenario/chart interface accepts constrained plain-English instructions. It updates these existing fields without changing unspecified choices:
- Reference case: Central, Resilience, Transformation.
- Productivity gain: 0–5% inclusive in 0.1 percentage-point increments.
- Year productivity starts: 2027, 2028 or 2029.
- Energy-price deviation: −3% to +3% in 0.1 percentage-point increments; explicit constant means 0%.
- Comparator: None, Central, Resilience, Transformation.

Commands can update one or multiple values atomically. The user can issue successive commands; the parser reads the **current tab's control values** on every turn. A validation failure, negation, unknown request, unsupported parameter, conflicting assignments, out-of-range number or ambiguous wording returns an explicit clarification and **changes no controls**. A read-only 'show chart/outlook' command leaves all controls unchanged. Manual slider/select changes remain authoritative.

Example: “Use FirmaBlick's Central Case for German industrial production. Assume a 3% annual productivity improvement from 2028. Hold energy prices constant in real terms. Show the resulting 2030 outlook and compare it against the Resilience Case.”

The system uses a fixed deterministic grammar implemented in `site/scenario-command-core.mjs` with an ephemeral client adapter `site/scenario-command.mjs`. No LLM, network fetch, localStorage, sessionStorage, cookies, user account, transcript store or analytics events are introduced. Input is limited to 450 characters. The current output is displayed in an `aria-live` status with keyboard-accessible text field and submit button. Starting a fresh tab starts from default sliders, not a saved conversation.

## Economic model limitations
The scenario remains a **synthetic exploratory index**, beginning at 100 in 2026. The three indicative annual scenario growth rates are Central 0.8%, Resilience 1.4%, and Transformation 2.2%. Every year, from the selected start date, assumed productivity percentage points add directly to scenario index growth; assumed energy changes multiply an **uncalibrated** coefficient of −0.35. These figures are not empirical causal estimates, not sector output/revenue, not the officially validated German manufacturing historical index and not forecasts issued by `forecast/flagship.py`. The exact assumptions are rendered next to the command result; official/forecast release gates remain intact.

The parser confirms all resulting assumptions and explicitly states that no calibrated economic forecast was changed. It does not claim to interpret unrestricted English; unsupported phrasing is rejected rather than guessed. No scenario sensitivity is presented as sourced, official or externally validated.

## Regression requirements
`npm test` verifies the pure grammar across upper/lower bounds, decimal precision, multiple clauses, same-field conflicts, negation, unknown instructions, comparison versus primary scenario, follow-ups, fresh-tab behavior and deterministic simulated trajectory. Existing Node tests, Python ingest/quality/forecast tests and negative GENESIS token check remain mandatory.

`tests/scenario-browser.mjs` executes Chromium on desktop 1365×900 and mobile 390×844. It tests a multi-sentence executive instruction, updates to every slider/select, table/chart refresh, successive updates preserving unnamed fields, atomic rejection, manual slider consistency, no browser JS exceptions, no LLM/API calls and a fresh tab reverting to defaults. Screenshots are artifacts of the CI workflow. The historical official-data empty state is tested independently by existing `tests/historical-browser.mjs`.

## Security and release
This is an engineering feature on the prototype branch only. Any numerical 2030 value remains explicitly illustrative. External publication of a calibrated forecast or scenario coefficient requires official-source parity, separate documented econometric sensitivity calibration, candidate benchmark approval and release sign-off. No third-party infrastructure or customer data is accessed.
