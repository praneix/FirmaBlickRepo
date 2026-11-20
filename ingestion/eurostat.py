"""Eurostat JSON-stat 2.0 adapter and fail-closed cross-source reconciler.

All data remain unpublished. Eurostat revisions are persisted locally as original
response bytes with retrieval events, never substituted for Destatis observations.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from uuid import uuid4

URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_inpr_m"
CODES = {"C", "C20", "C24", "C28", "C29"}
DIMENSIONS = {"freq", "indic_bt", "nace_r2", "s_adj", "unit", "geo", "time"}
MAX_RESPONSE = 20 * 1024 * 1024
ADJUSTMENTS = {"NSA": "original", "CA": "calendar_adjusted",
               "SA": "seasonally_adjusted", "SCA": "seasonal_calendar_adjusted"}
HTTP_RETRY = {429, 500, 502, 503, 504}
MISSING_FLAGS = {"c", "u", "z"}  # Preserve all source codes even if semantics unverified.


class EurostatError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def category_codes(dim):
    if not isinstance(dim, dict) or "category" not in dim:
        raise EurostatError("JSON-stat category metadata missing.")
    category = dim["category"]
    index = category.get("index")
    if isinstance(index, dict):
        indices = index
    elif isinstance(index, list):
        indices = {code: i for i, code in enumerate(index)}
    else:
        raise EurostatError("JSON-stat category index malformed.")
    if len(set(indices.values())) != len(indices) or any(
        not isinstance(i, int) or i < 0 for i in indices.values()
    ):
        raise EurostatError("JSON-stat category indices invalid or duplicated.")
    return indices


def validate_jsonstat(payload):
    if not isinstance(payload, dict) or payload.get("version") != "2.0" or payload.get("class") != "dataset":
        raise EurostatError("Expected Eurostat JSON-stat 2.0 dataset.")
    ids = payload.get("id", [])
    sizes = payload.get("size", [])
    dims = payload.get("dimension", {})
    if not isinstance(ids, list) or not isinstance(sizes, list) or set(ids) != DIMENSIONS:
        raise EurostatError("Missing, extra or unknown Eurostat dimensions.")
    if len(ids) != len(sizes) or len(set(ids)) != len(ids):
        raise EurostatError("Invalid JSON-stat dimension order.")
    categories = {}
    size = 1
    for name, expected_size in zip(ids, sizes):
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise EurostatError("Invalid JSON-stat dimension size.")
        code_map = category_codes(dims.get(name))
        if len(code_map) != expected_size or set(code_map.values()) != set(range(expected_size)):
            raise EurostatError("JSON-stat dimension category count or positions mismatch.")
        categories[name] = code_map
        size *= expected_size
        if size > 2_000_000:
            raise EurostatError("Eurostat response exceeds safe cell limit.")
    vals = payload.get("value", {})
    flags = payload.get("status", {})
    if not isinstance(vals, (list, dict)) or not isinstance(flags, (list, dict)):
        raise EurostatError("JSON-stat value/status containers invalid.")
    return ids, sizes, categories, size


def get_cell(container, i):
    return container[i] if isinstance(container, list) and i < len(container) else (
        container.get(str(i)) if isinstance(container, dict) else None)


def flat_index(ids, sizes, categories, selected):
    pos = 0
    for key, extent in zip(ids, sizes):
        v = selected[key]
        if v not in categories[key]:
            return None
        pos = pos * extent + categories[key][v]
    return pos


def normalize(payload, *, classification="NACE_REV2"):
    ids, sizes, categories, _ = validate_jsonstat(payload)
    if classification != "NACE_REV2":
        raise EurostatError("NACE Rev. 2.1 conversion not approved; keep separate.")
    for name, code in (("geo", "DE"), ("freq", "M"), ("indic_bt", "PRD")):
        if code not in categories[name]:
            raise EurostatError(f"Required Eurostat {name} category missing: {code}")
    for name in ("s_adj", "unit", "nace_r2"):
        if not categories[name]:
            raise EurostatError(f"Eurostat {name} metadata empty.")
    output = []
    for nace in sorted(CODES):
        if nace not in categories["nace_r2"]:
            continue
        for adjust in categories["s_adj"]:
            if adjust not in ADJUSTMENTS:
                continue
            for unit in categories["unit"]:
                # Only inspect index units with an explicit index base.
                match = re.fullmatch(r"I(20\d{2}|\d{2})", unit)
                if not match:
                    continue
                base = int(match.group(1))
                if base < 100:
                    base += 2000
                for period in categories["time"]:
                    if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", period):
                        raise EurostatError("Unexpected Eurostat monthly period format.")
                    selection = {"geo": "DE", "freq": "M", "indic_bt": "PRD",
                                 "nace_r2": nace, "s_adj": adjust, "unit": unit, "time": period}
                    pos = flat_index(ids, sizes, categories, selection)
                    value = get_cell(payload.get("value", {}), pos)
                    status = get_cell(payload.get("status", {}), pos)
                    if value is not None and (not isinstance(value, (int, float)) or
                                              isinstance(value, bool) or not math.isfinite(value)):
                        raise EurostatError("Invalid Eurostat numeric value.")
                    if status is not None and not isinstance(status, str):
                        raise EurostatError("Invalid Eurostat status value.")
                    output.append({
                        "source_id": "eurostat", "dataset_id": "sts_inpr_m",
                        "geo": "DE", "frequency": "M", "period": period,
                        "industry_code": nace, "classification_revision": classification,
                        "adjustment": ADJUSTMENTS[adjust], "unit": "index",
                        "base_year": base, "value": value,
                        "source_status_flags": [] if not status else list(status),
                        "raw_dimensions": selection, "source_cell_index": pos,
                    })
    if not output:
        raise EurostatError("No recognised monthly German industrial index series.")
    return output


def fetch(*, transport=urlopen, sleep=time.sleep, attempts=3, params=None):
    params = dict(params or {})
    defaults = {"geo": "DE", "freq": "M", "indic_bt": "PRD", "lang": "EN"}
    defaults.update(params)
    if defaults.get("geo") != "DE" or defaults.get("freq") != "M" or defaults.get("indic_bt") != "PRD":
        raise EurostatError("Only monthly German industrial production is approved.")
    if not set(defaults).issubset({"geo", "freq", "indic_bt", "lang", "sinceTimePeriod", "untilTimePeriod"}):
        raise EurostatError("Unapproved Eurostat query dimension.")
    url = URL + "?" + urlencode(defaults)
    for attempt in range(attempts):
        try:
            with transport(Request(url, headers={"Accept":"application/json",
                                                 "User-Agent":"FirmaBlick-Source-Verification/1.0"}),
                           timeout=60) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise EurostatError("Eurostat dataset exceeds safety limit.")
                metadata = {"http_status": response.status,
                            "content_type": response.headers.get("Content-Type", ""),
                            "etag": response.headers.get("ETag"),
                            "last_modified": response.headers.get("Last-Modified")}
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise EurostatError("Invalid Eurostat JSON response.") from exc
                validate_jsonstat(payload)
                return raw, metadata, defaults
        except HTTPError as exc:
            if exc.code in HTTP_RETRY and attempt + 1 < attempts:
                sleep(min(2 ** attempt, 8))
                continue
            raise EurostatError(f"Eurostat HTTP {exc.code}. Check dataset availability.") from None
        except (URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                sleep(min(2 ** attempt, 8))
                continue
            raise EurostatError("Eurostat network unavailable after retries.") from exc
    raise EurostatError("Eurostat retries exhausted.")


class EurostatArchive:
    """Independent local-only archive. No Destatis ledger, Supabase or publication writes."""
    def __init__(self, root):
        root = Path(root)
        if root.is_symlink():
            raise EurostatError("Storage root must not be a symlink.")
        self.root = root / "firmablick" / "v1" / "eurostat"
        part = root
        for name in ("firmablick", "v1", "eurostat"):
            part = part / name
            if part.is_symlink():
                raise EurostatError("Eurostat archive directory must not be a symlink.")
            part.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(part, 0o700)
        self.blobs = self.root / "objects"
        self.blobs.mkdir(exist_ok=True, mode=0o700)
        os.chmod(self.blobs, 0o700)
        self.dbpath = self.root / "acquisitions.sqlite3"
        if self.dbpath.is_symlink():
            raise EurostatError("Archive DB must not be a symlink.")
        with sqlite3.connect(self.dbpath) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS blobs (
                    digest TEXT PRIMARY KEY, size INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS acquisitions (
                    id TEXT PRIMARY KEY, received_utc TEXT NOT NULL, digest TEXT NOT NULL
                    REFERENCES blobs(digest), request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL, source_updated TEXT,
                    publication_approved INTEGER NOT NULL DEFAULT 0 CHECK(publication_approved=0));
                CREATE INDEX IF NOT EXISTS eurostat_asof ON acquisitions(received_utc,id);
                CREATE TRIGGER IF NOT EXISTS no_eu_blob_update BEFORE UPDATE ON blobs
                    BEGIN SELECT RAISE(ABORT,'immutable'); END;
                CREATE TRIGGER IF NOT EXISTS no_eu_blob_delete BEFORE DELETE ON blobs
                    BEGIN SELECT RAISE(ABORT,'immutable'); END;
                CREATE TRIGGER IF NOT EXISTS no_eu_event_update BEFORE UPDATE ON acquisitions
                    BEGIN SELECT RAISE(ABORT,'immutable'); END;
                CREATE TRIGGER IF NOT EXISTS no_eu_event_delete BEFORE DELETE ON acquisitions
                    BEGIN SELECT RAISE(ABORT,'immutable'); END;
                """)
        os.chmod(self.dbpath, 0o600)

    def archive(self, raw, response, params, *, received=None):
        payload = json.loads(raw)
        validate_jsonstat(payload)
        if not isinstance(response, dict) or not isinstance(params, dict):
            raise EurostatError("Invalid response/request metadata.")
        if not set(params).issubset({"geo","freq","indic_bt","lang","sinceTimePeriod","untilTimePeriod"}):
            raise EurostatError("Unsafe Eurostat request parameter.")
        if params.get("geo") != "DE" or params.get("freq") != "M" or params.get("indic_bt") != "PRD":
            raise EurostatError("Invalid response scope.")
        digest = sha(raw)
        location = self.blobs / digest
        if location.is_symlink():
            raise EurostatError("Unsafe object path.")
        if location.exists():
            if location.read_bytes() != raw:
                raise EurostatError("Previously archived Eurostat raw bytes corrupted.")
        else:
            with tempfile.NamedTemporaryFile(dir=self.blobs, delete=False) as handle:
                tmp = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o600)
            try:
                os.link(tmp, location)
            except FileExistsError:
                if location.is_symlink() or location.read_bytes() != raw:
                    raise EurostatError("Concurrent object conflict.")
            finally:
                tmp.unlink(missing_ok=True)
        stamp = received or utc_now()
        try:
            dt = datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if not stamp.endswith("Z") or dt.utcoffset().total_seconds() != 0:
                raise ValueError("UTC required")
            stamp = dt.isoformat(timespec="microseconds").replace("+00:00","Z")
        except (ValueError, AttributeError) as exc:
            raise EurostatError("Invalid retrieval UTC.") from exc
        allowed_http = {k:response[k] for k in ("http_status","content_type","etag","last_modified") if k in response}
        event_id = str(uuid4())
        try:
            with sqlite3.connect(self.dbpath) as db:
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("INSERT OR IGNORE INTO blobs(digest,size) VALUES(?,?)",(digest,len(raw)))
                db.execute("INSERT INTO acquisitions(id,received_utc,digest,request_json,response_json,source_updated) VALUES(?,?,?,?,?,?)",
                           (event_id, stamp, digest, json_canonical(params),
                            json_canonical(allowed_http),payload.get("updated")))
        except sqlite3.Error as exc:
            raise EurostatError("Archive transaction failed; source remains unpublished.") from exc
        return {"acquisition_id":event_id,"retrieved_at":stamp,"raw_sha256":digest,
                "publication_approved":False}

    def events(self, *, as_of=None):
        if as_of is not None:
            try:
                dt = datetime.fromisoformat(as_of.replace("Z","+00:00"))
                if not as_of.endswith("Z") or dt.utcoffset().total_seconds() != 0:
                    raise ValueError()
                as_of=dt.isoformat(timespec="microseconds").replace("+00:00","Z")
            except (ValueError, AttributeError) as exc:
                raise EurostatError("Invalid as-of timestamp.") from exc
        with sqlite3.connect(self.dbpath) as db:
            rows=db.execute("SELECT id,received_utc,digest,source_updated FROM acquisitions "
                            + ("WHERE received_utc<=? " if as_of else "")
                            + "ORDER BY received_utc DESC,id DESC",
                            (as_of,) if as_of else ()).fetchall()
        output=[]
        for id_,stamp,digest,updated in rows:
            location=self.blobs/digest
            if location.is_symlink() or not location.is_file():
                raise EurostatError("Missing or unsafe stored Eurostat raw response.")
            raw=location.read_bytes()
            if sha(raw)!=digest:
                raise EurostatError("Eurostat raw snapshot digest mismatch.")
            output.append({"acquisition_id":id_,"retrieved_at":stamp,
                           "raw_sha256":digest,"source_updated":updated,
                           "publication_approved":False})
        return output


