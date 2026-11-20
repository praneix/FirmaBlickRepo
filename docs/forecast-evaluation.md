# FirmaBlick v1 | Forecast benchmarking & rolling-origin evaluation (Issue #13)

## Engineering preflight and scope
GitHub write access, verified merged Issue #12 baseline and existing Node/Python/Chromium CI were checked before implementation. No GENESIS token, customer database, paid libraries or production deployment is required. All Issue #13 tests are **synthetic-only**.

## Predeclared target and protocol
See `forecast/evaluation-protocol.v1.json` for the machine-readable locked evaluation plan. The initial target is the **German manufacturing aggregate production volume index (WZ2008 Section C)** sourced from Destatis table `42153-0001`. Exactly one provider-confirmed adjustment and index base must be used; the four sector forecasts are gated separately under Issue #16. Forecast horizons are 1, 3, 6 and 12 months; monthly, expanding-window rolling origins; at least 60 complete known training months. Hold out the final 24 target months for an eventual independent locked evaluation.

Three initial comparators are implemented: last observed monthly value; seasonal naïve (same month in preceding 12-month cycle); and a drift extrapolation based on first-to-last training observation. No ARIMA/ETS complexity is justified until these baselines are measured against real verified vintages.

## Protection against look-ahead bias
Each observation must include its **month, index value (or explicit missing), available_at UTC and source_vintage identity**. Each origin specifies an explicit decision timestamp; its training subset uses only data already available then. A later source revision never enters earlier origin training. Target truth is measured as of an explicit scoring cutoff, separately from the point-in-time training set. If a month was unavailable, the origin is excluded with a reason; there is no zero-fill, future interpolation or full-sample scaling. MASE denominators are calculated from the training history at that origin only.

The local harness cannot itself prove that an operator-supplied timestamp is authentic. Until actual immutable GENESIS source events and release metadata have been independently attested (Issues #10–12), outputs are explicitly marked `synthetic_or_unverified_diagnostic`, `real_time_claim_permitted=false`, `official_source_certified=false`, `publication_approved=false`. The release gate always fails closed for such results, even if numeric errors appear impressive. Formal real-time assessment requires a separately reviewed ingestion-vintage adapter and official-source evidence.

## Accuracy and uncertainty
Every horizon/method reports MAE in index points, forecast-minus-actual bias, MASE, sMAPE, counts and optional empirical interval coverage. Zero training-scale or zero-denominator sMAPE are marked unavailable rather than assigned zero. Pointwise prediction interval coverage is *only* computed if explicit pre-calibrated half-widths are provided; those half-widths must themselves be fitted without future information. This task does not manufacture or assert 90% prediction intervals.

**Final holdout discipline:** development runs may set `final_holdout_start` to exclude any target from the final 24-month window. Once genuine vintages are available, lock and hash the final holdout split before model selection. Overlapping monthly forecast errors are dependent; raw nominal coverage on small samples must be interpreted cautiously. Horizon-specific and rolling-window stability must be reviewed before any model is declared superior.

## Candidate quality gate (frozen in protocol before genuine model trials)
A future candidate must use identical source vintages and same forecast origin/target pairs as seasonal naive, demonstrate at least 5% lower MAE at every tested horizon, and show empirical interval coverage near a nominal 90% target (predeclared acceptance 80–98% and at least 20 interval observations per horizon). At least 24 eligible development origins and 12 comparable holdout errors per horizon are required; a separate independent review must authorize release. These are *provisional decision criteria* fixed before official holdout exposure, not observed performance claims.

**Fail-closed outcome:** Any source-gate, evaluation or statistical acceptance failure returns benchmark-only evidence, with no superior-forecast claim. The current `release_decision` intentionally blocks all uncertified results. Issue #14 will introduce a candidate forecasting model and govern its calibration separately.

## Reproducible verification
`python3 -m unittest discover -s tests -p 'test_*.py' -v` runs fixtures for seasonal naïve, last-value and drift forecasts, expanding rolling origins, vintage revision leakage checks, training-length and missing-observation exclusions, horizon error/interval metrics, protocol determinism, final holdout exclusion and publication blocking. `npm ci && npm run build && npm test` and the existing Chromium historical UI workflow remain required on the same PR.

## Methodological references
- Hyndman and Athanasopoulos, *Forecasting: Principles and Practice*, rolling-origin evaluation and forecasting toolbox: https://otexts.com/fpp3/toolbox.html
- Rob Hyndman, rolling-scaled forecast accuracy: https://otext.robjhyndman.com/hyndsight/rolling_mase.html
- Source contract and deferred official parity: GitHub issues #5, #10, #11, #12, #13.

## Release limitations
No actual official German data were analyzed in this engineering task; all benchmark numbers in regression tests are fabricated deterministic fixtures. No hosted infrastructure, domain/DNS, existing IIA application or production site were modified.
