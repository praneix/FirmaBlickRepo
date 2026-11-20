"""Issue #16: independent synthetic sector model/lineage/release safeguards."""
import copy
import hashlib
import math
import unittest
from forecast.benchmarks import Observation, _month_number, _month_string
from forecast.sectors import (
    SECTOR_ORDER,SECTOR_NAMES,SECTOR_MODEL_VERSIONS,SECTOR_MODELS,
    _shock_diagnostics,evaluate_sector,evaluate_portfolio,
)


def synthetic(code,*,n=180,shock=False,missing=None,late=None,revision=False):
    base=_month_number("2010-01")
    out=[]
    offset={"28":0.7,"29":2.0,"24":4.0,"20":6.0}[code]
    for i in range(n):
        month=_month_string(base+i)
        after=_month_string(base+i+1)
        level=95+offset+(i%12)*0.35+i*0.04
        if shock and i>=113:level*=0.62
        if missing==i:level=None
        available=after+"-16T00:00:00Z"
        if late==i:available="2040-01-01T00:00:00Z"
        out.append(Observation(month,level,available,"synthetic-"+code+"-"+str(i)))
        if revision and i==45:
            out.append(Observation(month,level+12,"2028-01-01T00:00:00Z",
                                   "future-revision-"+code))
    return out


def source(code,**changes):
    s={"dataset_id":"42153-0002","industry_code":code,"geo":"DE","frequency":"M",
       "unit":"index","base_year":2021,"adjustment":"original",
       "classification_revision":"WZ2008","raw_sha256":hashlib.sha256(code.encode()).hexdigest(),
       "acquisition_id":"synthetic-acquisition-"+code,"official_source_certified":False}
    s.update(changes)
    return s


def origins(*,first="2020-01",n=24):
    base=_month_number(first)
    return [{"month":_month_string(base+i),
             "available_at":_month_string(base+i+1)+"-20T00:00:00Z"}
            for i in range(n)]


def sector_payload(code,**kwargs):
    return {
        "history":synthetic(code,**kwargs),"source":source(code),
        "origins":origins(),"truth_cutoff":"2026-01-01T00:00:00Z",
        "holdout_start":"2024-01",
    }


