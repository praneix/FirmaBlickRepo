# T07–T09 | First authentic-data retrospective forecast diagnostic (20 November 2026)

**Not a release-grade point-in-time backtest. No model release.** This is a directional diagnostic using real 141-month Destatis source observations, independently matched to Eurostat, but all values originate from the same November 2026 revised source vintage. Older as-of source vintages are not available. The source revision described in the September 2026 Destatis release is especially relevant.

## Original data and frozen model
- Five 2021=100 original monthly series (2015-01–2026-09) from authenticated GENESIS artifact 14613832495. Outer SHA256 `568b6d514643c85a777dc21e9cecf6aa36d2d8fe12bdf4a1e5ebef986a80d3de`.
- 705/705 records exactly equal to independent Eurostat archive 14612934209.
- Fixed candidate formula from existing `forecast/flagship.py`, damping `0.85`: prior-year same-month index plus annual mean change multiplied by `(1-0.85**h)/(1-0.85**12)`. Competing model: prior-year same-month (seasonal naive), plus last observed and linear first-to-last drift.
- For each horizon h=1,3,6,12, every target month in the reserved 2024-10–2026-09 **24-month holdout** is predicted from the prefix ending h months earlier. Each eligible horizon has 24 target errors; all calculation starts after 60 months of contiguous original-index history.
- Errors computed in index points. Improvement is `100*(1-MAE_candidate/MAE_seasonal_naive)`. Interval widths obtained using preceding within-training rolling absolute residuals of candidate and split-conformal quantile; none of these are a guarantee of 90% coverage.

## Observed diagnostics: percentage improvement in MAE versus seasonal naive

| Original series | Horizon 1 | Horizon 3 | Horizon 6 | Horizon 12 |
|---|---:|---:|---:|---:|
| C manufacturing | +3.5% | +5.9% | +7.6% | **-15.7%** |
| C20 chemicals | +5.1% | +5.6% | -10.6% | **-89.6%** |
| C24 metals | +0.5% | -4.5% | -15.5% | **-27.1%** |
| C28 machinery | +5.5% | +9.5% | +7.6% | **-36.8%** |
| C29 automotive | +0.1% | +1.3% | +3.8% | **-31.5%** |

## Aggregate C MAE, index points

| Horizon | Candidate | Seasonal naive | Last value | Linear drift |
|---|---:|---:|---:|---:|
| 1 | 3.1903 | 3.3042 | 7.8292 | 7.8577 |
| 3 | 3.1098 | 3.3042 | 7.9542 | 8.0371 |
| 6 | 3.0523 | 3.3042 | 6.9542 | 7.1387 |
| 12 | 3.8233 | 3.3042 | 3.3042 | 3.5707 |

Rounded display figures are derived from the independent local diagnostic, not model-release results. Training-prefix absolute-residual intervals produced 100% apparent coverage in the 24 targets at each horizon, exceeding the predeclared 80–98% range and suggesting overly wide, unhelpful intervals. They are not independently statistically calibrated.

## Conclusion: release gates FAIL
- The existing baseline candidate fails the locked **>=5% improvement at each horizon** requirement for all five industries (C fails 1m and 12m; all sectors fail 12m).
- Existing candidate's intervals would also fail the upper 98% empirical coverage cap in this diagnostic.
- Even apparently positive values at some horizons cannot satisfy point-in-time evaluation due to lack of historical availability vintages and locked independent as-of records.
- Maintain no public forecast for C, C20, C24, C28 or C29, keep 2030 trajectory illustrative only, and retain historical-only UX.
- Future engineering may test a separately preregistered seasonal-naive baseline or alternative candidate with honest uncertainty, but this evaluation must not be used to tune against the sealed holdout and then claim unbiased final superiority.

This is a **preliminary independent computation**. Before treating it as the formal CI-backed Issues #14/#16 evaluation, port the exact source parsing and model calculations into pinned repository code, independently reproduce results under CI against GitHub archived official artifacts, and preserve both original source hashes and experiment configuration.
