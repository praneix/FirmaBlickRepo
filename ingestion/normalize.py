"""Fail-closed Destatis monthly-production normalization and quarantine (Issue #10).

No publication path is exposed. Requires explicitly verified source-series mapping and
quality-code mapping supplied by the caller. Never infers official semantics.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

from ingestion.genesis import INDEX_BASE, TABLES, CODE_ALIASES
from ingestion.snapshot_store import SnapshotStore, SnapshotError

EXPECTED = {"42153-0001": {"C"}, "42153-0002": {"20", "24", "28", "29"}}
PERIOD = re.compile(r"^(20\d\d|19\d\d)-(0[1-9]|1[0-2])$")
TRANSFORMATION_VERSION = "genesis-monthly-production-v1.0.0"
MAX_CSV_BYTES = 80 * 1024 * 1024
MISSING_TOKENS = {".", "-", "/", "..."}
ALLOWED_ADJUSTMENTS = {
    "original", "calendar_adjusted", "seasonally_adjusted", "seasonal_calendar_adjusted"
}


class QualityError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise QualityError(code, message)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def validated_profile(profile: dict) -> dict:
    """A deliberate human-confirmed mapping. Never infer base/quality/adjustment."""
    require(isinstance(profile, dict), "PROFILE_MISSING", "Confirmed source profile required.")
    required = {"value_variable_code", "adjustment_variable_code",
                "adjustment_attribute_code", "adjustment", "expected_base_year",
                "quality_map", "confirmed_against_official_metadata"}
    require(set(profile) == required, "PROFILE_FIELDS", "Profile fields must match explicit contract.")
    for key in ("value_variable_code", "adjustment_variable_code", "adjustment_attribute_code"):
        require(isinstance(profile[key], str) and bool(profile[key].strip()),
                "PROFILE_FIELDS", f"Invalid profile {key}.")
    require(profile["adjustment"] in ALLOWED_ADJUSTMENTS,
            "ADJUSTMENT_UNKNOWN", "Profile adjustment must be classified.")
    require(type(profile["expected_base_year"]) is int
            and 1990 <= profile["expected_base_year"] <= 2100,
            "BASE_UNKNOWN", "Expected index base must be explicit.")
    require(profile["confirmed_against_official_metadata"] is True,
            "PROFILE_UNVERIFIED", "Official metadata confirmation required.")
    q = profile["quality_map"]
    require(isinstance(q, dict) and "" in q, "QUALITY_MAP", "Empty quality flag mapping is required.")
    for flag, mapping in q.items():
        require(isinstance(flag, str) and isinstance(mapping, dict)
                and set(mapping) == {"observation_type", "source_status_flags", "missing_reason"},
                "QUALITY_MAP", "Each source quality flag needs explicit three-part mapping.")
        require(mapping["observation_type"] in ("official", "provisional"),
                "QUALITY_MAP", "Source type must be official or provisional.")
        require(isinstance(mapping["source_status_flags"], list)
                and all(isinstance(x, str) and x for x in mapping["source_status_flags"])
                and len(set(mapping["source_status_flags"])) == len(mapping["source_status_flags"]),
                "QUALITY_MAP", "Invalid source-status flags.")
        require(mapping["missing_reason"] is None or
                (isinstance(mapping["missing_reason"], str) and mapping["missing_reason"]),
                "QUALITY_MAP", "Invalid missing reason mapping.")
        if mapping["observation_type"] == "provisional":
            require("provisional" in mapping["source_status_flags"],
                    "QUALITY_MAP", "Provisional observations require source evidence.")
        if mapping["observation_type"] == "official":
            require("provisional" not in mapping["source_status_flags"],
                    "QUALITY_MAP", "Provisional source cannot be final official.")
    return profile


def parse_decimal(value: str, *, missing_reason: str | None) -> tuple[float | None, str | None]:
    v = (value or "").strip()
    if v in MISSING_TOKENS or not v:
        require(bool(missing_reason), "MISSING_UNMAPPED",
                "Source missing value has no confirmed missing-status mapping.")
        return None, None
    require(missing_reason is None, "STATUS_MISMATCH",
            "A source status designated missing supplied a numeric value.")
    cleaned = v.replace(",", ".")
    require(bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned)), "INVALID_NUMBER",
            "Source value is not a recognized decimal index.")
    try:
        number = Decimal(cleaned)
        as_float = float(number)
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise QualityError("INVALID_NUMBER", "Source index is numerically invalid.") from exc
    require(number.is_finite() and as_float >= 0 and as_float != float("inf"),
            "INVALID_NUMBER", "Index must be finite and nonnegative.")
    # Both representations are retained to prove exact decimal numeric lineage.
    require(Decimal(str(as_float)) == number, "PRECISION_LOSS",
            "Source decimal cannot be exactly round-tripped as a JSON number.")
    return as_float, format(number, "f")


def unzip_csv(raw: bytes) -> tuple[list[str], list[dict]]:
    try:
        with ZipFile(io.BytesIO(raw)) as zipfile:
            members = [i for i in zipfile.infolist() if not i.is_dir()]
            require(len(members) == 1 and members[0].filename.lower().endswith(".csv"),
                    "ARCHIVE_SHAPE", "Source ZIP must contain exactly one CSV.")
            require(members[0].file_size <= MAX_CSV_BYTES,
                    "ARCHIVE_SIZE", "Source CSV exceeds uncompressed size limit.")
            data = zipfile.read(members[0])
    except (BadZipFile, ValueError, OSError) as exc:
        raise QualityError("ARCHIVE_INVALID", "Stored source archive is not a valid ZIP.") from exc
    require(len(data) <= MAX_CSV_BYTES, "ARCHIVE_SIZE", "Source CSV exceeds safe size limit.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = data.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise QualityError("ENCODING", "Source CSV encoding is unsupported.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    fields = reader.fieldnames or []
    require(bool(fields) and len(fields) == len(set(fields)), "COLUMNS_INVALID",
            "Source CSV field names missing or duplicated.")
    required = {"time", "value", "value_unit", "value_variable_code",
                "statistics_code", "quality"}
    require(required <= set(fields), "COLUMNS_INVALID",
            "Essential GENESIS flat-file columns are missing.")
    dims = [field for field in fields if re.fullmatch(r"\d+_variable_attribute_code", field)
            and field.replace("_attribute_code", "_code") in fields]
    require(bool(dims), "DIMENSIONS_MISSING", "Original source dimensions missing.")
    rows = list(reader)
    require(bool(rows), "SOURCE_EMPTY", "No source data rows.")
    require(all(None not in row for row in rows), "ROWS_MALFORMED",
            "Source row has unrecognized extra fields.")
    return dims, rows


def normalize_event(store: SnapshotStore, event: dict, profile: dict) -> list[dict]:
    """Normalize one acquired immutable vintage. No external writes or publishing."""
    profile = validated_profile(profile)
    table = event["dataset_id"]
    require(table in TABLES, "DATASET_UNKNOWN", "Unapproved production dataset.")
    require(event["publication_approved"] is False, "PUBLICATION_STATE",
            "Acquisition must remain unpublished.")
    required_roles = {"metadata.json", "tablefile.zip"}
    require(set(event["objects"]) == required_roles, "LINEAGE_INCOMPLETE",
            "Raw source and metadata evidence are required.")
    metadata = store.read_object(event["objects"]["metadata.json"])
    require(hashlib.sha256(metadata).hexdigest() == event["objects"]["metadata.json"],
            "LINEAGE_INCOMPLETE", "Metadata digest mismatch.")
    raw = store.read_object(event["objects"]["tablefile.zip"])
    dims, rows = unzip_csv(raw)
    results = []
    duplicates = set()
    observed = set()
    selected_bases = set()
    observed_periods: dict[str, set] = {}
    for row_index, row in enumerate(rows, start=2):
        dimensions = {key: (row[key] or "").strip() for key in dims}
        wz_keys = [key for key in dims if
                   "WZ" in (row[key.replace("_attribute_code", "_code")] or "").upper()]
        industry_values = [dimensions[key] for key in wz_keys]
        matches = {sector for sector in EXPECTED[table] for raw_code in industry_values
                   if raw_code in CODE_ALIASES[sector]}
        require(len(matches) <= 1, "INDUSTRY_AMBIGUOUS",
                f"Row {row_index} has conflicting classification dimensions.")
        if not matches:
            continue
        industry = next(iter(matches))
        observed.add(industry)
        # Original dimension identity is preserved from every source attribute.
        adjustment_codes = [dimensions[key] for key in dims if
                            (row[key.replace("_attribute_code", "_code")] or "").strip()
                            == profile["adjustment_variable_code"]]
        require(len(adjustment_codes) == 1, "ADJUSTMENT_UNKNOWN",
                f"Row {row_index} has missing/ambiguous adjustment identity.")
        if adjustment_codes[0] != profile["adjustment_attribute_code"]:
            continue
        if row["value_variable_code"] != profile["value_variable_code"]:
            continue
        month = (row["time"] or "").strip()
        require(bool(PERIOD.fullmatch(month)), "PERIOD_INVALID",
                f"Row {row_index} is not a monthly YYYY-MM period.")
        raw_unit = (row["value_unit"] or "").strip()
        bases = INDEX_BASE.findall(raw_unit)
        require(len(bases) == 1, "UNIT_UNKNOWN",
                f"Row {row_index} has no unique source index base.")
        base = int(bases[0])
        require(base == profile["expected_base_year"], "BASE_CONFLICT",
                f"Row {row_index} index base differs from confirmed metadata.")
        selected_bases.add(base)
        raw_quality = (row["quality"] or "").strip()
        require(raw_quality in profile["quality_map"], "STATUS_UNKNOWN",
                f"Row {row_index} has an unrecognized source quality status.")
        mapping = profile["quality_map"][raw_quality]
        number, exact = parse_decimal(row["value"], missing_reason=mapping["missing_reason"])
        identity = (industry, month, profile["adjustment"], profile["value_variable_code"])
        require(identity not in duplicates, "DUPLICATE_OBSERVATION",
                f"Duplicate sector/month/series at source row {row_index}.")
        duplicates.add(identity)
        observed_periods.setdefault(industry, set()).add(month)
        original_dimensions = {
            key: (row[key] or "").strip() for key in dims
        }
        for key in dims:
            dimension_code = key.replace("_attribute_code", "_code")
            original_dimensions[dimension_code] = (row[dimension_code] or "").strip()
        original_dimensions["value_variable_code"] = row["value_variable_code"]
        original_dimensions["statistics_code"] = row["statistics_code"]
        original_dimensions["quality"] = raw_quality or "empty"
        status_flags = list(mapping["source_status_flags"])
        item = {
            "schema_version": "1.0.0", "source_id": "destatis",
            "dataset_id": table,
            "original_series_key": "|".join([
                str(row["statistics_code"]), str(row["value_variable_code"]),
                industry, profile["adjustment_attribute_code"]]),
            "original_dimensions": original_dimensions,
            "geo": "DE", "frequency": "M", "period": month,
            "measure": "industrial_production_volume_index",
            "value": number, "unit": "index", "base_year": base,
            "adjustment": profile["adjustment"],
            "classification_system": "WZ",
            "classification_revision": "WZ2008",
            "industry_code": industry,
            "observation_type": mapping["observation_type"],
            "source_status_flags": status_flags,
            "retrieved_at": event["retrieved_at"],
            "raw_sha256": event["objects"]["tablefile.zip"],
            "raw_snapshot_id": event["acquisition_id"],
            "transformation_version": TRANSFORMATION_VERSION,
        }
        if number is None:
            item["missing_reason"] = mapping["missing_reason"]
        if event["source_release_at"]:
            item["source_release_at"] = event["source_release_at"]
        lineage = {
            "acquisition_id": event["acquisition_id"], "dataset_id": table,
            "raw_sha256": event["objects"]["tablefile.zip"],
            "metadata_sha256": event["objects"]["metadata.json"],
            "raw_csv_row": row_index, "raw_csv_column": "value",
            "raw_value": (row["value"] or "").strip(),
            "raw_decimal": exact,
            "raw_quality": raw_quality,
            "transformation_version": TRANSFORMATION_VERSION,
        }
        results.append({"observation": item, "lineage": lineage})
    require(observed == EXPECTED[table], "SECTOR_COVERAGE",
            "Raw source missing required industry sectors.")
    require(set(observed_periods) == EXPECTED[table], "SELECTED_COVERAGE",
            "Selected source/adjustment lacks one or more sectors.")
    common_months = next(iter(observed_periods.values()))
    require(all(months == common_months for months in observed_periods.values()),
            "PERIOD_COVERAGE", "Selected sectors do not share monthly coverage.")
    require(len(selected_bases) == 1, "BASE_CONFLICT",
            "Selected observations have mixed index bases.")
    require(results, "SOURCE_EMPTY", "No observations in selected source.")
    return sorted(results, key=lambda item: (
        item["observation"]["period"], item["observation"]["industry_code"]))


def normalize_pair(store: SnapshotStore, profile_by_table: dict) -> list[dict]:
    """Select a coherent two-table vintage. Return observations only if all pass."""
    require(set(profile_by_table) == set(TABLES), "PROFILE_COVERAGE",
            "A verified source profile is needed for both tables.")
    combined = []
    bases = set()
    adjustments = set()
    month_sets = []
    for table in TABLES:
        event = store.latest(table)
        require(event is not None, "ACQUISITION_MISSING",
                "Both source tables must be acquired before normalization.")
        items = normalize_event(store, event, profile_by_table[table])
        combined.extend(items)
        bases.update(x["observation"]["base_year"] for x in items)
        adjustments.update(x["observation"]["adjustment"] for x in items)
        month_sets.append({x["observation"]["period"] for x in items})
    require(all(months == month_sets[0] for months in month_sets),
            "CROSS_TABLE_PERIOD_COVERAGE",
            "Manufacturing aggregate and industry divisions cover different months.")
    require(len(bases) == 1, "BASE_CONFLICT",
            "Manufacturing/sector source tables have inconsistent base years.")
    require(len(adjustments) == 1, "ADJUSTMENT_CONFLICT",
            "Original, calendar and seasonally adjusted sources cannot be mixed.")
    return combined


def _write_exclusive_json(root: Path, name: str, payload: object):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = root / name
    if target.is_symlink():
        raise QualityError("OUTPUT_UNSAFE", "Cannot overwrite a symlinked result.")
    data = (canonical(payload) + "\n").encode("utf-8")
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix="pending-", delete=False) as file:
            tmp = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(tmp, 0o600)
        try:
            os.link(tmp, target, follow_symlinks=False)
        finally:
            tmp.unlink(missing_ok=True)
    except (FileExistsError, OSError) as exc:
        raise QualityError("OUTPUT_WRITE", "Could not persist a new immutable quality result.") from exc
    return str(target)


def run_quality_gate(store: SnapshotStore, profiles: dict) -> dict:
    """Always produces an audit result. Invalid inputs go into quarantine."""
    run_id = str(uuid4())
    root = store.base / "quality"
    try:
        items = normalize_pair(store, profiles)
        # Safety gate: valid normalized observations are still not published.
        report = {"run_id": run_id, "status": "VALIDATED_UNPUBLISHED",
                  "publication_approved": False, "transformation_version": TRANSFORMATION_VERSION,
                  "observation_count": len(items),
                  "results": items, "checked_at": utc_now()}
        location = _write_exclusive_json(root / "validated", run_id + ".json", report)
        return {"status": report["status"], "run_id": run_id,
                "observation_count": len(items), "path": location,
                "publication_approved": False}
    except (QualityError, SnapshotError, KeyError, ValueError, TypeError) as exc:
        code = exc.code if isinstance(exc, QualityError) else "SOURCE_INTEGRITY"
        report = {"run_id": run_id, "status": "QUARANTINED",
                  "publication_approved": False, "reason_code": code,
                  "reason": str(exc)[:400], "transformation_version": TRANSFORMATION_VERSION,
                  "checked_at": utc_now()}
        location = _write_exclusive_json(root / "quarantine", run_id + ".json", report)
        return {"status": report["status"], "run_id": run_id,
                "reason_code": code, "path": location,
                "publication_approved": False}
