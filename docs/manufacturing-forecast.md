# FirmaBlick V1 Issue #14: Manufacturing forecast candidate and publication gate

## Engineering preflight
GitHub repository push permission, merged Issue #13 baseline and Python/Node/browser CI were verified. No new paid libraries, credentials, Supabase project, production deployment or DNS changes are required. The official-data acceptance gates for Issues #10–12 remain open. The candidate therefore remains **diagnostic-only**.

## Model specification, fixed before official model fitting
The target remains monthly Germany manufacturing industrial-production volume index, WZ2008 Section C, source GENESIS 42153-0001, using one explicitly verified seasonal adjustment and one index reference base. No chemistry, metals, machinery or automotive forecast is authorized here.

The `forecast/flagship.py` model `fb-manufacturing-seasonal-damped-trend` version 1.0.0 uses:
- **Last-year monthly seasonality**: observed index for the same calendar month in the latest complete 12-month cycle.
- **Local annual change**: mean(index of latest 12 months) minus mean(index of the preceding 12 months).
- **Damped forward trend**: annual change multiplied by the ratio `(1 − 0.85^h) / (1 − 0.85^12)`, so a 12-month projection incorporates exactly one annual increment while shorter horizons use damped fractions. Negative index projections are clipped to zero.
- **12 forecast horizons**: one month each through month 12. No unconditional extension to 2030. No model tuning, fitted random seed, external statistical package, exogenous energy data or training on Eurostat.

The candidate is a deliberately interpretable **baseline proposal**, not an empirically superior or statistically calibrated flagship until its complete validation plan passes.

## Reproducible output contract
`forecast_package(history, origin_month, origin_at, source)` requires a complete history of timestamped `Observation` records, plus an explicit immutable GENESIS table/industry/adjustment/base context. It returns:
- Model ID, semantic version, fixed parameters and scenario ID.
- Origin month and UTC time, observed end month, 12 target months and horizons.
- Input source acquisition UUID, raw ZIP SHA-256, source-adjustment/index base, latest admissible source vintage, forecast-input SHA-256 calculated exclusively from source observations that existed at the origin cutoff.
- A distinct projection value for every future month; intervals are either bounded diagnostic quantiles or explicit null with calibration count.
- `type=forecast_diagnostic_not_official_observation`, `official_source_certified=false`, `publication_approved=false`, with a written release-block reason.
- A withheld 2030 trajectory with a clear longer-horizon validation explanation.

All input observations are selected as of the forecast origin's *actual provided* information timestamp. A later revision never changes an earlier forecast. Missing/released-late data block fitting rather than silently introducing an imputation. Input source descriptors are not independently authenticated by this offline model.

## Interval construction and limitations
For each horizon (1–12), the engine performs rolling-origin forecasts on strictly earlier training prefixes with 60 or more observations, and collects absolute errors for targets **already observed inside that training prefix**. It derives a symmetric 90% nominal absolute-error half-width from the rank `ceil((n+1)*0.9)` of historical residuals. It requires at least 20 residuals; otherwise the interval is absent. Lower bounds are clipped to zero.

These overlapping-origin residuals may exhibit temporal dependence. They **do not establish independent 90% coverage**, exchangeability or calibrated tail probabilities. Empirical holdout coverage must be assessed using the frozen Issue #13 protocol; even passing tests with synthetic fixtures is never evidence of actual economic forecast accuracy.

## Independent benchmark evaluation
`evaluate_candidate` uses the Issue #13 rolling-origin machinery with exactly matched origins, targets, training availability and truth cutoff. It evaluates the candidate plus last-value, seasonal-naive and drift benchmarks on the same data, reports each horizon's MAE, signed bias, MASE, sMAPE, intervals, sample counts and early/late MAE stability. It rejects missing training history, unavailable truth and final-holdout dates. Evaluations are `publication_approved=false`, `history_evidence=not_independently_certified`.

`predeclared_gate` documents the numerical requirements for a future genuine flagship, consistent with Issue #13: at least 24 eligible origins; at least 12 *paired* per-horizon errors; 5% or greater MAE improvement over seasonal naive at each of 1/3/6/12 months; minimum 20 interval observations and 80–98% empirical coverage at every horizon. It always returns benchmark-only at this stage, even if someone changes the evaluation status field, until actual independently authenticated archival evidence, locked holdout review and an explicit authorization workflow are implemented. This prevents fabricated 'superiority' claims.

## Provenance and external acceptance
Successful official release needs: registered GENESIS personal API token, verified source values, separately confirmed adjustment/index-base/status mapping, genuine point-in-time archived vintages, final 24-month holdout lock, statistical calibration and external benchmark parity, publication/quality review and rollout authorization. These dependencies are recorded in Issues #10–12 and #14. There is **no public forecast artifact** and the original website's scenario simulator remains labelled illustrative.

## Automated evidence
Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` and `npm ci && npm run build && npm test`. CI also runs real Chromium browser QA at desktop and mobile sizes. Tests include candidate numerical fixture, per-horizon estimates, deterministic SHA fingerprints, source ID validation, 12-month output, future revision leakage, missing training and released-late rejection, locked holdout, interval availability, rolling-origin benchmark parity and benchmark-only release fallback.

No production, DNS, billing, other ventures or hosted infrastructure changes are part of this issue.
