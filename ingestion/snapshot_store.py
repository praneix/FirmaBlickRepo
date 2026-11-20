"""FirmaBlick append-only, content-addressed raw acquisition archive (Issue #9).

Local implementation for CI and trusted server-side ingestion. No network access,
cloud credentials, customer data, or publication permissions. Requires Python 3.11+.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

NAMESPACE = "firmablick/v1"
TABLES = frozenset(("42153-0001", "42153-0002"))
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
SAFE_HTTP = frozenset(("http_status", "content_type", "source_last_modified", "source_etag"))
MAX_OBJECT_BYTES = 80 * 1024 * 1024
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS object_blobs (
    sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),
    size_bytes INTEGER NOT NULL CHECK(size_bytes>=0),
    storage_key TEXT NOT NULL UNIQUE,
    first_seen_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acquisitions (
    acquisition_id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK(source='destatis'),
    dataset_id TEXT NOT NULL CHECK(dataset_id IN ('42153-0001', '42153-0002')),
    retrieved_at TEXT NOT NULL,
    source_url TEXT NOT NULL,
    request_json TEXT NOT NULL,
    response_http_json TEXT NOT NULL,
    inventory_json TEXT NOT NULL,
    source_release_at TEXT,
    publication_approved INTEGER NOT NULL DEFAULT 0 CHECK(publication_approved=0),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS acquisition_objects (
    acquisition_id TEXT NOT NULL REFERENCES acquisitions(acquisition_id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK(role IN ('tablefile.zip','metadata.json')),
    sha256 TEXT NOT NULL REFERENCES object_blobs(sha256) ON DELETE RESTRICT,
    PRIMARY KEY (acquisition_id, role)
);
CREATE INDEX IF NOT EXISTS acquisitions_asof_idx
    ON acquisitions(dataset_id, retrieved_at, acquisition_id);
CREATE INDEX IF NOT EXISTS acquisition_objects_sha_idx
    ON acquisition_objects(sha256);
"""
TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS no_blobs_update BEFORE UPDATE ON object_blobs
BEGIN SELECT RAISE(ABORT, 'append-only blob metadata'); END;
CREATE TRIGGER IF NOT EXISTS no_blobs_delete BEFORE DELETE ON object_blobs
BEGIN SELECT RAISE(ABORT, 'append-only blob metadata'); END;
CREATE TRIGGER IF NOT EXISTS no_acquisitions_update BEFORE UPDATE ON acquisitions
BEGIN SELECT RAISE(ABORT, 'append-only acquisitions'); END;
CREATE TRIGGER IF NOT EXISTS no_acquisitions_delete BEFORE DELETE ON acquisitions
BEGIN SELECT RAISE(ABORT, 'append-only acquisitions'); END;
CREATE TRIGGER IF NOT EXISTS no_objects_update BEFORE UPDATE ON acquisition_objects
BEGIN SELECT RAISE(ABORT, 'append-only acquisition objects'); END;
CREATE TRIGGER IF NOT EXISTS no_objects_delete BEFORE DELETE ON acquisition_objects
BEGIN SELECT RAISE(ABORT, 'append-only acquisition objects'); END;
"""


class SnapshotError(Exception):
    """Rejects invalid acquisitions, corrupted source blobs or storage failures."""


def timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def require_utc_timestamp(value: str) -> str:
    if not isinstance(value, str) or not UTC_TIMESTAMP.fullmatch(value):
        raise SnapshotError("Timestamp must be an ISO-8601 UTC value ending in Z.")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError("Invalid UTC timestamp.") from exc
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def safe_http(http: dict) -> dict:
    if not isinstance(http, dict):
        raise SnapshotError("HTTP evidence must be an object.")
    return {key: http[key] for key in SAFE_HTTP if key in http}


def verify_query(query: dict, dataset_id: str) -> dict:
    if not isinstance(query, dict) or query.get("name") != dataset_id:
        raise SnapshotError("Query table must match dataset_id.")
    allowed = {"name", "startyear", "endyear", "format", "language", "area", "compress", "job"}
    if set(query) - allowed or any(not isinstance(v, (str, int, bool)) for v in query.values()):
        raise SnapshotError("Unknown or unsafe acquisition query parameter.")
    if any(word in str(k).lower() for k in query for word in ("password", "token", "secret", "auth")):
        raise SnapshotError("Credentials must never enter provenance.")
    return query.copy()


def validate_namespace(root: Path) -> Path:
    path = Path(root).expanduser()
    if path.is_symlink():
        raise SnapshotError("Snapshot store root cannot be a symlink.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise SnapshotError("Snapshot store root is not a directory.")
    real_root = path.resolve()
    namespace = real_root / NAMESPACE
    current = real_root
    for component in NAMESPACE.split("/"):
        current = current / component
        if current.is_symlink():
            raise SnapshotError("Snapshot namespace cannot contain symlinks.")
        current.mkdir(mode=0o700, exist_ok=True)
    for component in ("objects", "tmp"):
        target = namespace / component
        if target.is_symlink():
            raise SnapshotError("Snapshot object path cannot contain symlinks.")
        target.mkdir(mode=0o700, exist_ok=True)
    try:
        os.chmod(namespace, 0o700)
        os.chmod(namespace / "objects", 0o700)
        os.chmod(namespace / "tmp", 0o700)
    except OSError as exc:
        raise SnapshotError("Cannot secure snapshot namespace.") from exc
    return namespace


class SnapshotStore:
    def __init__(self, root: Path):
        self.base = validate_namespace(root)
        self.objects = self.base / "objects"
        self.tmp = self.base / "tmp"
        self.db_file = self.base / "acquisitions.sqlite3"
        if self.db_file.is_symlink():
            raise SnapshotError("SQLite metadata path cannot be a symlink.")
        try:
            with self._connect() as db:
                db.executescript(SCHEMA)
                db.executescript(TRIGGERS)
            os.chmod(self.db_file, 0o600)
        except (sqlite3.Error, OSError) as exc:
            raise SnapshotError("Cannot initialise local snapshot metadata store.") from exc

    def _connect(self):
        connection = sqlite3.connect(str(self.db_file), timeout=30)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _object_path(self, digest: str) -> Path:
        if not HEX_SHA256.fullmatch(digest):
            raise SnapshotError("Invalid content digest.")
        return self.objects / digest[:2] / digest[2:4] / digest

    def _write_object(self, raw: bytes) -> tuple[str, int, str]:
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_OBJECT_BYTES:
            raise SnapshotError("Raw source artifact must be nonempty bytes within size limit.")
        digest = hashlib.sha256(raw).hexdigest()
        destination = self._object_path(digest)
        parent = destination.parent
        for folder in (parent.parent, parent):
            if folder.is_symlink():
                raise SnapshotError("Blob destination directory cannot be a symlink.")
            folder.mkdir(mode=0o700, exist_ok=True)
        if destination.is_symlink():
            raise SnapshotError("Blob destination cannot be a symlink.")
        if destination.exists():
            # Any corruption is a hard failure, never silently overwrite a content hash.
            if not destination.is_file() or destination.read_bytes() != raw:
                raise SnapshotError("Existing content-addressed object failed integrity check.")
        else:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.tmp, prefix="blob-", delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o600)
                # Atomic creation without overwrite; a concurrent writer may already
                # have created the same digest. Hard link is atomic and no-clobber.
                try:
                    os.link(temporary, destination, follow_symlinks=False)
                except FileExistsError:
                    if destination.is_symlink() or destination.read_bytes() != raw:
                        raise SnapshotError("Concurrent object write did not match digest.")
            except OSError as exc:
                raise SnapshotError("Raw object storage failed; acquisition not recorded.") from exc
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return digest, len(raw), str(destination.relative_to(self.base))

    def archive(self, *, dataset_id: str, archive: bytes, metadata: bytes, source_url: str,
                request: dict, http: dict, inventory: dict, retrieved_at: str | None = None,
                source_release_at: str | None = None) -> dict:
        if dataset_id not in TABLES:
            raise SnapshotError("Unapproved source dataset.")
        if source_url != "https://genesis.destatis.de/genesisWS/rest/2020/":
            raise SnapshotError("Acquisition source must match approved GENESIS endpoint.")
        if not isinstance(inventory, dict) or inventory.get("table") != dataset_id or inventory.get("published_observations") is not False:
            raise SnapshotError("Source inventory must be validated and discovery-only.")
        expected = {"C"} if dataset_id == "42153-0001" else {"20", "24", "28", "29"}
        if set(inventory.get("covered_codes", [])) != expected:
            raise SnapshotError("Incomplete industry source inventory.")
        query = verify_query(request, dataset_id)
        if not isinstance(http, dict) or set(http) != {"tablefile", "metadata"}:
            raise SnapshotError("Both tablefile and metadata HTTP responses are required.")
        stamp = require_utc_timestamp(retrieved_at or timestamp_now())
        source_release_at = require_utc_timestamp(source_release_at) if source_release_at is not None else None
        # JSON serialization validates all untrusted metadata before binary writes.
        try:
            request_json = canonical_json(query)
            response_json = canonical_json({role: safe_http(http[role]) for role in ("tablefile", "metadata")})
            inventory_json = canonical_json(inventory)
        except (ValueError, TypeError) as exc:
            raise SnapshotError("Unserializable or invalid acquisition metadata.") from exc
        digests = {
            "tablefile.zip": self._write_object(archive),
            "metadata.json": self._write_object(metadata),
        }
        acquisition_id = str(uuid4())
        created_at = timestamp_now()
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                for digest, size, key in digests.values():
                    db.execute(
                        "INSERT OR IGNORE INTO object_blobs(sha256,size_bytes,storage_key,first_seen_utc)"
                        " VALUES(?,?,?,?)", (digest, size, key, stamp)
                    )
                    stored = db.execute("SELECT size_bytes,storage_key FROM object_blobs WHERE sha256=?",
                                        (digest,)).fetchone()
                    if stored != (size, key):
                        raise SnapshotError("Existing object metadata conflicts with source artifact.")
                db.execute(
                    "INSERT INTO acquisitions(acquisition_id,source,dataset_id,retrieved_at,source_url,"
                    "request_json,response_http_json,inventory_json,source_release_at,"
                    "publication_approved,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,?)",
                    (acquisition_id, "destatis", dataset_id, stamp, source_url,
                     request_json, response_json, inventory_json, source_release_at, created_at)
                )
                for role, (digest, _, _) in digests.items():
                    db.execute(
                        "INSERT INTO acquisition_objects(acquisition_id,role,sha256) VALUES(?,?,?)",
                        (acquisition_id, role, digest)
                    )
        except sqlite3.Error as exc:
            raise SnapshotError("Metadata transaction failed; no acquisition committed.") from exc
        # Audit file bytes again before returning apparent success.
        for role, (digest, _, _) in digests.items():
            if self.read_object(digest) != (archive if role == "tablefile.zip" else metadata):
                raise SnapshotError("Acquisition integrity verification failed.")
        return {"acquisition_id": acquisition_id, "dataset_id": dataset_id,
                "retrieved_at": stamp, "sha256": {k: v[0] for k, v in digests.items()},
                "publication_approved": False, "namespace": NAMESPACE}

    def read_object(self, digest: str) -> bytes:
        path = self._object_path(digest)
        if path.is_symlink() or not path.is_file():
            raise SnapshotError("Content-addressed object missing or unsafe.")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise SnapshotError("Cannot read source object.") from exc
        if hashlib.sha256(data).hexdigest() != digest:
            raise SnapshotError("Content digest mismatch; corrupted raw data.")
        return data

    def events(self, dataset_id: str, *, as_of: str | None = None) -> list[dict]:
        if dataset_id not in TABLES:
            raise SnapshotError("Unapproved source dataset.")
        if as_of is not None:
            as_of = require_utc_timestamp(as_of)
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            query = ("SELECT acquisition_id,dataset_id,retrieved_at,source_url,request_json,"
                     "response_http_json,inventory_json,source_release_at,publication_approved"
                     " FROM acquisitions WHERE dataset_id=?")
            args = [dataset_id]
            if as_of is not None:
                query += " AND retrieved_at<=?"
                args.append(as_of)
            query += " ORDER BY retrieved_at DESC, acquisition_id DESC"
            rows = db.execute(query, args).fetchall()
            results = []
            for row in rows:
                event = dict(row)
                event["publication_approved"] = bool(event["publication_approved"])
                for key in ("request_json", "response_http_json", "inventory_json"):
                    event[key.removesuffix("_json")] = json.loads(event.pop(key))
                event["objects"] = dict(db.execute(
                    "SELECT role,sha256 FROM acquisition_objects WHERE acquisition_id=?",
                    (event["acquisition_id"],)).fetchall())
                if set(event["objects"]) != {"tablefile.zip", "metadata.json"}:
                    raise SnapshotError("Incomplete source evidence for an acquisition.")
                # Every historic response returned by API is cryptographically verified.
                for digest in event["objects"].values():
                    self.read_object(digest)
                results.append(event)
        return results

    def latest(self, dataset_id: str, *, as_of: str | None = None) -> dict | None:
        observations = self.events(dataset_id, as_of=as_of)
        return observations[0] if observations else None

    def metrics(self) -> dict:
        with self._connect() as db:
            blob_count, size = db.execute("SELECT count(*),coalesce(sum(size_bytes),0) FROM object_blobs").fetchone()
            count = db.execute("SELECT count(*) FROM acquisitions").fetchone()[0]
            publications = db.execute("SELECT count(*) FROM acquisitions WHERE publication_approved!=0").fetchone()[0]
        return {"distinct_blobs": blob_count, "blob_bytes": size,
                "acquisition_events": count, "published": publications}