class SectorTests(unittest.TestCase):
    def test_sector_order_and_unique_model_versions(self):
        self.assertEqual(SECTOR_ORDER,("28","29","24","20"))
        self.assertEqual(len(set(SECTOR_MODEL_VERSIONS.values())),4)
        self.assertEqual(len(set(SECTOR_MODELS.values())),4)
        self.assertEqual(len(SECTOR_NAMES),4)

    def test_independently_scored_all_four_remain_historical_only(self):
        p=evaluate_portfolio({c:sector_payload(c) for c in SECTOR_ORDER})
        self.assertEqual(p["evaluation_order"],list(SECTOR_ORDER))
        self.assertFalse(p["publication_approved"])
        self.assertFalse(p["aggregate_release_transfer_permitted"])
        self.assertFalse(p["official_source_certified"])
        self.assertEqual(p["user_visible_mode"],"historical_only")
        self.assertEqual(p["forecast_release_flags"],{c:False for c in SECTOR_ORDER})
        for s in p["sectors"]:
            self.assertFalse(s["release_approved"])
            self.assertFalse(s["public_forecast_available"])
            self.assertFalse(s["publication_approved"])
            self.assertEqual(s["forecast_months"],[])
            self.assertEqual(s["status"],"historical_only")
            self.assertEqual(s["diagnostic"]["eligible_origins"],24)
            for h in (1,3,6,12):
                self.assertEqual(s["diagnostic"]["metrics"]["candidate"][str(h)]["n"],24)
                self.assertEqual(s["diagnostic"]["metrics"]["seasonal_naive"][str(h)]["n"],24)
            self.assertEqual(len(s["candidate_diagnostic_not_released"]["index_projections"]),12)
            self.assertEqual(s["candidate_diagnostic_not_released"]["publication_approved"],False)

    def test_each_sector_has_independent_raw_source_and_model_identity(self):
        p=evaluate_portfolio({c:sector_payload(c) for c in SECTOR_ORDER})
        entries=p["sectors"]
        self.assertEqual(len({s["source"]["raw_sha256"] for s in entries}),4)
        self.assertEqual(len({s["forecast_input_sha256"] for s in entries}),4)
        self.assertEqual(len({s["model_version"] for s in entries}),4)
        for s in entries:
            self.assertEqual(s["source"]["industry_code"],s["industry_code"])
            self.assertEqual(s["source"]["dataset_id"],"42153-0002")
            self.assertEqual(s["diagnostic"]["publication_approved"],False)
            self.assertTrue(all(r["information_max_available_at"]<=r["origin_at"]
                                for r in s["diagnostic"]["predictions"]))

    def test_aggregate_approval_can_never_enable_sector_release(self):
        p={c:sector_payload(c) for c in SECTOR_ORDER}
        base=evaluate_portfolio(p,aggregate_approved=False)
        spoof=evaluate_portfolio(p,aggregate_approved=True)
        self.assertEqual(spoof["sectors"],base["sectors"])
        self.assertEqual(spoof["forecast_release_flags"],{c:False for c in SECTOR_ORDER})

    def test_one_bad_sector_does_not_contaminate_others(self):
        p={c:sector_payload(c) for c in SECTOR_ORDER}
        p["29"]["source"]["industry_code"]="28"
        result=evaluate_portfolio(p)
        lookup={s["industry_code"]:s for s in result["sectors"]}
        self.assertIsNone(lookup["29"]["diagnostic"])
        self.assertIn("Source mismatch",lookup["29"]["reason"])
        for code in ("28","24","20"):
            self.assertIsNotNone(lookup[code]["diagnostic"])
            self.assertEqual(lookup[code]["diagnostic"]["eligible_origins"],24)
        self.assertEqual(result["forecast_release_flags"]["29"],False)

    def test_absent_sector_has_historical_only_explanation(self):
        p=evaluate_portfolio({"28":sector_payload("28")})
        for s in p["sectors"][1:]:
            self.assertEqual(s["status"],"historical_only")
            self.assertIn("unavailable",s["reason"])
            self.assertIsNone(s["diagnostic"])

    def test_out_of_contract_geography_adjustment_vintage_and_auth_are_blocked(self):
        for delta in [
            {"geo":"AT"},{"dataset_id":"42153-0001"},{"base_year":2020.5},
            {"classification_revision":"NACE_REV2_1"},
            {"official_source_certified":True},{"raw_sha256":"invalid"},
            {"adjustment":"unknown"},
        ]:
            p=sector_payload("28")
            p["source"].update(delta)
            r=evaluate_portfolio({"28":p})["sectors"][0]
            self.assertIsNone(r["diagnostic"],delta)
            self.assertFalse(r["release_approved"])

    def test_late_source_revision_cannot_change_prior_diagnostic_fingerprint(self):
        original=sector_payload("28")
        future=copy.deepcopy(original)
        future["history"]=synthetic("28",revision=True)
        plain=evaluate_portfolio({"28":original})["sectors"][0]
        altered=evaluate_portfolio({"28":future})["sectors"][0]
        self.assertEqual(plain["forecast_input_sha256"],altered["forecast_input_sha256"])
        self.assertEqual(plain["diagnostic"]["metrics"],altered["diagnostic"]["metrics"])
        self.assertEqual(plain["candidate_diagnostic_not_released"],
                         altered["candidate_diagnostic_not_released"])

    def test_shocks_flag_regime_break_without_claiming_cause(self):
        r=evaluate_portfolio({"28":sector_payload("28",shock=True)})["sectors"][0]
        self.assertEqual(r["structural_breaks"]["status"],"descriptive_unvalidated")
        self.assertTrue(r["structural_breaks"]["has_shock_flags"])
        self.assertTrue(r["diagnostic"]["shock_history"])
        self.assertIn("unknown",r["structural_breaks"]["note"])
        self.assertFalse(r["release_approved"])

    def test_orders_feature_needs_independent_incremental_evidence(self):
        p=sector_payload("28")
        p["orders_indicator"]=[1,2,3]
        r=evaluate_portfolio({"28":p})["sectors"][0]
        self.assertIn("disabled",r["reason"])
        self.assertIsNone(r["diagnostic"])

    def test_missing_training_zero_imputation_and_unreleased_month_block(self):
        for key,val in (("missing",85),("late",85)):
            p=sector_payload("28",**{key:val})
            r=evaluate_portfolio({"28":p})["sectors"][0]
            self.assertFalse(r["public_forecast_available"])
            self.assertIsNone(r["diagnostic"])
            self.assertIn("Validation rejected",r["reason"])

    def test_missing_origin_and_holdout_rejected(self):
        p=sector_payload("28")
        p["origins"]=[]
        out=evaluate_portfolio({"28":p})["sectors"][0]
        self.assertEqual(out["status"],"historical_only")
        self.assertIsNone(out["diagnostic"])
        p=sector_payload("28")
        p["holdout_start"]="2020-01"
        out=evaluate_portfolio({"28":p})["sectors"][0]
        self.assertEqual(out["diagnostic"]["eligible_origins"],0)
        self.assertFalse(out["release_approved"])

    def test_predeclared_methods_and_holdout_are_source_specific(self):
        p=sector_payload("28")
        p["holdout_start"]="2021-05"
        r=evaluate_portfolio({"28":p})["sectors"][0]
        self.assertTrue(r["diagnostic"]["excluded"])
        self.assertTrue(all(z["target"]<"2021-05" for z in r["diagnostic"]["predictions"]))
        self.assertEqual(set(r["diagnostic"]["metrics"]),
                         {"candidate","last_value","seasonal_naive","drift"})
        self.assertTrue(all(z["target_vintage"].startswith("synthetic-28")
                            for z in r["diagnostic"]["predictions"]))

    def test_deterministic_same_source_reproduces_score_exactly(self):
        p={c:sector_payload(c) for c in SECTOR_ORDER}
        self.assertEqual(evaluate_portfolio(p),evaluate_portfolio(p))
        r=evaluate_portfolio({"28":sector_payload("28")})["sectors"][0]
        self.assertEqual(r["observed_end_month"],"2021-12")
        self.assertEqual(r["model_version"],"1.0.0-28")
        self.assertEqual(len(r["forecast_input_sha256"]),64)

    def test_unknown_sector_is_rejected_not_pooled(self):
        with self.assertRaises(Exception):
            evaluate_portfolio({"35":sector_payload("28")})
        from forecast.sectors import evaluate_sector
        with self.assertRaises(Exception):
            evaluate_sector("C",[],{},[],"2026-01-01T00:00:00Z",
                            holdout_start="2024-01")


if __name__=="__main__":
    unittest.main()