def reconcile(destatis, eurostat, *, absolute_tolerance=0.2, mapping_verified=False):
    """Compare already normalized observations. Report every excluded pair and reason.

    Never automatically rebase, reclassify, modify or publish Destatis data.
    """
    if isinstance(absolute_tolerance,bool) or not isinstance(absolute_tolerance,(float,int)) or not 0 <= absolute_tolerance <= 10:
        raise EurostatError("Invalid absolute index tolerance.")
    result={"compared":[],"excluded":[],"publication_approved":False,
            "classification_mapping_verified": mapping_verified is True,
            "tolerance_index_points":absolute_tolerance}
    index={}
    for item in eurostat:
        key=(item.get("industry_code"),item.get("period"))
        index.setdefault(key,[]).append(item)
    names={"C":"C","20":"C20","24":"C24","28":"C28","29":"C29"}
    seen=set()
    for raw in destatis:
        d=raw.get("observation",raw)
        code=names.get(d.get("industry_code"))
        key=(code,d.get("period"))
        if not code:
            result["excluded"].append({"key":key,"reason":"industry_unmapped"});continue
        options=index.get(key,[])
        if not options:
            result["excluded"].append({"key":key,"reason":"missing_comparator"});continue
        matched=False
        reasons=set()
        for e in options:
            reason=None
            if e.get("geo")!=d.get("geo") or e.get("frequency")!=d.get("frequency"):
                reason="geography_or_frequency_mismatch"
            elif mapping_verified is not True or e.get("classification_revision")!="NACE_REV2" or d.get("classification_revision")!="WZ2008":
                reason="classification_mapping_not_verified"
            elif e.get("unit")!=d.get("unit") or e.get("base_year")!=d.get("base_year"):
                reason="index_unit_or_base_mismatch"
            elif e.get("adjustment")!=d.get("adjustment"):
                reason="adjustment_mismatch"
            elif e.get("value") is None or d.get("value") is None:
                reason="missing_observation"
            elif not isinstance(e.get("value"),(int,float)) or not isinstance(d.get("value"),(int,float)):
                reason="invalid_observation"
            if reason:
                reasons.add(reason);continue
            diff=round(float(e["value"])-float(d["value"]),10)
            # The same sector/month/adjustment/base must be unique.
            duplicates = [item for item in options if item.get("geo")==e.get("geo")
                          and item.get("frequency")==e.get("frequency")
                          and item.get("classification_revision")==e.get("classification_revision")
                          and item.get("unit")==e.get("unit")
                          and item.get("base_year")==e.get("base_year")
                          and item.get("adjustment")==e.get("adjustment")]
            if len(duplicates) > 1:
                reasons.add("ambiguous_comparator_duplicate")
                continue
            result["compared"].append({"key":key,"destatis":d["value"],"eurostat":e["value"],
                                       "difference_index_points":diff,
                                       "assessment":"exact" if diff==0 else ("within_tolerance" if abs(diff)<=absolute_tolerance else "deviation"),
                                       "source_vintages":{"destatis":d.get("raw_snapshot_id"),
                                                          "eurostat":e.get("acquisition_id")}})
            matched=True
            break
        if not matched:
            result["excluded"].append({"key":key,"reason":";".join(sorted(reasons)) or "no_comparable_series"})
        seen.add(key)
    for key in index:
        if key not in seen:
            result["excluded"].append({"key":key,"reason":"missing_primary"})
    result["summary"]={"compared":len(result["compared"]),"excluded":len(result["excluded"]),
                       "deviations":sum(x["assessment"]=="deviation" for x in result["compared"])}
    return result

def cli(argv=None):
    """Opt-in live Eurostat retrieval; never publishes or touches Destatis."""
    import argparse
    parser=argparse.ArgumentParser(description="Eurostat industrial production comparator snapshots")
    parser.add_argument("command",choices=("fetch","history"))
    parser.add_argument("--output",default="artifacts/eurostat")
    parser.add_argument("--since",default="2021-01")
    options=parser.parse_args(argv)
    try:
        arc=EurostatArchive(options.output)
        if options.command=="history":
            print(json.dumps(arc.events(),indent=2))
        else:
            if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])",options.since):
                raise EurostatError("Invalid start month.")
            raw,http,params=fetch(params={"sinceTimePeriod":options.since})
            parsed=json.loads(raw)
            rows=normalize(parsed)
            observed={x["industry_code"] for x in rows}
            if observed!=CODES:
                raise EurostatError("Required five industry series are incomplete.")
            event=arc.archive(raw,http,params)
            print(json.dumps({"status":"raw_snapshot_archived","event":event,
                              "series_codes":sorted(observed),
                              "records":len(rows),"published":False},indent=2))
        return 0
    except (EurostatError,OSError,ValueError) as exc:
        print("Eurostat ingestion blocked: "+str(exc),file=__import__("sys").stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(cli())
