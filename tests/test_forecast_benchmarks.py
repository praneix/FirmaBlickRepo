"""Synthetic-only rolling origin benchmark and non-leakage protocol regression tests."""
import math
import unittest
from datetime import datetime, timezone
from forecast.benchmarks import (
    Observation, ForecastError, HORIZONS, METHODS, MIN_TRAIN_MONTHS,
    _month_number, _month_string, _scale, _smape, predict,
    as_of, run_backtest, release_decision
)


def synthetic(n=124, start="2016-01", *,
              revision=False, missing_at=None, forward_released=False):
    base=_month_number(start)
    out=[]
    for i in range(n):
        month=_month_string(base+i)
        next_month=_month_string(base+i+1)
        year,m=map(int,next_month.split("-"))
        # An observation is published in the following month on the 15th.
        stamp=f"{year:04d}-{m:02d}-15T12:00:00Z"
        value=100+(i//12)*0.8+(i%12)*0.7
        if missing_at is not None and i==missing_at:
            value=None
        if forward_released and i==50:
            stamp="2035-01-01T00:00:00Z"
        out.append(Observation(month,value,stamp,f"synthetic-original-{i}"))
        if revision and i==40:
            out.append(Observation(month,value+9.0,"2028-01-01T00:00:00Z",
                                   "synthetic-future-revision"))
    return out


def origins(first="2022-01", n=20):
    start=_month_number(first)
    result=[]
    for i in range(n):
        month=_month_string(start+i)
        following=_month_string(start+i+1)
        result.append({"month":month,"available_at":following+"-20T00:00:00Z"})
    return result


class BenchmarkTests(unittest.TestCase):
    def test_last_value_seasonal_naive_and_linear_drift_have_known_values(self):
        # 5 full years plus trend from explicit synthetic fixture.
        training=[float(i) for i in range(60)]
        self.assertEqual(predict("last_value",training,1),59.0)
        self.assertEqual(predict("last_value",training,12),59.0)
        self.assertEqual(predict("seasonal_naive",training,1),48.0)
        self.assertEqual(predict("seasonal_naive",training,3),50.0)
        self.assertEqual(predict("seasonal_naive",training,12),59.0)
        self.assertEqual(predict("drift",training,1),60.0)
        self.assertEqual(predict("drift",training,12),71.0)

    def test_methods_reject_invalid_input(self):
        for fn in [
            lambda:predict("ARIMA",list(range(60)),1),
            lambda:predict("last_value",list(range(59)),1),
            lambda:predict("last_value",list(range(60)),13),
            lambda:predict("seasonal_naive",[float("nan")]*60,2)
        ]:
            with self.assertRaises(ForecastError):fn()

    def test_original_vintage_asof_excludes_future_revision(self):
        history=synthetic(revision=True)
        early=as_of(history,"2024-01-20T00:00:00Z")
        late=as_of(history,"2029-01-20T00:00:00Z")
        m=history[40].month
        self.assertEqual(early[m].source_vintage,"synthetic-original-40")
        self.assertEqual(late[m].source_vintage,"synthetic-future-revision")
        self.assertEqual(late[m].value,early[m].value+9.0)

    def test_future_not_yet_available_is_excluded_without_backfill(self):
        history=synthetic(forward_released=True)
        selected=as_of(history,"2022-06-20T00:00:00Z")
        self.assertNotIn(history[50].month,selected)
        report=run_backtest(history,origins("2022-01",12),"2027-01-01T00:00:00Z")
        self.assertEqual(report["origins_eligible"],0)
        self.assertTrue(report["excluded"])
        self.assertTrue(any("Missing training months" in r["reason"] for r in report["excluded"]))

    def test_origin_cannot_see_later_target_or_future_release(self):
        history=synthetic()
        result=run_backtest(history,origins("2022-01",14),"2027-01-01T00:00:00Z")
        self.assertEqual(result["assessment"],"synthetic_or_unverified_diagnostic")
        self.assertFalse(result["real_time_claim_permitted"])
        self.assertFalse(result["official_source_certified"])
        self.assertEqual(result["origins_eligible"],14)
        self.assertEqual(result["publication_approved"],False)
        self.assertTrue(result["predictions"])
        for p in result["predictions"]:
            self.assertLessEqual(p["information_max_available_at"],p["origin_at"])
            self.assertGreater(_month_number(p["target"]),_month_number(p["origin"]))
            self.assertTrue(p["information_latest_vintage"].startswith("synthetic"))
            self.assertIn(p["method"],METHODS)
            self.assertIn(p["horizon"],HORIZONS)

    def test_reproduces_identical_results_and_training_hash(self):
        h=synthetic()
        a=run_backtest(h,origins("2022-01",13),"2027-01-01T00:00:00Z")
        b=run_backtest(h,origins("2022-01",13),"2027-01-01T00:00:00Z")
        self.assertEqual(a,b)
        self.assertEqual(len(a["history_sha256"]),64)
        altered=list(h)
        o=altered[-1]
        altered[-1]=Observation(o.month,o.value+1,o.available_at,o.source_vintage)
        c=run_backtest(altered,origins("2022-01",13),"2027-01-01T00:00:00Z")
        self.assertNotEqual(a["history_sha256"],c["history_sha256"])

    def test_all_horizons_include_bias_mae_mase_smape_sample_counts(self):
        result=run_backtest(synthetic(),origins("2022-01",20),"2027-01-01T00:00:00Z")
        for method in METHODS:
            for h in HORIZONS:
                met=result["metrics"][method][str(h)]
                self.assertEqual(met["n"],20)
                self.assertGreaterEqual(met["mae"],0)
                self.assertTrue(math.isfinite(met["bias"]))
                self.assertTrue(math.isfinite(met["mase"]))
                self.assertTrue(math.isfinite(met["smape"]))
                self.assertIsNone(met["interval_coverage"])
                self.assertEqual(met["interval_count"],0)

    def test_mase_is_training_only_and_constant_series_handled(self):
        self.assertEqual(_scale(list(range(60))),12.0)
        self.assertIsNone(_scale([100.0]*60))
        self.assertIsNone(_smape(0.0,0.0))
        result=run_backtest([Observation(x.month,100.0,x.available_at,x.source_vintage)
                             for x in synthetic()],
                            origins("2022-01",12),"2027-01-01T00:00:00Z")
        self.assertIsNone(result["metrics"]["last_value"]["1"]["mase"])
        self.assertEqual(result["metrics"]["last_value"]["1"]["smape"],0.0)
        self.assertIsNone(_smape(0.0,0.0))

    def test_interval_coverage_requires_external_precalibrated_bounds(self):
        result=run_backtest(synthetic(),origins("2022-01",16),
                            "2027-01-01T00:00:00Z",
                            intervals={"last_value":{1:50.0,3:50.0,6:50.0,12:50.0}})
        one=result["metrics"]["last_value"]["1"]
        self.assertEqual(one["interval_count"],16)
        self.assertEqual(one["interval_coverage"],1.0)
        self.assertGreater(one["mean_interval_width"],0)
        self.assertEqual(result["metrics"]["drift"]["1"]["interval_count"],0)
        with self.assertRaises(ForecastError):
            run_backtest(synthetic(),origins("2022-01",12),"2027-01-01T00:00:00Z",
                         intervals={"last_value":{1:-1.0}})

    def test_horizon_specific_cutoff_and_counts(self):
        result=run_backtest(synthetic(),origins("2023-01",15),
                            "2024-04-20T00:00:00Z")
        self.assertEqual(result["metrics"]["last_value"]["1"]["n"],14)
        self.assertLess(result["metrics"]["last_value"]["12"]["n"],14)
        self.assertTrue(any(e["reason"].startswith("Target truth unavailable")
                            for e in result["excluded"]))

    def test_final_holdout_does_not_enter_development_scoring(self):
        result=run_backtest(synthetic(),origins("2022-01",24),
                            "2027-01-01T00:00:00Z", final_holdout_start="2023-07")
        self.assertEqual(result["final_holdout_start"],"2023-07")
        self.assertTrue(all(p["target"]<"2023-07" for p in result["predictions"]))
        self.assertTrue(any(e["reason"]=="Locked final 24-month holdout."
                            for e in result["excluded"]))
        with self.assertRaises(ForecastError):
            run_backtest(synthetic(),origins("2022-01",12),
                         "2027-01-01T00:00:00Z",allow_diagnostic=False)

    def test_release_decision_fails_closed_on_all_synthetic_data(self):
        result=run_backtest(synthetic(),origins("2022-01",24),
                            "2027-01-01T00:00:00Z")
        self.assertFalse(release_decision(result)["approved"])
        assert "official" in release_decision(result)["reason"]
        self.assertFalse(release_decision(result,final_holdout_unlocked=True,
                                         model_metrics={"1":{"mae":0}})["approved"])

    def test_rejects_missing_reordered_duplicate_origins_and_invalid_vintage_metadata(self):
        h=synthetic()
        for bad in [
          origins("2022-01",12)[::-1],
          [origins("2022-01",12)[0]]*12
        ]:
            with self.assertRaises(ForecastError):
                run_backtest(h,bad,"2027-01-01T00:00:00Z")
        with self.assertRaises(ForecastError):
            Observation("2022-13",100.0,"2022-02-15T00:00:00Z","vintage")
        with self.assertRaises(ForecastError):
            Observation("2022-01",100.0,"2022-02-15T00:00:00+05:30","vintage")
        with self.assertRaises(ForecastError):
            Observation("2022-01",float("inf"),"2022-02-15T00:00:00Z","vintage")

    def test_missing_training_values_exclude_origin_without_zero_imputation(self):
        h=synthetic(missing_at=70)
        result=run_backtest(h,origins("2022-01",15),"2027-01-01T00:00:00Z")
        self.assertEqual(result["origins_eligible"],0)
        self.assertTrue(all(r["reason"].startswith("Training data contains")
                            for r in result["excluded"] if "reason" in r))

    def test_explicit_protocol_has_no_claim_of_model_superiority(self):
        result=run_backtest(synthetic(),origins("2022-01",12),
                            "2027-01-01T00:00:00Z")
        self.assertFalse(result["real_time_claim_permitted"])
        self.assertEqual(result["interval_policy"],
                         "precalibrated_nonnegative_halfwidth_only; none means coverage unavailable")
        self.assertNotIn("best_model",result)
        self.assertNotIn("statistical_significance",result)


if __name__=="__main__":
    unittest.main()
