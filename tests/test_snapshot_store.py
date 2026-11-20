"""Issue #9 local immutable acquisition archive contract and failure-injection tests."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ingestion.snapshot_store import (
    NAMESPACE, SnapshotError, SnapshotStore, require_utc_timestamp,
)
from ingestion.genesis import BASE_URL, GenesisError, acquire
from test_genesis import fixture_zip, status_response

FIRST = "2026-11-19T10:30:00Z"
LATER = "2026-11-19T10:30:01Z"


def inventory(table):
    codes = ["C"] if table == "42153-0001" else ["20", "24", "28", "29"]
    return {"table": table, "covered_codes": codes,
            "reported_index_base_year": 2021, "published_observations": False,
            "discovery_only": True}


def evidence(table="42153-0002", *, archive=None, metadata=None, stamp=FIRST):
    return dict(
        dataset_id=table,
        archive=archive if archive is not None else fixture_zip(table),
        metadata=metadata if metadata is not None else status_response(),
        source_url=BASE_URL,
        request={"name": table, "startyear": 2021, "endyear": 2026,
                 "format": "ffcsv", "language": "de"},
        http={"tablefile": {"http_status": 200,
                            "content_type": "application/zip",
                            "source_etag": '"public-etag"'},
              "metadata": {"http_status": 200,
                           "content_type": "application/json"}},
        inventory=inventory(table),
        retrieved_at=stamp,
    )


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "safe-local"
        self.store = SnapshotStore(self.root)

    def test_immutable_byte_for_byte_sha256_and_provenance(self):
        data = evidence()
        result = self.store.archive(**data)
        self.assertFalse(result["publication_approved"])
        self.assertEqual(result["namespace"], NAMESPACE)
        self.assertEqual(result["sha256"]["tablefile.zip"],
                         hashlib.sha256(data["archive"]).hexdigest())
        self.assertEqual(result["sha256"]["metadata.json"],
                         hashlib.sha256(data["metadata"]).hexdigest())
        retrieved = self.store.latest(data["dataset_id"])
        self.assertEqual(retrieved["objects"], result["sha256"])
        self.assertEqual(retrieved["request"]["startyear"], 2021)
        self.assertEqual(retrieved["source_url"], BASE_URL)
        self.assertEqual(retrieved["response_http"]["tablefile"]["http_status"], 200)
        self.assertIn("retrieved_at", retrieved)
        self.assertEqual(self.store.read_object(result["sha256"]["tablefile.zip"]), data["archive"])
        self.assertEqual(self.store.read_object(result["sha256"]["metadata.json"]), data["metadata"])
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_same_content_deduplicates_blobs_but_retains_both_acquisitions(self):
        first = self.store.archive(**evidence())
        second = self.store.archive(**evidence(stamp=LATER))
        self.assertNotEqual(first["acquisition_id"], second["acquisition_id"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(self.store.metrics()["distinct_blobs"], 2)
        self.assertEqual(self.store.metrics()["acquisition_events"], 2)
        self.assertEqual(len(self.store.events("42153-0002")), 2)

    def test_revision_preserves_earlier_bytes_and_asof_history(self):
        original = evidence()
        first = self.store.archive(**original)
        # The test-only revised archive has distinct raw bytes, not invented
        # public statistics; it mimics a new raw provider release.
        revised = evidence(archive=original["archive"] + b"test-revision",
                           stamp=LATER)
        second = self.store.archive(**revised)
        self.assertNotEqual(first["sha256"]["tablefile.zip"], second["sha256"]["tablefile.zip"])
        old = self.store.latest("42153-0002", as_of=FIRST)
        current = self.store.latest("42153-0002")
        self.assertEqual(old["acquisition_id"], first["acquisition_id"])
        self.assertEqual(current["acquisition_id"], second["acquisition_id"])
        self.assertEqual(self.store.read_object(first["sha256"]["tablefile.zip"]), original["archive"])
        self.assertEqual(self.store.read_object(second["sha256"]["tablefile.zip"]), revised["archive"])
        self.assertIsNone(self.store.latest("42153-0002", as_of="2026-11-18T00:00:00Z"))
        self.assertEqual(len(self.store.events("42153-0002")), 2)

    def test_asof_second_boundary_excludes_later_microseconds(self):
        self.store.archive(**evidence(stamp="2026-11-19T10:30:00.900Z"))
        self.assertIsNone(self.store.latest("42153-0002", as_of="2026-11-19T10:30:00Z"))
        self.assertIsNotNone(self.store.latest("42153-0002", as_of="2026-11-19T10:30:01Z"))

    def test_blob_corruption_blocks_read_and_historical_query(self):
        result = self.store.archive(**evidence())
        digest = result["sha256"]["tablefile.zip"]
        path = self.store._object_path(digest)
        path.write_bytes(b"TAMPERED")
        with self.assertRaisesRegex(SnapshotError, "digest mismatch"):
            self.store.read_object(digest)
        with self.assertRaisesRegex(SnapshotError, "digest mismatch"):
            self.store.latest("42153-0002")
        with self.assertRaisesRegex(SnapshotError, "integrity check"):
            self.store.archive(**evidence(stamp=LATER))
        self.assertEqual(self.store.metrics()["acquisition_events"], 1)

    def test_triggers_prevent_updates_deletions_and_publication(self):
        event = self.store.archive(**evidence())
        with sqlite3.connect(self.store.db_file) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE acquisitions SET publication_approved=1 WHERE acquisition_id=?",
                           (event["acquisition_id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM acquisitions WHERE acquisition_id=?",
                           (event["acquisition_id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM object_blobs")
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_validation_errors_leave_no_acquisition_events(self):
        bad_cases = [
            {"dataset_id": "other"},
            {"source_url": "http://attacker.example"},
            {"request": {"name": "42153-0001"}},
            {"request": {"name": "42153-0002", "token": "secret"}},
            {"inventory": {"table": "42153-0002", "covered_codes": ["20"],
                           "published_observations": False}},
            {"inventory": {"table": "42153-0002", "covered_codes": ["20","24","28","29"],
                           "published_observations": True}},
            {"retrieved_at": "2026-11-19"},
            {"http": {"tablefile": {"http_status": 200}}},
        ]
        for patch in bad_cases:
            with self.subTest(patch=patch):
                with self.assertRaises(SnapshotError):
                    self.store.archive(**{**evidence(), **patch})
                self.assertEqual(self.store.metrics()["acquisition_events"], 0)

    def test_blob_write_failure_never_records_acquisition(self):
        with patch.object(self.store, "_write_object", side_effect=SnapshotError("disk full")):
            with self.assertRaisesRegex(SnapshotError, "disk full"):
                self.store.archive(**evidence())
        self.assertEqual(self.store.metrics()["acquisition_events"], 0)
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_db_write_failure_never_records_acquisition(self):
        # Simulate a transactional failure after the raw blobs are written.
        with patch.object(self.store, "_connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaisesRegex(SnapshotError, "Metadata transaction failed"):
                self.store.archive(**evidence())
        self.assertEqual(self.store.metrics()["acquisition_events"], 0)

    def test_namespace_permissions_and_symlinks(self):
        self.assertEqual(self.store.base.name, "v1")
        self.assertEqual(self.store.base.parent.name, "firmablick")
        self.assertEqual(self.store.base.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.store.db_file.stat().st_mode & 0o777, 0o600)
        hostile = Path(self.temp.name) / "link"
        hostile.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(SnapshotError, "symlink"):
            SnapshotStore(hostile)
        event = self.store.archive(**evidence())
        digest = event["sha256"]["tablefile.zip"]
        self.assertEqual(self.store._object_path(digest).stat().st_mode & 0o777, 0o600)

    def test_no_data_leakage_across_independent_store_namespaces(self):
        other = SnapshotStore(Path(self.temp.name) / "other-project")
        self.store.archive(**evidence())
        self.assertEqual(other.metrics()["acquisition_events"], 0)
        self.assertEqual(other.events("42153-0002"), [])

    def test_source_query_and_http_credentials_not_persisted(self):
        with self.assertRaises(SnapshotError):
            self.store.archive(**evidence(
                http={"tablefile": {"http_status": 200}, "metadata": {"http_status": 200}},
                request={"name": "42153-0002", "password": "sensitive"}))
        self.assertEqual(self.store.metrics()["acquisition_events"], 0)
        example = evidence()
        example["http"]["tablefile"]["Authorization"] = "SECRET"
        self.store.archive(**example)
        with sqlite3.connect(self.store.db_file) as db:
            value = db.execute("SELECT response_http_json FROM acquisitions").fetchone()[0]
        self.assertNotIn("SECRET", value)
        self.assertNotIn("Authorization", value)

    def test_acquisition_integration_uses_append_only_store(self):
        class Client:
            def table_metadata(self, name):
                return status_response(), {"http_status": 200}
            def tablefile(self, name, start, end):
                return fixture_zip(name), {"http_status": 200}
        result = acquire(Client(), self.root, startyear=2021, endyear=2026)
        self.assertFalse(result["published"])
        self.assertEqual(result["coverage"], ["20", "24", "28", "29", "C"])
        self.assertEqual(len(result["snapshots"]), 2)
        self.assertEqual(self.store.metrics()["acquisition_events"], 2)
        self.assertEqual(self.store.metrics()["published"], 0)

    def test_rejects_invalid_datetime(self):
        with self.assertRaises(SnapshotError):
            require_utc_timestamp("2026-02-30T00:00:00Z")
        with self.assertRaises(SnapshotError):
            require_utc_timestamp("2026-11-19T10:30:00+05:30")


if __name__ == "__main__":
    unittest.main()
