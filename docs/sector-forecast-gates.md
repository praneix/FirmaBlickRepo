# Issue #16 | Independent sector forecast evaluation

## Preflight and permissions
- GitHub repository: `praneix/FirmaBlickRepo`, writable via connected GitHub; Issue #15 (PR #27) merged into the prototype integration branch.
- Existing Node 22, Python regression and Chromium desktop/mobile CI available. Standard library forecasting is sufficient, with no new dependencies or paid infrastructure.
- Real official Destatis GENESIS source vintages remain unavailable pending the user's secure personal token setup. Issues #10–12 and #14 retain independent official-data certification gates.
- No new API secret, Supabase storage, publication approval, production/main merge or changes to IIA.

## Independent series and model decisions
Evaluation order is **C28 machinery**, then **C29 automotive**, **C24 basic metals**, **C20 chemicals**. The source contract is Destatis GENESIS 42153-0002, WZ2008, Germany, monthly production volume **index**, with explicit adjustment, source vintage, base year, acquisition ID and SHA-256. No source series can silently borrow another sector's observations or aggregate certification.

Each sector is assigned a distinct `fb-sector-XX-seasonal-damped-trend` model identifier and version `1.0.0-XX`. The fixed candidate is the Issue #14 prior-year seasonal anchor and damped annual change, with **12 diagnostic monthly horizons** but zero publicly released forecast months. Each industry has its own rolling-origin comparison to seasonal naive, last value and drift, horizon-specific MAE/bias/MASE/sMAPE, early-vs-late stability, sample counts, source vintages, locked holdout and training-prefix interval coverage diagnostics.

`forecast/sectors.py` returns separate records including `source`, `diagnostic`, `structural_breaks`, `release_recommendation`, `model_version`, `reason`, and `forecast_input_sha256`. Failure of one industry's data or metric does not affect another industry's historical views or evaluation. Missing input produces a historical-only record rather than a forecast. A `aggregate_approved=True` value has **no authorization effect**.

## Shock detection and supplemental orders
A per-sector descriptive structural-break indicator flags absolute year-on-year index movements above 20%. This is an **uncalibrated anomaly flag** and assigns no cause, intervention, or economic interpretation. Potential shocks require additional independent validation. The candidate does not fit order indicators or external regressors; attempts to supply `orders_indicator` explicitly disable the candidate until incremental predictive value can be shown using properly frozen holdout evidence.

## Release policy
The prototype has **no production authorization path**. Every sector always returns:
- `status=historical_only` and `release_recommendation=historical_only`
- `release_approved=false` and `publication_approved=false`
- `public_forecast_available=false`, `forecast_months=[]`
- An independently documented reason and diagnostic or explicit source-failure information.

The protected `site/data/sector-forecast-status.json` contains four separate `false` release flags and readable per-industry historical-only explanations; it contains **no synthetic projection numbers**. The website's five-industry historical data desk now shows this state beside the selected industry. A strict browser release-contract validator rejects any changed approval, duplicated industry, or injected projection field and fails closed. The manufacturing aggregate retains its separate Issue #14 gate.

## External acceptance that cannot be simulated
To qualify actual sector forecasts, acquire authenticated historical table 42153-0002 observations, confirm official adjustment/index/reference dates, independently certify source-vintage fidelity, pin a sector-specific development/24-month final holdout split, validate all horizons versus the same sector's naive baselines, assess interval coverage and structural breaks, establish classification crosswalk transitions, and record a distinct explicit model-release authorization for *each* industry.

Passing synthetic tests is **engineering acceptance**, not empirical economic forecast accuracy. A public sector forecast remains forbidden until official-data and independent statistical acceptance are achieved.

## Verification
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- `npm ci && npm run build && npm test`
- GitHub Chromium historical-browser desktop 1365×900/mobile 390×844, now checking all four sector historical-only selections.
- Existing scenario-command Chromium regression remains mandatory.
- Source evidence: `data-contracts/industrial-observation.v1.schema.json`, `forecast/evaluation-protocol.v1.json`, GitHub epic #5 and Issues #10–16.

All updates are restricted to a feature PR against `agent/prototype-2-44525788542`. No production site or DNS change.
