"""Read-only Destatis GENESIS POST client and fail-closed industrial-series discovery.

Requires a free GENESIS personal token in GENESIS_TOKEN. Stores raw ZIP responses and
provenance, never normalized or purportedly published economic statistics.
No third-party dependencies. See docs/genesis-ingestion.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

BASE_URL = "https://genesis.destatis.de/genesisWS/rest/2020/"
TABLES = ("42153-0001", "42153-0002")
TARGETS = {"42153-0001": {"C"}, "42153-0002": {"20", "24", "28", "29"}}
# Reject unknown classifications rather than guessing via German text labels.
CODE_ALIASES = {
    "C": {"C", "WZ08-C", "WZ2008-C"},
    "20": {"20", "WZ08-20", "WZ2008-20"},
    "24": {"24", "WZ08-24", "WZ2008-24"},
    "28": {"28", "WZ08-28", "WZ2008-28"},
    "29": {"29", "WZ08-29", "WZ2008-29"},
}
TRANSIENT_HTTP = {429, 500, 502, 503, 504}
MAX_ARCHIVE = 30 * 1024 * 1024
MAX_CSV = 80 * 1024 * 1024
INDEX_BASE = re.compile(r"\b(19\d\d|20\d\d)\s*=\s*100\b")


class GenesisError(Exception):
    """GENESIS request, response or quality error. Never contains credentials."""

    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def headers(token: str) -> dict[str, str]:
    if not token or not token.strip():
        raise GenesisError(
            "GENESIS_TOKEN is required. Register for free at genesis.destatis.de "
            "and generate a read-only personal token under Webservice (API).",
            exit_code=2,
        )
    if "\n" in token or "\r" in token:
        raise GenesisError("Invalid GENESIS_TOKEN header contents.", exit_code=2)
    return {"Content-Type": "application/x-www-form-urlencoded", "Accept": "*/*",
            "username": token, "password": ""}


def api_status(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise GenesisError("Unexpected GENESIS API JSON shape: expected an object.")
    status = payload.get("Status")
    if isinstance(status, dict):
        return str(status.get("Code", "")), str(status.get("Content", ""))
    if isinstance(status, str):
        return "", status
    raise GenesisError("GENESIS API JSON has no Status; refusing to treat it as data.")


def decode_api_json(raw: bytes, operation: str) -> dict:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise GenesisError(f"{operation}: malformed JSON response.") from exc
    code, message = api_status(data)
    # According to the GENESIS API, an HTTP 200 can also carry an error Status.
    if code != "0":
        suffix = (" (check token credentials)" if code in ("2", "15") else "")
        raise GenesisError(f"{operation}: GENESIS status {code}: {message[:250]}{suffix}",
                           exit_code=2 if code in ("2", "15") else 1)
    return data


class GenesisClient:
    def __init__(self, token: str, *, base_url: str = BASE_URL, attempts: int = 3,
                 transport=None, sleep=time.sleep):
        self.token = token
        self.base_url = base_url.rstrip("/") + "/"
        if not self.base_url.startswith("https://"):
            raise GenesisError("GENESIS endpoint must use HTTPS.")
        self.attempts = attempts
        self.transport = transport or urlopen
        self.sleep = sleep

    def post(self, operation: str, params: dict[str, str], *, max_bytes=MAX_ARCHIVE) -> tuple[bytes, dict]:
        if operation not in ("helloworld/logincheck", "metadata/table", "data/tablefile"):
            raise GenesisError("Unapproved GENESIS API operation.")
        url = self.base_url + operation
        req = Request(url, data=urlencode(params).encode("utf-8"),
                      headers=headers(self.token), method="POST")
        for attempt in range(self.attempts):
            try:
                with self.transport(req, timeout=60) as response:
                    status = response.status
                    # Limit even successful downloads; avoid a runaway allocation.
                    raw = response.read(max_bytes + 1)
                    if len(raw) > max_bytes:
                        raise GenesisError(f"{operation}: exceeds {max_bytes} byte safety limit.")
                    info = {
                        "http_status": status,
                        "content_type": response.headers.get("Content-Type", ""),
                        "source_last_modified": response.headers.get("Last-Modified"),
                        "source_etag": response.headers.get("ETag"),
                    }
                    return raw, info
            except HTTPError as exc:
                # Some GENESIS authentication failures arrive as HTTP 404 with
                # Status.Code 2 or 15, rather than a conventional 401/403.
                try:
                    err_payload = json.loads(exc.read(8192).decode("utf-8-sig"))
                    err_code, _ = api_status(err_payload)
                except (ValueError, UnicodeDecodeError, GenesisError):
                    err_code = ""
                if exc.code in (401, 403) or err_code in ("2", "15"):
                    raise GenesisError(
                        "GENESIS authentication rejected. Check the read-only token in GENESIS_TOKEN.",
                        exit_code=2,
                    ) from None
                if exc.code in TRANSIENT_HTTP and attempt + 1 < self.attempts:
                    self.sleep(min(2 ** attempt, 8))
                    continue
                raise GenesisError(
                    f"GENESIS {operation}: HTTP {exc.code}. "
                    + ("Retry later." if exc.code in TRANSIENT_HTTP else "Check table and API access.")
                ) from None
            except (URLError, TimeoutError) as exc:
                if attempt + 1 < self.attempts:
                    self.sleep(min(2 ** attempt, 8))
                    continue
                raise GenesisError(f"GENESIS {operation}: network unavailable after retries.") from exc
        raise GenesisError(f"GENESIS {operation}: retry budget exhausted.")

    def logincheck(self) -> dict:
        raw, _ = self.post("helloworld/logincheck", {"language": "de"})
        # Official Destatis examples return a *textual* Status for logincheck,
        # whereas metadata/table returns Status {Code, Content}. Accept the
        # textual success only with the documented Username evidence.
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise GenesisError("logincheck: malformed JSON response.") from exc
        if isinstance(payload, dict) and isinstance(payload.get("Status"), str):
            message = payload["Status"].lower()
            if payload.get("Username") and ("erfolgreich" in message or "successful" in message):
                return payload
            raise GenesisError("GENESIS logincheck: authentication was not confirmed.", exit_code=2)
        return decode_api_json(raw, "logincheck")

    def table_metadata(self, table: str) -> tuple[bytes, dict]:
        raw, info = self.post("metadata/table", {"name": table, "area": "all",
                                                 "language": "de"})
        decode_api_json(raw, f"metadata/{table}")
        return raw, info

    def tablefile(self, table: str, startyear: int, endyear: int) -> tuple[bytes, dict]:
        params = {"name": table, "area": "all", "startyear": str(startyear),
                  "endyear": str(endyear), "format": "ffcsv", "compress": "true",
                  "job": "false", "language": "de"}
        raw, info = self.post("data/tablefile", params)
        # Error replies can be JSON *even with HTTP 200*.
        if raw.lstrip().startswith(b"{"):
            decode_api_json(raw, f"tablefile/{table}")
            raise GenesisError(f"tablefile/{table}: expected ZIP; received JSON status only.")
        if not raw.startswith(b"PK"):
            raise GenesisError(f"tablefile/{table}: expected a ZIP archive, got another format.")
        return raw, info


def inspect_ffcsv(archive: bytes, table: str) -> dict:
    """Parse the documented GENESIS flat-file CSV structure without deriving figures.

    Returns coverage, source row identifiers/dimensions and observed base-year strings.
    Rejects unidentified sector labels, ambiguous codes and missing expected sectors.
    """
    if len(archive) > MAX_ARCHIVE:
        raise GenesisError("GENESIS ZIP exceeds archive limit.")
    try:
        with ZipFile(io.BytesIO(archive)) as zf:
            names = [item for item in zf.infolist() if not item.is_dir()]
            if len(names) != 1 or not names[0].filename.lower().endswith(".csv"):
                raise GenesisError("GENESIS ZIP must contain exactly one CSV file.")
            if names[0].file_size > MAX_CSV:
                raise GenesisError("GENESIS CSV uncompressed size exceeds safety limit.")
            csv_bytes = zf.read(names[0])
    except (BadZipFile, RuntimeError, ValueError) as exc:
        raise GenesisError("Malformed GENESIS tablefile ZIP.") from exc
    if len(csv_bytes) > MAX_CSV:
        raise GenesisError("GENESIS decompressed CSV exceeds safety limit.")
    text = None
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = csv_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise GenesisError("Unsupported GENESIS CSV encoding.")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    fields = reader.fieldnames or []
    if not {"value", "time"}.issubset(fields):
        raise GenesisError("GENESIS flat-file CSV missing value/time columns.")
    dims = [key for key in fields if re.fullmatch(r"\d+_variable_attribute_code", key)
            and key.replace("_attribute_code", "_code") in fields]
    if not dims:
        raise GenesisError("GENESIS CSV has no coded industry dimensions.")
    expected = TARGETS[table]
    coverage: dict[str, dict] = {}
    base_years = set()
    matched_rows = 0
    for record in reader:
        if not any(record.values()):
            continue
        raw_codes = {key: (record.get(key) or "").strip() for key in dims}
        # Match industry codes exclusively on WZ-classifying dimensions, not
        # arbitrary month/adjustment attributes that might also equal "20".
        industry_codes = [raw_codes[key] for key in dims
                          if "WZ" in (record.get(key.replace("_attribute_code", "_code")) or "").upper()]
        matched = {target for target in expected for code in industry_codes
                   if code in CODE_ALIASES[target]}
        if len(matched) > 1:
            raise GenesisError("Ambiguous industry codes within a GENESIS record.")
        if not matched:
            continue  # Other WZ divisions are expected in the sector table.
        sector = next(iter(matched))
        if not (record.get("time") or "").strip():
            raise GenesisError(f"{table}/{sector}: empty source time value.")
        value = (record.get("value") or "").strip()
        if not value:
            raise GenesisError(f"{table}/{sector}: empty raw value; status must be explicit.")
        raw_unit = (record.get("value_unit") or "").strip()
        bases = INDEX_BASE.findall(raw_unit)
        if not bases:
            # Some GENESIS versions show the base in the value-variable label.
            bases = INDEX_BASE.findall((record.get("value_variable_label") or ""))
        if not bases:
            raise GenesisError(f"{table}/{sector}: index basis not discoverable in source row.")
        base_years.update(bases)
        chosen = coverage.setdefault(sector, {"rows": 0, "sample_original_dimensions": raw_codes,
                                               "source_keys": [], "raw_time_examples": []})
        chosen["rows"] += 1
        matched_rows += 1
        if len(chosen["source_keys"]) < 3:
            chosen["source_keys"].append(
                {"statistics_code": record.get("statistics_code"), "time_code": record.get("time_code"),
                 "value_variable_code": record.get("value_variable_code"),
                 "quality": record.get("quality") or record.get("value_quality")})
            chosen["raw_time_examples"].append(record.get("time"))
    if set(coverage) != expected:
        missing = sorted(expected - set(coverage))
        raise GenesisError(f"{table}: missing expected industry codes {missing}; raw data is not publishable.")
    if len(base_years) != 1:
        raise GenesisError(f"{table}: conflicting index reference bases {sorted(base_years)}.")
    return {"table": table, "covered_codes": sorted(coverage), "industry_summary": coverage,
            "matched_rows": matched_rows, "reported_index_base_year": int(next(iter(base_years))),
            "discovery_only": True, "published_observations": False}


def write_snapshot(folder: Path, table: str, metadata: bytes, archive: bytes,
                   meta_http: dict, data_http: dict, inventory: dict,
                   *, startyear: int, endyear: int) -> dict:
    """Local raw acquisition artifacts; Issue #9 will move to immutable storage."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = folder / f"{table}_{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    manifest = {
        "source": "Destatis GENESIS", "dataset_id": table,
        "retrieved_at": utc_now(), "source_url": BASE_URL,
        "methods": ["POST metadata/table", "POST data/tablefile"],
        "request_parameters": {"name": table, "startyear": startyear, "endyear": endyear,
                               "format": "ffcsv", "language": "de"},
        "raw_files": {"tablefile.zip": hashlib.sha256(archive).hexdigest(),
                      "metadata.json": hashlib.sha256(metadata).hexdigest()},
        "http": {"tablefile": data_http, "metadata": meta_http}, "inventory": inventory,
        "quality_gate": "COMPLETE_SOURCE_CODE_COVERAGE_DISCOVERY_ONLY",
        "publication_approved": False,
    }
    (target / "tablefile.zip").write_bytes(archive)
    (target / "metadata.json").write_bytes(metadata)
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    return {"table": table, "directory": str(target), "covered_codes": inventory["covered_codes"],
            "raw_sha256": manifest["raw_files"]["tablefile.zip"]}


