#!/usr/bin/env python3
"""Validate an ephemeral, source-backed historical preview. No data publication.

Run *after* scripts/build-verified-history-preview.py generated site/data/historical.json.
Only sanitized summary metadata is printed. Fails closed on provenance or policy mismatch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

CODES={"C":"42153-0001","20":"42153-0002","24":"42153-0002","28":"42153-0002","29":"42153-0002"}
EXPECTED_COMPARATOR="65906eb5bcd853bf1b6f85c60d16d7d9f60fed9eace673daa4c2b5846e30c694"
VALID_HEX="0123456789abcdef"
def require(condition,message):
    if not condition: raise ValueError(message)

def verify(path:Path)->dict:
    raw=path.read_bytes()
    d=json.loads(raw)
    require(d.get("schema_version")=="1.0.0","SCHEMA_MISMATCH")
    require(d.get("status")=="preview_validated","PREVIEW_STATE_INVALID")
    require(d.get("release_scope")=="protected_vercel_preview_only","PREVIEW_SCOPE_INVALID")
    require(d.get("public_release_authorized") is False,"PUBLIC_RELEASE_MUST_BE_FALSE")
    require(d.get("verification")=="705_of_705_exact","PARITY_ATTESTATION_MISSING")
    require(d.get("comparator_raw_sha256")==EXPECTED_COMPARATOR,"COMPARATOR_SOURCE_HASH_CHANGED")
    require(d.get("comparator_dataset")=="Eurostat sts_inpr_m","COMPARATOR_DATASET_CHANGED")
    require(d.get("source_quality_caveat")=="GENESIS FFCsv does not supply per-cell release/revision flags","QUALITY_CAVEAT_MISSING")
    require(isinstance(d.get("series"),list) and len(d["series"])==5,"FIVE_SERIES_REQUIRED")
    retrieved=set()
    seen=set()
    source_hashes=set()
    for s in d["series"]:
        code=s.get("industry_code")
        require(code in CODES and code not in seen,"SERIES_DUPLICATE_OR_UNKNOWN")
        seen.add(code)
        require(s.get("dataset_id")==CODES[code],"TABLE_MAPPING_WRONG")
        require(s.get("source")=="Destatis GENESIS" and s.get("source_url","").startswith("https://genesis.destatis.de/"),"SOURCE_IDENTITY_WRONG")
        require((s.get("geo"),s.get("frequency"),s.get("unit"),s.get("base_year"),s.get("classification"),s.get("adjustment"))==("DE","M","index",2021,"WZ2008","original"),"SERIES_DIMENSIONS_WRONG")
        require(s.get("official_verification") is True and s.get("publication_approved") is False and s.get("preview_verified") is True,"SERIES_PUBLICATION_GUARD")
        sha=s.get("raw_sha256","")
        require(len(sha)==64 and all(v in VALID_HEX for v in sha),"BAD_RAW_HASH")
        source_hashes.add(sha)
        require(s.get("acquisition_id"),"ACQUISITION_ID_REQUIRED")
        dt=datetime.fromisoformat(s["retrieved_at"].replace("Z","+00:00"))
        require(dt.tzinfo is not None and dt<=datetime.now(timezone.utc),"INVALID_ACQUISITION_VINTAGE")
        retrieved.add(s["retrieved_at"])
        rows=s.get("observations")
        require(isinstance(rows,list) and len(rows)==141,"PER_SECTOR_PERIOD_COUNT")
        months=[r.get("period") for r in rows]
        require(months[0]=="2015-01" and months[-1]=="2026-09" and len(set(months))==141 and months==sorted(months),"PERIOD_INTEGRITY")
        for r in rows:
            require(isinstance(r.get("value"),(float,int)) and not isinstance(r.get("value"),bool) and 0<=r["value"]<1000000,"BAD_OR_MISSING_INDEX_VALUE")
            require(r.get("missing_reason") is None,"INVALID_MISSING_STATE")
            require(r.get("source_status_flags")==["source_quality_field_not_provided"],"UNSUPPORTED_SOURCE_REVISION_STATUS")
    require(seen==set(CODES),"INDUSTRY_COVERAGE")
    require(len(source_hashes)==2,"DESTATIS_TWO_SOURCE_OBJECTS_REQUIRED")
    require(len(retrieved)==2,"ACQUISITION_EVENT_EXPECTATION_CHANGED")
    manifest={
        "schema_version":"1.0.0",
        "evidence_state":"RECONSTRUCTED_PROTECTED_PREVIEW_ONLY",
        "public_release_authorized":False,
        "approved_for_commercial_use":False,
        "source_dataset_ids":sorted(set(CODES.values())),
        "source_retrieval_vintages_utc":sorted(retrieved),
        "source_raw_sha256":sorted(source_hashes),
        "comparator_raw_sha256":EXPECTED_COMPARATOR,
        "source_quality_flag_available":False,
        "classification":"WZ2008",
        "unit":"industrial production index, 2021=100, original unadjusted",
        "observations":705,
        "industries":sorted(CODES),
        "first_period":"2015-01",
        "last_period":"2026-09",
        "generated_json_sha256":hashlib.sha256(raw).hexdigest()
    }
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="site/data/historical.json")
    p.add_argument("--manifest",default="/tmp/firmablick-historical-preview-manifest.json")
    args=p.parse_args()
    try:
        result=verify(Path(args.input))
        Path(args.manifest).write_text(json.dumps(result,indent=2)+"\n")
        print("FIRMABLICK_705_ORIGINAL_VERIFIED_PROTECTED_ONLY")
        print("Source period: 2015-01..2026-09; 5 sectors; no released forecast or public approval")
        print("Generated preview JSON SHA256:",result["generated_json_sha256"])
    except Exception as e:
        raise SystemExit("PREVIEW_VALIDATION_BLOCKED: "+str(e))
