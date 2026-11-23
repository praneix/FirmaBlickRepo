#!/usr/bin/env python3
"""Owner-only asset ingestion preflight. Does not upload or publish.
Usage: python3 scripts/verify-private-report-assets.py <full.pdf> <sample.pdf>
Check exact local bytes against the pinned registry, then upload via a restricted,
server-side process only after an approved release and authenticated storage exist.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"product/registry/energy-v4.review.json"
MAN=ROOT/"research/energy/v4_candidate_manifest.json"
def check(path:Path,expected:str):
    if not path.is_file():raise ValueError("ASSET_MISSING")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=expected:raise ValueError("ASSET_SHA256_MISMATCH")
    with path.open("rb") as f:
        if f.read(5)!=b"%PDF-":raise ValueError("ASSET_NOT_PDF")
    return {"sha256":digest,"size_bytes":path.stat().st_size}
def run(full:Path,sample:Path):
    reg=json.loads(REG.read_text())
    manifest=json.loads(MAN.read_text())
    ver=reg["versions"][0]
    assert manifest["revision"]==ver["revision"]
    assert manifest["full_pdf_sha256"]==ver["full_pdf_sha256"]
    assert manifest["sample_pdf_sha256"]==ver["sample_pdf_sha256"]
    assert reg["publication_approved"] is False and ver["publication_approved"] is False
    assert not reg["price_approved"] and not manifest["publication_approved"]
    data={"report_id":reg["report_id"],"revision":ver["revision"],
          "full":check(full,ver["full_pdf_sha256"]),
          "sample":check(sample,ver["sample_pdf_sha256"])}
    return {"status":"PRIVATE_ASSET_HASHES_VERIFIED_UNPUBLISHED",**data}
if __name__=="__main__":
    try:
        if len(sys.argv)!=3:raise ValueError("Pass full.pdf and sample.pdf paths")
        print(json.dumps(run(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
    except Exception as e:
        print("PRIVATE_ASSET_VERIFICATION_BLOCKED:",str(e),file=sys.stderr)
        raise SystemExit(2)