def acquire(client: GenesisClient, output: Path, *, startyear: int, endyear: int) -> dict:
    if endyear < startyear or startyear < 1990 or endyear > 2100:
        raise GenesisError("Invalid start/end years.")
    if output.is_symlink():
        raise GenesisError("Refusing symlink output directory.")
    results = []
    for table in TABLES:
        metadata, mi = client.table_metadata(table)
        archive, ai = client.tablefile(table, startyear, endyear)
        inventory = inspect_ffcsv(archive, table)
        results.append(write_snapshot(output, table, metadata, archive, mi, ai, inventory,
                                      startyear=startyear, endyear=endyear))
    return {"status": "discovered_and_downloaded", "published": False,
            "coverage": sorted({code for v in results for code in v["covered_codes"]}),
            "snapshots": results}


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Destatis GENESIS source snapshot downloader")
    parser.add_argument("command", choices=("fetch", "logincheck", "live-smoke"))
    parser.add_argument("--output", default="artifacts/genesis",
                        help="Local raw-data directory (ignored by Git)")
    parser.add_argument("--startyear", type=int, default=2021)
    parser.add_argument("--endyear", type=int, default=datetime.now(timezone.utc).year)
    args = parser.parse_args(argv)
    try:
        token = os.environ.get("GENESIS_TOKEN", "")
        client = GenesisClient(token)
        if args.command == "live-smoke":
            if os.getenv("GENESIS_LIVE_SMOKE") != "1":
                raise GenesisError("Set GENESIS_LIVE_SMOKE=1 explicitly for external API smoke tests.",
                                   exit_code=2)
            client.logincheck()
            print(json.dumps({"status": "live_authenticated", "source": "Destatis GENESIS"}))
            return 0
        if args.command == "logincheck":
            client.logincheck()
            print(json.dumps({"status": "authenticated", "source": "Destatis GENESIS"}))
            return 0
        result = acquire(client, Path(args.output), startyear=args.startyear, endyear=args.endyear)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except GenesisError as exc:
        print(f"GENESIS ingestion blocked: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(cli())
