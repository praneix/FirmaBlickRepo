"""Offline Issue #10 normalization, statistical integrity and quarantine checks.

All values are synthetic official-FORMAT fixtures, never published Destatis data.
"""
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from ingestion.genesis import BASE_URL
from ingestion.normalize import (normalize_event, normalize_pair,
                                 run_quality_gate, QualityError, validated_profile)
from ingestion.snapshot_store import SnapshotStore
from test_genesis import fixture_zip, status_response


def profile(*, adjustment="original", quality_map=None, base=2021,
            confirmed=True, selector="ORIG"):
    return {
        "value_variable_code": "PRODIDX",
        "adjustment_variable_code": "AJUST",
        "adjustment_attribute_code": selector,
        "adjustment": adjustment,
        "expected_base_year": base,
        "quality_map": quality_map if quality_map is not None else {
            "": {"observation_type": "official",
                 "source_status_flags": [], "missing_reason": None},
            "p": {"observation_type": "provisional",
                  "source_status_flags": ["provisional"], "missing_reason": None},
            "s": {"observation_type": "official",
                  "source_status_flags": ["suppressed"], "missing_reason": "suppressed"},
        },
        "confirmed_against_official_metadata": confirmed,
    }


def altered_zip(raw, editor):
    with ZipFile(io.BytesIO(raw)) as zf:
        filename = zf.namelist()[0]
        original = zf.read(filename).decode("utf-8")
    modified = editor(original)
    buf = io.BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        zf.writestr(filename, modified.encode("utf-8"))
    return buf.getvalue()


