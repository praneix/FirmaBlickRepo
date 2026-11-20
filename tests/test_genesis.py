"""Official-format *synthetic* GENESIS tablefile and API response fixtures.

No published statistical figures are copied into these tests.
Source format: Destatis POST data/tablefile ffcsv (ZIP containing one semicolon CSV).
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from zipfile import ZipFile, ZIP_DEFLATED

from ingestion.genesis import (
    BASE_URL, GenesisClient, GenesisError, acquire, cli, decode_api_json,
    inspect_ffcsv, write_snapshot,
)


COLUMNS = [
    "statistics_code", "statistics_label", "time_code", "time_label", "time",
    "1_variable_code", "1_variable_label", "1_variable_attribute_code",
    "1_variable_attribute_label", "2_variable_code", "2_variable_label",
    "2_variable_attribute_code", "2_variable_attribute_label", "value",
    "value_unit", "value_variable_code", "value_variable_label", "quality",
]


def fixture_zip(table, *, missing=(), inconsistent_base=False, ambiguous=False, malformed=False):
    codes = ["C"] if table == "42153-0001" else ["20", "24", "28", "29"]
    rows = []
    for i, code in enumerate(codes):
        if code in missing:
            continue
        first = f"WZ08-{code}"
        second = ("WZ08-24" if code == "28" and ambiguous else "ORIG")
        row = [
            "42153", "Synthetic index fixture", "2026M01", "January 2026",
            "2026-01", "WZ08", "WZ 2008", first, f"Code {code}",
            "AJUST", "Adjustment", second, "Original data",
            f"{90+i},5", "2020=100" if inconsistent_base and code == "29" else "2021=100",
            "PRODIDX", "Production index", "p" if code == "29" else "",
        ]
        rows.append(row)
    if table == "42153-0002":
        rows.append([
            "42153", "Synthetic index fixture", "2026M01", "January 2026",
            "2026-01", "WZ08", "WZ 2008", "WZ08-281", "3-digit unrelated",
            "AJUST", "Adjustment", "ORIG", "Original data", "50,0",
            "2021=100", "PRODIDX", "Production index", "",
        ])
    data = ";".join(COLUMNS) + "\n"
    for row in rows:
        data += ";".join(row) + "\n"
    if malformed:
        data = "time;price\n2026-01;100\n"
    memory = io.BytesIO()
    with ZipFile(memory, "w", ZIP_DEFLATED) as zf:
        zf.writestr("genesis_ffcsv.csv", data.encode("utf-8"))
    return memory.getvalue()


def status_response(code=0):
    return json.dumps({"Ident": {"Service": "metadata", "Method": "table"},
                       "Status": {"Code": code, "Content": "OK" if code == 0 else "Bad token"},
                       "Object": {"Code": "42153-0002", "Content": "Synthetic metadata"}}).encode()


class FakeHTTP:
    def __init__(self, raw, status=200):
        self.raw = raw
        self.status = status
        self.headers = {"Content-Type": "application/octet-stream", "ETag": '"fixture"'}
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, tb):
        return False
    def read(self, n):
        return self.raw[:n]


class ClientTests(unittest.TestCase):
    def test_no_token_does_not_contact_provider(self):
        touched = []
        client = GenesisClient("", transport=lambda request, timeout: touched.append(True))
        with self.assertRaisesRegex(GenesisError, "GENESIS_TOKEN"):
            client.logincheck()
        self.assertEqual(touched, [])

    def test_post_form_auth_headers_no_secrets_in_body(self):
        seen = []
        def transport(request, timeout):
            seen.append(request)
            return FakeHTTP(status_response())
        result = GenesisClient("test-only-token", transport=transport).logincheck()
        self.assertEqual(result["Status"]["Code"], 0)
        self.assertEqual(len(seen), 1)
        request = seen[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Username"), "test-only-token")
        self.assertEqual(request.get_header("Password"), "")
        self.assertNotIn(b"test-only-token", request.data)
        self.assertEqual(request.full_url, BASE_URL + "helloworld/logincheck")

    def test_json_status_errors_are_not_successful_downloads(self):
        with self.assertRaisesRegex(GenesisError, "status 2"):
            decode_api_json(status_response(2), "test")
        client = GenesisClient("test", transport=lambda request, timeout: FakeHTTP(status_response(2)))
        with self.assertRaisesRegex(GenesisError, "status 2"):
            client.tablefile("42153-0002", 2021, 2026)

    def test_http_unauthorized_is_actionable_and_not_retried(self):
        attempts = []
        def bad(request, timeout):
            attempts.append(True)
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)
        client = GenesisClient("invalid", transport=bad, sleep=lambda _: None)
        with self.assertRaisesRegex(GenesisError, "authentication rejected"):
            client.logincheck()
        self.assertEqual(len(attempts), 1)

    def test_transient_http_status_is_retried_with_bounded_budget(self):
        attempts = []
        def flaky(request, timeout):
            attempts.append(True)
            if len(attempts) < 3:
                raise HTTPError(request.full_url, 503, "Unavailable", {}, None)
            return FakeHTTP(status_response())
        client = GenesisClient("test", transport=flaky, sleep=lambda _: None)
        self.assertEqual(client.logincheck()["Status"]["Code"], 0)
        self.assertEqual(len(attempts), 3)

    def test_rejects_non_zip_and_json_status_without_data(self):
        client = GenesisClient("test", transport=lambda request, timeout: FakeHTTP(b"not-zip"))
        with self.assertRaisesRegex(GenesisError, "expected a ZIP"):
            client.tablefile("42153-0001", 2021, 2026)
        client = GenesisClient("test", transport=lambda request, timeout: FakeHTTP(status_response(0)))
        with self.assertRaisesRegex(GenesisError, "received JSON status only"):
            client.tablefile("42153-0001", 2021, 2026)

    def test_large_response_rejected(self):
        client = GenesisClient("test", transport=lambda request, timeout: FakeHTTP(b"x" * 101))
        with self.assertRaisesRegex(GenesisError, "safety limit"):
            client.post("metadata/table", {"name": "42153-0001"}, max_bytes=100)


class ShapeAndCoverageTests(unittest.TestCase):
    def test_all_five_industries_discovered_exact_codes(self):
        aggregate = inspect_ffcsv(fixture_zip("42153-0001"), "42153-0001")
        divisions = inspect_ffcsv(fixture_zip("42153-0002"), "42153-0002")
        self.assertEqual(aggregate["covered_codes"], ["C"])
        self.assertEqual(divisions["covered_codes"], ["20", "24", "28", "29"])
        self.assertEqual(divisions["matched_rows"], 4)
        self.assertEqual(divisions["reported_index_base_year"], 2021)
        self.assertEqual(divisions["industry_summary"]["29"]["source_keys"][0]["quality"], "p")
        self.assertIn("1_variable_attribute_code", divisions["industry_summary"]["28"]["sample_original_dimensions"])
        self.assertFalse(divisions["published_observations"])

    def test_missing_sectors_and_mixed_base_fail_closed(self):
        with self.assertRaisesRegex(GenesisError, "missing expected industry codes"):
            inspect_ffcsv(fixture_zip("42153-0002", missing=["24"]), "42153-0002")
        with self.assertRaisesRegex(GenesisError, "conflicting index reference bases"):
            inspect_ffcsv(fixture_zip("42153-0002", inconsistent_base=True), "42153-0002")

    def test_ambiguous_dimension_codes_fail(self):
        with self.assertRaisesRegex(GenesisError, "Ambiguous"):
            inspect_ffcsv(fixture_zip("42153-0002", ambiguous=True), "42153-0002")

    def test_unexpected_csv_shape_fails(self):
        with self.assertRaisesRegex(GenesisError, "missing value/time"):
            inspect_ffcsv(fixture_zip("42153-0002", malformed=True), "42153-0002")

    def test_snapshot_is_raw_and_digest_accurate(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = fixture_zip("42153-0001")
            meta = status_response()
            inventory = inspect_ffcsv(raw, "42153-0001")
            result = write_snapshot(Path(temp), "42153-0001", meta, raw,
                                    {"http_status": 200}, {"http_status": 200},
                                    inventory, startyear=2021, endyear=2026)
            folder = Path(result["directory"])
            self.assertEqual((folder / "tablefile.zip").read_bytes(), raw)
            self.assertEqual((folder / "metadata.json").read_bytes(), meta)
            manifest = json.loads((folder / "manifest.json").read_text())
            self.assertEqual(manifest["raw_files"]["tablefile.zip"],
                             __import__("hashlib").sha256(raw).hexdigest())
            self.assertFalse(manifest["publication_approved"])
            self.assertIn("retrieved_at", manifest)
            self.assertNotIn("token", json.dumps(manifest).lower())

    def test_acquire_records_two_sources_and_complete_coverage(self):
        class Dummy:
            def table_metadata(self, table):
                return status_response(), {"http_status": 200}
            def tablefile(self, table, first, last):
                return fixture_zip(table), {"http_status": 200}
        with tempfile.TemporaryDirectory() as temp:
            result = acquire(Dummy(), Path(temp), startyear=2021, endyear=2026)
            self.assertEqual(result["status"], "discovered_and_downloaded")
            self.assertEqual(result["coverage"], ["20", "24", "28", "29", "C"])
            self.assertEqual(len(result["snapshots"]), 2)
            self.assertFalse(result["published"])

    def test_missing_token_cli_halts_with_actionable_exit(self):
        with patch.dict("os.environ", {"GENESIS_TOKEN": ""}):
            with patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(cli(["logincheck"]), 2)
            self.assertIn("GENESIS_TOKEN", err.getvalue())

    def test_live_smoke_requires_explicit_flag(self):
        with patch.dict("os.environ", {"GENESIS_TOKEN": "test-token", "GENESIS_LIVE_SMOKE": "0"}):
            self.assertEqual(cli(["live-smoke"]), 2)


if __name__ == "__main__":
    unittest.main()
