"""Deterministic Issue #14 manufacturing forecasting and fail-closed release tests.

All source values and vintages are synthetic test fixtures, not official Destatis.
"""
import math
import unittest
from forecast.flagship import (
    MODEL_ID, MODEL_VERSION, point_forecast, calibrate_intervals,
    forecast_package, evaluate_candidate, predeclared_gate,
)
from forecast.benchmarks import Observation, ForecastError, _month_number, _month_string


def fixtures(n=170, *, start="2010-01", future_revision=False,
             missing_at=None, future_release_at=None):
    base=_month_number(start)
    result=[]
    for i in range(n):
        month=_month_string(base+i)
        nxt=_month_string(base+i+1)
        year,mo=map(int,nxt.split("-"))
        stamp=f"{year:04d}-{mo:02d}-12T00:00:00Z"
        # Upward drift + stable seasonality: deterministic benchmark data
        value=80+i*.12+(i%12)*1.3
        if i==missing_at:value=None
        if i==future_release_at:stamp="2032-01-01T00:00:00Z"
        result.append(Observation(month,value,stamp,f"synthetic-vintage-{i}"))
        if future_revision and i==32:
            result.append(Observation(month,value+40,"2026-01-01T00:00:00Z",
                                      "synthetic-later-revision"))
    return result


def source(**changes):
    return {"dataset_id":"42153-0001","industry_code":"C","geo":"DE",
            "frequency":"M","unit":"index","base_year":2021,
            "adjustment":"original","classification_revision":"WZ2008",
            "raw_sha256":"b"*64,"acquisition_id":"synthetic-acquisition",
            "official_source_certified":False,**changes}


def origins(start="2020-01",count=24):
    first=_month_number(start)
    out=[]
    for i in range(count):
        month=_month_string(first+i)
        after=_month_string(first+i+1)
        out.append({"month":month,"available_at":after+"-20T00:00:00Z"})
    return out