def make_event(store, table, *, archive=None):
    raw = archive if archive is not None else fixture_zip(table)
    return store.archive(
        dataset_id=table, archive=raw, metadata=status_response(),
        source_url=BASE_URL,
        request={"name": table, "startyear": 2021, "endyear": 2026, "format": "ffcsv"},
        http={"tablefile": {"http_status": 200, "content_type": "application/zip"},
              "metadata": {"http_status": 200, "content_type": "application/json"}},
        inventory={"table": table, "covered_codes":
                   ["C"] if table == "42153-0001" else ["20", "24", "28", "29"],
                   "reported_index_base_year": 2021, "published_observations": False},
    )


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SnapshotStore(Path(self.temp.name) / "firmablick-only")

    def source(self, table="42153-0002", *, archive=None):
        make_event(self.store, table, archive=archive)
        return self.store.latest(table)

    def both(self):
        self.source("42153-0001")
        self.source("42153-0002")

    def test_exact_decimal_values_and_raw_cell_lineage(self):
        event = self.source()
        result = normalize_event(self.store, event, profile())
        self.assertEqual(len(result), 4)
        by_code = {x["observation"]["industry_code"]: x for x in result}
        self.assertEqual(set(by_code), {"20", "24", "28", "29"})
        self.assertEqual(by_code["20"]["observation"]["value"], 90.5)
        self.assertEqual(by_code["28"]["lineage"]["raw_decimal"], "92.5")
        self.assertEqual(
            Decimal(by_code["28"]["lineage"]["raw_decimal"]),
            Decimal(str(by_code["28"]["observation"]["value"])))
        self.assertEqual(by_code["29"]["observation"]["observation_type"], "provisional")
        self.assertEqual(by_code["29"]["observation"]["source_status_flags"], ["provisional"])
        self.assertEqual(by_code["20"]["lineage"]["raw_csv_column"], "value")
        self.assertEqual(by_code["20"]["lineage"]["raw_csv_row"], 2)
        self.assertEqual(by_code["20"]["lineage"]["metadata_sha256"],
                         event["objects"]["metadata.json"])
        self.assertEqual(by_code["20"]["observation"]["raw_sha256"],
                         event["objects"]["tablefile.zip"])
        self.assertEqual(by_code["20"]["observation"]["raw_snapshot_id"],
                         event["acquisition_id"])
        self.assertIn("transformation_version", by_code["20"]["lineage"])
        self.assertTrue(all(x["observation"]["adjustment"] == "original" for x in result))

    def test_cross_table_complete_validated_but_never_published(self):
        self.both()
        outcome = run_quality_gate(self.store, {"42153-0001": profile(),
                                                 "42153-0002": profile()})
        self.assertEqual(outcome["status"], "VALIDATED_UNPUBLISHED")
        self.assertFalse(outcome["publication_approved"])
        result = json.loads(Path(outcome["path"]).read_text())
        self.assertEqual(result["observation_count"], 5)
        self.assertEqual(len(result["results"]), 5)
        self.assertFalse(result["publication_approved"])
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_identical_run_rerunnable_without_changing_source(self):
        self.both()
        profiles = {"42153-0001": profile(), "42153-0002": profile()}
        one = run_quality_gate(self.store, profiles)
        two = run_quality_gate(self.store, profiles)
        self.assertNotEqual(one["run_id"], two["run_id"])
        self.assertEqual(one["observation_count"], two["observation_count"])
        self.assertEqual(
            json.loads(Path(one["path"]).read_text())["results"],
            json.loads(Path(two["path"]).read_text())["results"])
        self.assertEqual(self.store.metrics()["acquisition_events"], 2)

    def test_missing_sector_quarantines_without_partial_output(self):
        self.source("42153-0001")
        self.source("42153-0002", archive=fixture_zip("42153-0002", missing=["24"]))
        result = run_quality_gate(self.store, {"42153-0001": profile(),
                                               "42153-0002": profile()})
        self.assertEqual(result["status"], "QUARANTINED")
        self.assertEqual(result["reason_code"], "SECTOR_COVERAGE")
        self.assertFalse(result["publication_approved"])
        self.assertEqual(list((self.store.base / "quality" / "validated").glob("*.json")), []
                         if (self.store.base / "quality" / "validated").exists() else [])

    def test_duplicate_period_series_quarantines(self):
        original = fixture_zip("42153-0002")
        duplicated = altered_zip(original, lambda text: text + text.splitlines(True)[1])
        event = self.source(archive=duplicated)
        with self.assertRaisesRegex(QualityError, "Duplicate"):
            normalize_event(self.store, event, profile())

    def test_unverified_metadata_profile_quarantined(self):
        self.both()
        result = run_quality_gate(self.store, {"42153-0001": profile(confirmed=False),
                                               "42153-0002": profile()})
        self.assertEqual(result["reason_code"], "PROFILE_UNVERIFIED")

    def test_conflicting_base_year_quarantines(self):
        self.source("42153-0001")
        self.source("42153-0002", archive=fixture_zip("42153-0002", inconsistent_base=True))
        result = run_quality_gate(self.store, {"42153-0001": profile(),
                                               "42153-0002": profile()})
        self.assertEqual(result["reason_code"], "BASE_CONFLICT")

    def test_missing_value_cannot_be_silently_zero(self):
        original = fixture_zip("42153-0002")
        modified = altered_zip(original, lambda text: text.replace("90,5;2021=100", ".;2021=100"))
        event = self.source(archive=modified)
        with self.assertRaises(QualityError) as ctx:
            normalize_event(self.store, event, profile())
        self.assertEqual(ctx.exception.code, "MISSING_UNMAPPED")

        # Replace a source row with an explicit recognized suppression indicator.
        suppressed = altered_zip(modified, lambda text: text.replace(
            ".;2021=100;PRODIDX;Production index;",
            ".;2021=100;PRODIDX;Production index;s", 1))
        event2 = self.source(archive=suppressed)
        rows = normalize_event(self.store, event2, profile())
        obs = next(x["observation"] for x in rows if x["observation"]["industry_code"] == "20")
        self.assertIsNone(obs["value"])
        self.assertEqual(obs["missing_reason"], "suppressed")
        self.assertEqual(obs["source_status_flags"], ["suppressed"])

    def test_unrecognized_quality_is_quarantined(self):
        text = altered_zip(fixture_zip("42153-0002"), lambda src: src.replace(
            "90,5;2021=100;PRODIDX;Production index;",
            "90,5;2021=100;PRODIDX;Production index;z", 1))
        event = self.source(archive=text)
        with self.assertRaises(QualityError) as ctx:
            normalize_event(self.store, event, profile())
        self.assertEqual(ctx.exception.code, "STATUS_UNKNOWN")

    def test_adjustment_selector_unknown_or_mixed_blocks(self):
        self.both()
        bad = run_quality_gate(self.store, {"42153-0001": profile(),
                                            "42153-0002": profile(
                                                adjustment="seasonally_adjusted")})
        self.assertEqual(bad["reason_code"], "ADJUSTMENT_CONFLICT")
        no_series = run_quality_gate(self.store, {"42153-0001": profile(),
                                                  "42153-0002": profile(selector="SA")})
        self.assertEqual(no_series["reason_code"], "SELECTED_COVERAGE")

    def test_corrupted_object_quarantines(self):
        event = self.source()
        digest = event["objects"]["tablefile.zip"]
        self.store._object_path(digest).write_bytes(b"tampered")
        self.source("42153-0001")
        result = run_quality_gate(self.store, {"42153-0001": profile(),
                                               "42153-0002": profile()})
        self.assertEqual(result["status"], "QUARANTINED")
        self.assertEqual(result["reason_code"], "SOURCE_INTEGRITY")

    def test_invalid_csv_source_month_quarantines(self):
        raw = altered_zip(fixture_zip("42153-0002"), lambda txt: txt.replace(
            "2026-01", "2026-13", 1))
        event = self.source(archive=raw)
        with self.assertRaises(QualityError) as ctx:
            normalize_event(self.store, event, profile())
        self.assertEqual(ctx.exception.code, "PERIOD_INVALID")

    def test_source_snapshot_unchanged_by_validation(self):
        self.both()
        before = [self.store.latest(t)["objects"].copy() for t in
                  ("42153-0001", "42153-0002")]
        run_quality_gate(self.store, {"42153-0001": profile(),
                                      "42153-0002": profile()})
        after = [self.store.latest(t)["objects"].copy() for t in
                 ("42153-0001", "42153-0002")]
        self.assertEqual(before, after)
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_quality_results_are_append_only(self):
        self.both()
        options = {"42153-0001": profile(), "42153-0002": profile()}
        first = run_quality_gate(self.store, options)
        self.assertEqual(first["status"], "VALIDATED_UNPUBLISHED")
        filename = Path(first["path"])
        self.assertTrue(filename.is_file())
        self.assertEqual(filename.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.store.base / "quality" / "validated").stat().st_mode & 0o777,
                         0o700)
        self.assertEqual(first["path"], str(filename))
        with self.assertRaises(QualityError):
            # Reusing the same immutable result filename is refused.
            from ingestion.normalize import _write_exclusive_json
            _write_exclusive_json(filename.parent, filename.name, {"changed": True})

    def test_source_contract_fields_and_lineage_identity(self):
        self.both()
        output = normalize_pair(self.store, {"42153-0001": profile(),
                                              "42153-0002": profile()})
        schema = json.loads((Path(__file__).parent.parent /
                             "data-contracts/industrial-observation.v1.schema.json").read_text())
        for row in output:
            obs = row["observation"]
            self.assertTrue(set(schema["required"]) <= set(obs))
            self.assertTrue(set(obs) <= set(schema["properties"]))
            self.assertEqual(obs["source_id"], "destatis")
            self.assertEqual(obs["classification_revision"], "WZ2008")
            self.assertEqual(obs["raw_sha256"], row["lineage"]["raw_sha256"])
            self.assertEqual(obs["raw_snapshot_id"], row["lineage"]["acquisition_id"])


if __name__ == "__main__":
    unittest.main()
