#!/usr/bin/env python3
"""Verify the private original source archives after restoring them from durable storage.
Usage: python3 scripts/verify-restored-statistical-archives.py DESTATIS.zip EUROSTAT.zip
Uses only Python stdlib. Fail-closed; prints source checksums and numerical parity only.
"""
import csv,hashlib,io,json,sqlite3,sys,tempfile
from pathlib import Path
from decimal import Decimal
from zipfile import ZipFile
CHECKSUMS={
"destatis":"568b6d514643c85a777dc21e9cecf6aa36d2d8fe12bdf4a1e5ebef986a80d3de",
"eurostat":"65906eb5bcd853bf1b6f85c60d16d7d9f60fed9eace673daa4c2b5846e30c694"}
CODES={"C":"C","20":"C20","24":"C24","28":"C28","29":"C29"}
def require(ok,message):
    if not ok:raise ValueError(message)
def unpack(path,digest,target):
    require(hashlib.sha256(path.read_bytes()).hexdigest()==digest,"ORIGINAL_ARCHIVE_SHA256_MISMATCH")
    with ZipFile(path) as z:
        require(len(z.infolist())<=20 and sum(e.file_size for e in z.infolist())<20_000_000,"UNEXPECTED_ARCHIVE_EXPANSION")
        for e in z.infolist():
            p=Path(e.filename)
            require(not p.is_absolute() and ".." not in p.parts,"ARCHIVE_PATH_TRAVERSAL")
        z.extractall(target)
def object_bytes(root,sha,nested=False):
    require(len(sha)==64 and all(x in "0123456789abcdef" for x in sha),"INVALID_HASH")
    path=root/"objects"/sha[:2]/sha[2:4]/sha if nested else root/"objects"/sha
    b=path.read_bytes()
    require(hashlib.sha256(b).hexdigest()==sha,"SOURCE_OBJECT_HASH_MISMATCH")
    return b
def destatis(root):
    with sqlite3.connect(root/"acquisitions.sqlite3") as db:
        acquisitions=db.execute("SELECT acquisition_id,dataset_id,publication_approved FROM acquisitions").fetchall()
        require(len(acquisitions)==2 and {a[1] for a in acquisitions}=={"42153-0001","42153-0002"},"DEST_ACQUISITION_INCOMPLETE")
        require(all(a[2]==0 for a in acquisitions),"PUBLICATION_APPROVAL_UNEXPECTED")
        objects=db.execute("SELECT sha256,size_bytes FROM object_blobs").fetchall()
        require(len(objects)==4,"DEST_BLOB_INVENTORY_INCOMPLETE")
        for sha,size in objects:require(len(object_bytes(root,sha,True))==size,"DEST_BLOB_SIZE_MISMATCH")
        observations={}
        for acquisition,dataset,_ in acquisitions:
            roles=dict(db.execute("SELECT role,sha256 FROM acquisition_objects WHERE acquisition_id=?",(acquisition,)).fetchall())
            require(set(roles)=={"metadata.json","tablefile.zip"},"DEST_ROLES_MISSING")
            object_bytes(root,roles["metadata.json"],True)
            with ZipFile(io.BytesIO(object_bytes(root,roles["tablefile.zip"],True))) as source:
                members=[n for n in source.namelist() if n.lower().endswith(".csv")]
                require(len(members)==1,"DEST_CSV_MISSING")
                rows=csv.DictReader(io.StringIO(source.read(members[0]).decode("utf-8-sig")),delimiter=";")
                for row in rows:
                    dims={v for k,v in row.items() if k.endswith("_variable_attribute_code")}
                    if "WERTORG" not in dims:continue
                    industry=[code for code in CODES if "WZ08-"+code in dims]
                    if len(industry)!=1:continue
                    code=industry[0]
                    if (dataset=="42153-0001")!=(code=="C"):continue
                    month=[v for v in dims if v.startswith("MONAT") and len(v)==7]
                    require(len(month)==1,"DEST_MONTH_AMBIGUOUS")
                    period=row["time"]+"-"+month[0][-2:]
                    require(row["value_unit"].replace(" ","")=="2021=100" and row["value_variable_code"]=="PRO101","DEST_UNITS_MISMATCH")
                    value=Decimal(row["value"].replace(",","."))
                    require(value.is_finite() and value>=0,"DEST_VALUE_INVALID")
                    key=(CODES[code],period)
                    require(key not in observations,"DEST_DUPLICATE_OBSERVATION")
                    observations[key]=value
    require(len(observations)==705,"DEST_OBSERVATIONS_NOT_705")
    for sector in CODES.values():
        periods=sorted(t for s,t in observations if s==sector)
        require(len(periods)==141 and periods[0]=="2015-01" and periods[-1]=="2026-09","DEST_PERIOD_COVERAGE")
    return observations
def eurostat(root,observations):
    with sqlite3.connect(root/"acquisitions.sqlite3") as db:
        entries=db.execute("SELECT digest,publication_approved FROM acquisitions").fetchall()
        require(len(entries)==1 and entries[0][1]==0,"EU_ACQUISITION_INVALID")
        digest=entries[0][0]
        inventory=db.execute("SELECT digest,size FROM blobs").fetchall()
        require(len(inventory)==1 and inventory[0][0]==digest,"EU_BLOB_INVENTORY")
        b=object_bytes(root,digest)
        require(len(b)==inventory[0][1],"EU_BLOB_SIZE")
    data=json.loads(b)
    require(data["version"]=="2.0" and data["class"]=="dataset","EU_JSONSTAT_INVALID")
    dimensions={name:data["dimension"][name]["category"]["index"] for name in data["id"]}
    for name,value in {"geo":{"DE":0},"unit":{"I21":0},"s_adj":{"NSA":0},"indic_bt":{"PRD":0},"freq":{"M":0}}.items():
        require(dimensions[name]==value,"EU_DEFINITIONS_MISMATCH")
    require(set(dimensions["nace_r2"])==set(CODES.values()) and len(dimensions["time"])==141,"EU_COVERAGE")
    for (sector,month),value in observations.items():
        n=dimensions["nace_r2"][sector]*141+dimensions["time"][month]
        observed=data["value"][str(n)] if isinstance(data["value"],dict) else data["value"][n]
        require(observed is not None and Decimal(str(observed))==value,"CROSS_SOURCE_MISMATCH_"+sector+"_"+month)
    return digest
def run(dest_zip,eu_zip):
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        unpack(dest_zip,CHECKSUMS["destatis"],root/"dest")
        unpack(eu_zip,CHECKSUMS["eurostat"],root/"eu")
        observations=destatis(root/"dest/genesis/firmablick/v1")
        eu_digest=eurostat(root/"eu/eurostat/firmablick/v1/eurostat",observations)
    return {"status":"VERIFIED_RESTORED_UNPUBLISHED","matches":len(observations),"sectors":5,"months_each":141,"eu_source_digest":eu_digest,"archive_sha256":CHECKSUMS,"publication_approved":False}
if __name__=="__main__":
    require(len(sys.argv)==3,"Pass DESTATIS.zip EUROSTAT.zip")
    try:print(json.dumps(run(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
    except Exception as e:
        print("ARCHIVE_RESTORE_VERIFICATION_FAILED: "+str(e),file=sys.stderr)
        sys.exit(2)