class ManufacturingForecastTests(unittest.TestCase):
    def test_monthly_candidate_model_is_explicit_and_reproducible(self):
        vals=[float(i) for i in range(60)]
        self.assertEqual(point_forecast(vals,1),48+12*.85)
        self.assertAlmostEqual(point_forecast(vals,12),
                               59+12*(.85*(1-.85**12)/(.15)))
        self.assertEqual(point_forecast(vals,1),point_forecast(vals,1))

    def test_zero_floor_and_training_only_inputs(self):
        vals=[float(200-i*3) for i in range(60)]
        self.assertGreaterEqual(point_forecast(vals,12),0)
        for problem in [
            lambda:point_forecast([90.]*59,1),
            lambda:point_forecast([90.]*60,13),
            lambda:point_forecast([90.]*60,0),
            lambda:point_forecast([float("nan")]*60,1),
            lambda:point_forecast([90.]*60,1,damping=1.0),
            lambda:point_forecast([90.]*60,1,damping=float("inf")),
        ]:
            with self.assertRaises(ForecastError):problem()

    def test_calibration_never_sees_outside_training_prefix(self):
        original=fixtures(120)
        vals=[x.value for x in original]
        first=calibrate_intervals(vals[:100])
        changed=list(vals)
        changed[101]+=999999
        self.assertEqual(calibrate_intervals(changed[:100]),first)
        self.assertIsNotNone(first["1"]["half_width"])
        self.assertIsNotNone(first["12"]["half_width"])
        self.assertGreaterEqual(first["1"]["calibration_n"],20)
        self.assertEqual(first["12"]["calibration_n"],29)
        self.assertTrue(all(i["diagnostic_only"] for i in first.values()))

    def test_short_calibration_explicitly_withholds_bounds(self):
        c=calibrate_intervals([100.]*60)
        self.assertIsNone(c["1"]["half_width"])
        self.assertEqual(c["1"]["calibration_n"],0)
        self.assertIsNone(c["12"]["half_width"])
        with self.assertRaises(ForecastError):
            calibrate_intervals([100.]*100,alpha=0)

    def test_diagnostic_package_has_lineage_origin_horizons_and_no_2030(self):
        history=fixtures(140)
        p=forecast_package(history,origin_month="2021-08",
                           origin_at="2021-09-20T00:00:00Z",source=source())
        self.assertEqual(p["type"],"forecast_diagnostic_not_official_observation")
        self.assertEqual(p["model_id"],MODEL_ID)
        self.assertEqual(p["model_version"],MODEL_VERSION)
        self.assertEqual(p["scenario_id"],"baseline_unadjusted")
        self.assertEqual(p["observed_end_month"],"2021-08")
        self.assertEqual(p["training_months"],140)
        self.assertEqual(len(p["forecast_months"]),12)
        self.assertEqual(p["forecast_months"][0]["target_month"],"2021-09")
        self.assertEqual(p["forecast_months"][-1]["target_month"],"2022-08")
        self.assertEqual(p["source"]["raw_sha256"],"b"*64)
        self.assertEqual(p["source"]["acquisition_id"],"synthetic-acquisition")
        self.assertFalse(p["publication_approved"])
        self.assertFalse(p["model_release_gate"]["approved"])
        self.assertFalse(p["official_source_certified"])
        self.assertEqual(p["long_horizon_2030"]["status"],"withheld")
        self.assertTrue(p["forecast_months"][0]["lower"] is not None)
        self.assertLessEqual(p["forecast_months"][0]["lower"],
                             p["forecast_months"][0]["index_projection"])
        self.assertGreaterEqual(p["forecast_months"][0]["upper"],
                                p["forecast_months"][0]["index_projection"])

    def test_diagnostic_package_short_training_discloses_no_intervals(self):
        p=forecast_package(fixtures(64),origin_month="2015-04",
                           origin_at="2015-05-20T00:00:00Z",source=source())
        self.assertEqual(p["training_months"],64)
        self.assertTrue(all(item["lower"] is None and item["upper"] is None
                            for item in p["forecast_months"]))

    def test_exact_package_reproducibility_and_source_fingerprint_changes(self):
        h=fixtures(120)
        kw={"origin_month":"2019-12","origin_at":"2020-01-20T00:00:00Z",
            "source":source()}
        first=forecast_package(h,**kw)
        second=forecast_package(h,**kw)
        self.assertEqual(first,second)
        self.assertEqual(len(first["forecast_input_sha256"]),64)
        revised=list(h)
        last=revised[-1]
        revised[-1]=Observation(last.month,last.value+1,last.available_at,last.source_vintage)
        self.assertNotEqual(first["forecast_input_sha256"],
                            forecast_package(revised,**kw)["forecast_input_sha256"])

    def test_prevent_future_revision_and_unreleased_observation_leakage(self):
        h=fixtures(140,future_revision=True)
        current=forecast_package(h,origin_month="2020-01",
                                 origin_at="2020-02-20T00:00:00Z",source=source())
        original=fixtures(140)
        clean=forecast_package(original,origin_month="2020-01",
                               origin_at="2020-02-20T00:00:00Z",source=source())
        self.assertEqual(current["forecast_months"],clean["forecast_months"])
        self.assertNotEqual(current["forecast_input_sha256"],clean["forecast_input_sha256"])
        with self.assertRaises(ForecastError):
            forecast_package(fixtures(80,future_release_at=50),origin_month="2016-08",
                             origin_at="2016-09-20T00:00:00Z",source=source())

    def test_invalid_source_and_real_certification_claims_are_rejected(self):
        h=fixtures(100)
        for bad in [
            {"dataset_id":"sts_inpr_m"},
            {"industry_code":"28"},
            {"geo":"FR"},
            {"adjustment":"unknown"},
            {"raw_sha256":"not_sha"},
            {"official_source_certified":True},
        ]:
            values=source()
            values.update(bad)
            with self.subTest(bad=bad),self.assertRaises(ForecastError):
                forecast_package(h,origin_month="2018-04",
                                 origin_at="2018-05-20T00:00:00Z",source=values)

    def test_unavailable_training_and_missing_months_block_model(self):
        h=fixtures(120,missing_at=50)
        with self.assertRaises(ForecastError):
            forecast_package(h,origin_month="2019-12",
                             origin_at="2020-01-20T00:00:00Z",source=source())
        h=fixtures(120)
        h.pop(55)
        with self.assertRaises(ForecastError):
            forecast_package(h,origin_month="2019-12",
                             origin_at="2020-01-20T00:00:00Z",source=source())

    def test_rolling_origin_candidate_uses_exactly_benchmark_methods_and_dates(self):
        h=fixtures(170)
        evaluation=evaluate_candidate(h,origins(), "2026-01-01T00:00:00Z",
                                      final_holdout_start="2023-01")
        self.assertEqual(evaluation["origin_count"],24)
        self.assertEqual(set(evaluation["metrics"]),{"candidate","last_value",
                         "seasonal_naive","drift"})
        for horizon in (1,3,6,12):
            c=evaluation["metrics"]["candidate"][str(horizon)]
            b=evaluation["metrics"]["seasonal_naive"][str(horizon)]
            self.assertEqual(c["n"],b["n"])
            self.assertEqual(c["n"],24)
            self.assertTrue(math.isfinite(c["mae"]))
        for row in evaluation["predictions"]:
            self.assertLessEqual(row["information_max_available_at"],row["origin_at"])
            self.assertLess(row["target"],"2023-01")
        self.assertFalse(evaluation["superiority_claim_permitted"])
        self.assertFalse(evaluation["publication_approved"])

    def test_locked_holdout_blocks_targets_and_reports_reason(self):
        h=fixtures(170)
        result=evaluate_candidate(h,origins("2022-01",24),
                                  "2026-01-01T00:00:00Z",final_holdout_start="2023-01")
        self.assertTrue(any(e["reason"]=="Locked final 24-month holdout."
                            for e in result["excluded"]))
        self.assertTrue(all(p["target"]<"2023-01" for p in result["predictions"]))

    def test_stability_sample_counts_uncertainty_and_baseline_fallback(self):
        out=evaluate_candidate(fixtures(170),origins(), "2026-01-01T00:00:00Z",
                               final_holdout_start="2023-01")
        for horizon in (1,3,6,12):
            m=out["metrics"]["candidate"][str(horizon)]
            self.assertIsNotNone(m["early_mae"])
            self.assertIsNotNone(m["late_mae"])
            self.assertTrue(math.isfinite(m["bias"]))
            self.assertEqual(m["n"],24)
        decision=predeclared_gate(out)
        self.assertFalse(decision["approved"])
        self.assertEqual(decision["mode"],"benchmark_only")
        self.assertIn("vintages",decision["reason"])

    def test_no_unverified_model_can_pass_by_spoofing_evidence(self):
        out=evaluate_candidate(fixtures(170),origins(), "2026-01-01T00:00:00Z",
                               final_holdout_start="2023-01")
        out["history_evidence"]="official_independently_certified"
        self.assertFalse(predeclared_gate(out)["approved"])
        self.assertEqual(predeclared_gate(out)["mode"],"benchmark_only")

    def test_reject_origin_after_scoring_cutoff(self):
        with self.assertRaises(ForecastError):
            evaluate_candidate(fixtures(170),origins("2023-01",24),
                               "2023-05-01T00:00:00Z",
                               final_holdout_start="2025-01")


if __name__=="__main__":
    unittest.main()
