"""Regression against the *shape* of authenticated GENESIS 42153 FFCsv observed 2026-11-20.

All numerical examples below are synthetic, with actual GENESIS column and
dimensional code syntax. No sampled official values are asserted in these tests.
"""
import csv
import io
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from ingestion.genesis import BASE_URL
from ingestion.normalize import (normalize_event,normalize_pair,run_quality_gate,QualityError)
from ingestion.snapshot_store import SnapshotStore
from test_genesis import status_response

HEADER=[
 "statistics_code","statistics_label","time_code","time_label","time",
 "1_variable_code","1_variable_label","1_variable_attribute_code","1_variable_attribute_label",
 "2_variable_code","2_variable_label","2_variable_attribute_code","2_variable_attribute_label",
 "3_variable_code","3_variable_label","3_variable_attribute_code","3_variable_attribute_label",
 "4_variable_code","4_variable_label","4_variable_attribute_code","4_variable_attribute_label",
 "value","value_unit","value_variable_code","value_variable_label"
]
CODES={"42153-0001":["C"],"42153-0002":["20","24","28","29"]}


def fixture(table,*,invalid_month=False,missing_quality=False):
    memory=io.StringIO(newline="")
    writer=csv.DictWriter(memory,fieldnames=HEADER,delimiter=";",lineterminator="\n")
    writer.writeheader()
    for code in CODES[table]:
        for month in [1,2]:
            for adj in ["WERTORG","X13JDKSB"]:
                r=dict.fromkeys(HEADER,"")
                r.update(statistics_code="42153",statistics_label="Synthetic demo",
                    time_code="JAHR",time_label="Jahr",time="2024",
                    value_variable_code="PRO101",value_variable_label="Produktionsindex",
                    value_unit="2021=100",value=f"{90+month},5",
                    **{
                        "1_variable_code":"MONAT","1_variable_label":"Monate",
                        "1_variable_attribute_code":f"MONAT{month:02d}",
                        "1_variable_attribute_label":"synthetic month",
                        "2_variable_code":"DINSG","2_variable_label":"Deutschland",
                        "2_variable_attribute_code":"DG","2_variable_attribute_label":"Deutschland",
                        "3_variable_code":"WERT03","3_variable_label":"Original- und bereinigte Daten",
                        "3_variable_attribute_code":adj,"3_variable_attribute_label":"synthetic adjustment",
                        "4_variable_code":"WZ08V1" if code=="C" else "WZ08V2",
                        "4_variable_label":"WZ 2008","4_variable_attribute_code":f"WZ08-{code}",
                        "4_variable_attribute_label":"Synthetic industry",
                    })
                if invalid_month and month==2 and code==CODES[table][0] and adj=="WERTORG":
                    r["1_variable_attribute_code"]="MONAT13"
                writer.writerow(r)
    output=io.BytesIO()
    with ZipFile(output,"w",ZIP_DEFLATED) as z:
        z.writestr("genesis.csv",memory.getvalue().encode("utf-8"))
    return output.getvalue()


def profile():
    return {"value_variable_code":"PRO101","adjustment_variable_code":"WERT03",
            "adjustment_attribute_code":"WERTORG","adjustment":"original",
            "expected_base_year":2021,
            "quality_map":{"":{"observation_type":"official",
               "source_status_flags":[],"missing_reason":None}},
            "confirmed_against_official_metadata":True}


def archive(store,table,data=None):
    store.archive(dataset_id=table,archive=data or fixture(table),
      metadata=status_response(),source_url=BASE_URL,
      request={"name":table,"startyear":2024,"endyear":2026,"format":"ffcsv"},
      http={"metadata":{"http_status":200},"tablefile":{"http_status":200}},
      inventory={"table":table,"covered_codes":CODES[table],
                 "reported_index_base_year":2021,"published_observations":False})
    return store.latest(table)


class OfficialShapeNormalization(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=SnapshotStore(Path(self.tmp.name)/"snapshots")

    def test_current_genesis_csv_year_month_and_missing_quality_columns(self):
        for table in CODES:
            event=archive(self.store,table)
            result=normalize_event(self.store,event,profile())
            self.assertEqual(len(result),2*len(CODES[table]))
            self.assertEqual(set(x["observation"]["period"] for x in result),{"2024-01","2024-02"})
            self.assertEqual(set(x["observation"]["industry_code"] for x in result),
                             set(CODES[table]))
            for x in result:
                self.assertEqual(x["observation"]["base_year"],2021)
                self.assertEqual(x["observation"]["adjustment"],"original")
                self.assertEqual(x["observation"]["source_status_flags"],
                                 ["source_quality_field_not_provided"])
                self.assertEqual(x["observation"]["original_dimensions"]["time_code"],"JAHR")
                self.assertEqual(x["observation"]["original_dimensions"]["raw_time"],"2024")
                self.assertEqual(x["observation"]["original_dimensions"]["quality"],"not_provided")
                self.assertEqual(x["lineage"]["raw_csv_column"],"value")
                self.assertEqual(x["observation"]["raw_sha256"],event["objects"]["tablefile.zip"])

    def test_complete_pair_can_be_validated_but_never_published(self):
        for table in CODES:archive(self.store,table)
        result=run_quality_gate(self.store,{table:profile() for table in CODES})
        self.assertEqual(result["status"],"VALIDATED_UNPUBLISHED")
        self.assertEqual(result["observation_count"],10)
        self.assertIs(result["publication_approved"],False)
        self.assertEqual(self.store.metrics()["published"],0)

    def test_unknown_month_dimension_is_quarantined(self):
        archive(self.store,"42153-0001")
        archive(self.store,"42153-0002",fixture("42153-0002",invalid_month=True))
        result=run_quality_gate(self.store,{table:profile() for table in CODES})
        self.assertEqual(result["status"],"QUARANTINED")
        self.assertEqual(result["reason_code"],"PERIOD_INVALID")

    def test_provisional_status_cannot_be_invented_from_absent_quality_column(self):
        event=archive(self.store,"42153-0001")
        p=profile()
        p["quality_map"][""]={"observation_type":"provisional",
                              "source_status_flags":["provisional"],"missing_reason":None}
        with self.assertRaises(QualityError) as ctx:
            normalize_event(self.store,event,p)
        self.assertEqual(ctx.exception.code,"STATUS_UNDOCUMENTED")


if __name__=="__main__":unittest.main()
