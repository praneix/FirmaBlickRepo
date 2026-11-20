"""Eurostat official-format JSON-stat fixtures. Values are synthetic, not published."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from ingestion.eurostat import (
    EurostatArchive, EurostatError, fetch, normalize, reconcile,
    validate_jsonstat, flat_index
)

IDS=["freq","indic_bt","nace_r2","s_adj","unit","geo","time"]
CATS={
    "freq":["M"],"indic_bt":["PRD"],"nace_r2":["C","C20","C24","C28","C29"],
    "s_adj":["NSA","SCA"],"unit":["I21"],"geo":["DE"],"time":["2026-01","2026-02"],
}


def fixture(*, dims=None, values=None, statuses=None, unit="I21"):
    src={k:v[:] for k,v in (dims or CATS).items()}
    src["unit"]=[unit]
    total=1
    for key in IDS:total*=len(src[key])
    return {
        "version":"2.0","class":"dataset",
        "source":"ESTAT","updated":"2026-11-20T00:00:00+0100",
        "id":IDS[:],"size":[len(src[k]) for k in IDS],
        "dimension":{k:{"label":k,"category":{
            "index":{c:i for i,c in enumerate(src[k])},
            "label":{c:c for c in src[k]}}} for k in IDS},
        "value":values if values is not None else {str(i):90.0+(i/10) for i in range(total)},
        "status":statuses if statuses is not None else {"0":"p"}
    }


def sample_primary(*, code="28", value=91.2, base=2021, adjustment="original",
                   period="2026-01", classification="WZ2008", geo="DE"):
    return {"observation":{"source_id":"destatis","dataset_id":"42153-0002",
            "industry_code":code,"period":period,"value":value,"geo":geo,
            "frequency":"M","unit":"index","base_year":base,
            "adjustment":adjustment,"classification_revision":classification,
            "raw_snapshot_id":"genesis-synthetic-acquisition"}}


class FakeHTTP:
    def __init__(self, raw):
        self.raw=raw; self.status=200
        self.headers={"Content-Type":"application/json","ETag":'"fixture"'}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.raw[:n]


class EurostatTests(unittest.TestCase):
    def test_discover_dimensions_and_json_stat_sparse_index(self):
        payload=fixture()
        ids,sizes,cats,size=validate_jsonstat(payload)
        self.assertEqual(ids,IDS)
        self.assertEqual(size,20)
        self.assertEqual(flat_index(ids,sizes,cats,{
            "freq":"M","indic_bt":"PRD","nace_r2":"C28","s_adj":"NSA",
            "unit":"I21","geo":"DE","time":"2026-01"}),12)

    def test_normalize_all_five_industries_and_preserve_status(self):
        rows=normalize(fixture())
        self.assertEqual(len(rows),20)
        self.assertEqual({r["industry_code"] for r in rows},{"C","C20","C24","C28","C29"})
        self.assertEqual({r["adjustment"] for r in rows},{"original","seasonal_calendar_adjusted"})
        self.assertEqual({r["base_year"] for r in rows},{2021})
        self.assertEqual(rows[0]["source_status_flags"],["p"])
        self.assertEqual(rows[0]["raw_dimensions"]["geo"],"DE")
        self.assertEqual(rows[0]["source_cell_index"],0)
        self.assertEqual(rows[0]["value"],90.0)

    def test_jsonstat_list_and_empty_missing_values(self):
        payload=fixture(values=[None]+[91.5]*19,statuses=["c"]+[None]*19)
        rows=normalize(payload)
        self.assertIsNone(rows[0]["value"])
        self.assertEqual(rows[0]["source_status_flags"],["c"])
        self.assertEqual(rows[1]["value"],91.5)

    def test_reject_malformed_dimension_and_cell_types(self):
        p=fixture();p["id"].append("not-real")
        with self.assertRaises(EurostatError):normalize(p)
        p=fixture();p["size"][2]=1
        with self.assertRaises(EurostatError):normalize(p)
        p=fixture(values={"0":"91.1"})
        with self.assertRaises(EurostatError):normalize(p)
        p=fixture(statuses={"0":12})
        with self.assertRaises(EurostatError):normalize(p)

    def test_explicit_rev21_conversion_is_blocked(self):
        with self.assertRaisesRegex(EurostatError,"conversion not approved"):
            normalize(fixture(),classification="NACE_REV2_1")

    def test_reject_wrong_indicator_and_unsupported_index_unit(self):
        p=fixture(dims={**CATS,"indic_bt":["TOVT"]})
        with self.assertRaisesRegex(EurostatError,"category missing"):
            normalize(p)
        p=fixture(unit="MIO_EUR")
        with self.assertRaisesRegex(EurostatError,"No recognised"):
            normalize(p)

    def test_fetch_exact_scoped_public_request_and_preserves_raw(self):
        seen=[]
        raw=json.dumps(fixture()).encode()
        def fake(request, timeout):
            seen.append(request.full_url)
            return FakeHTTP(raw)
        source,http,query=fetch(transport=fake)
        self.assertEqual(source,raw)
        self.assertEqual(http["http_status"],200)
        self.assertIn("geo=DE",seen[0])
        self.assertEqual(query["indic_bt"],"PRD")
        with self.assertRaises(EurostatError):
            fetch(transport=fake,params={"geo":"FR"})

    def test_archive_dedup_revision_vintage_and_asof(self):
        with tempfile.TemporaryDirectory() as temp:
            arc=EurostatArchive(temp)
            params={"geo":"DE","freq":"M","indic_bt":"PRD","lang":"EN"}
            raw=json.dumps(fixture()).encode()
            a=arc.archive(raw,{"http_status":200},params,received="2026-11-20T02:00:00Z")
            b=arc.archive(raw,{"http_status":200},params,received="2026-11-20T02:01:00Z")
            self.assertEqual(a["raw_sha256"],b["raw_sha256"])
            self.assertNotEqual(a["acquisition_id"],b["acquisition_id"])
            self.assertEqual(len(list(arc.blobs.iterdir())),1)
            changed=fixture();changed["value"]["0"]=110.0
            c=arc.archive(json.dumps(changed).encode(),{"http_status":200},params,
                          received="2026-11-20T02:02:00Z")
            self.assertEqual(len(list(arc.blobs.iterdir())),2)
            self.assertEqual(len(arc.events()),3)
            self.assertEqual(len(arc.events(as_of="2026-11-20T02:00:00Z")),1)
            self.assertEqual(arc.events()[0]["acquisition_id"],c["acquisition_id"])
            self.assertFalse(any(x["publication_approved"] for x in arc.events()))

    def test_archive_integrity_tampering_blocks_asof(self):
        with tempfile.TemporaryDirectory() as temp:
            arc=EurostatArchive(temp);raw=json.dumps(fixture()).encode()
            a=arc.archive(raw,{"http_status":200},
                          {"geo":"DE","freq":"M","indic_bt":"PRD"})
            (arc.blobs/a["raw_sha256"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(EurostatError,"digest mismatch"):
                arc.events()

    def test_reconcile_matching_and_tolerance_without_overwrite(self):
        rows=normalize(fixture())
        e=next(x for x in rows if x["industry_code"]=="C28" and x["period"]=="2026-01"
               and x["adjustment"]=="original")
        primary=[sample_primary(value=e["value"])]
        same=reconcile(primary,[e],mapping_verified=True)
        self.assertEqual(same["summary"],{"compared":1,"excluded":0,"deviations":0})
        self.assertEqual(same["compared"][0]["assessment"],"exact")
        changed={**e,"value":e["value"]+0.1}
        close=reconcile(primary,[changed],mapping_verified=True)
        self.assertEqual(close["compared"][0]["assessment"],"within_tolerance")
        far=reconcile(primary,[{**e,"value":e["value"]+2.0}],mapping_verified=True)
        self.assertEqual(far["compared"][0]["assessment"],"deviation")
        self.assertEqual(primary[0]["observation"]["value"],e["value"])

    def test_reconcile_rejects_mixed_basis_adjustment_classification_geography(self):
        e=next(x for x in normalize(fixture()) if x["industry_code"]=="C28"
               and x["period"]=="2026-01" and x["adjustment"]=="original")
        baseline=sample_primary(value=e["value"])
        for change,reason in [
            ({"base_year":2025},"index_unit_or_base_mismatch"),
            ({"adjustment":"seasonally_adjusted"},"adjustment_mismatch"),
            ({"classification_revision":"NACE_REV2_1"},"classification_mapping_not_verified"),
            ({"geo":"FR"},"geography_or_frequency_mismatch"),
        ]:
            report=reconcile([baseline],[{**e,**change}],mapping_verified=True)
            self.assertEqual(report["summary"]["compared"],0)
            self.assertEqual(report["excluded"][0]["reason"],reason)
        self.assertFalse(reconcile([baseline],[])["publication_approved"])

    def test_reconciliation_requires_confirmed_crosswalk(self):
        e=next(x for x in normalize(fixture()) if x["industry_code"]=="C28"
               and x["period"]=="2026-01" and x["adjustment"]=="original")
        d=sample_primary(value=e["value"])
        unapproved=reconcile([d],[e])
        self.assertEqual(unapproved["summary"]["compared"],0)
        self.assertEqual(unapproved["excluded"][0]["reason"],"classification_mapping_not_verified")
        self.assertFalse(unapproved["classification_mapping_verified"])
        approved=reconcile([d],[e],mapping_verified=True)
        self.assertEqual(approved["summary"]["compared"],1)
        self.assertTrue(approved["classification_mapping_verified"])

    def test_ambiguous_duplicate_comparator_is_not_silently_selected(self):
        e=next(x for x in normalize(fixture()) if x["industry_code"]=="C28"
               and x["period"]=="2026-01" and x["adjustment"]=="original")
        result=reconcile([sample_primary(value=e["value"])],[e,{**e,"value":e["value"]+2}],
                         mapping_verified=True)
        self.assertEqual(result["summary"]["compared"],0)
        self.assertEqual(result["excluded"][0]["reason"],"ambiguous_comparator_duplicate")

    def test_reconcile_missing_and_unmatched_period_reasons(self):
        e=next(x for x in normalize(fixture()) if x["industry_code"]=="C28"
               and x["period"]=="2026-01" and x["adjustment"]=="original")
        missing=reconcile([sample_primary(value=None)],[e],mapping_verified=True)
        self.assertEqual(missing["excluded"][0]["reason"],"missing_observation")
        unmatched=reconcile([sample_primary(period="2025-01")],[e],mapping_verified=True)
        self.assertEqual({x["reason"] for x in unmatched["excluded"]},
                         {"missing_comparator","missing_primary"})


if __name__=="__main__":
    unittest.main()
