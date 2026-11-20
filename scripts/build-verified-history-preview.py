"""Generate protected-preview-only five-series data from independently archived official sources.
Execution is ephemeral in GitHub Actions. Do not commit generated observations to Git.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from decimal import Decimal
from collections import defaultdict
import csv, hashlib, io, json, sqlite3, sys

CODES={"C":"C","20":"C20","24":"C24","28":"C28","29":"C29"}
RAW_ROOT=Path("artifacts/source/destatis/genesis/firmablick/v1")
EU_ROOT=Path("artifacts/source/eurostat/eurostat/firmablick/v1/eurostat")

def check(cond,message):
    if not cond: raise RuntimeError(message)

def object_bytes(root, sha):
    check(len(sha)==64 and all(c in "0123456789abcdef" for c in sha),"Invalid raw hash")
    path=root/"objects"/sha[:2]/sha[2:4]/sha if root==RAW_ROOT else root/"objects"/sha
    raw=path.read_bytes()
    check(hashlib.sha256(raw).hexdigest()==sha,"Source archive SHA256 mismatch")
    return raw

def main():
    db=sqlite3.connect(RAW_ROOT/"acquisitions.sqlite3")
    rows=db.execute("SELECT acquisition_id,dataset_id,retrieved_at FROM acquisitions").fetchall()
    check(len(rows)==2 and {x[1] for x in rows}=={"42153-0001","42153-0002"},"Unexpected Destatis acquisition count")
    found={}
    lineage={}
    for event,table,retrieved in rows:
        refs=dict(db.execute("SELECT role,sha256 FROM acquisition_objects WHERE acquisition_id=?",(event,)).fetchall())
        check(set(refs)=={"tablefile.zip","metadata.json"},"Incomplete authentic source lineage")
        object_bytes(RAW_ROOT,refs["metadata.json"])
        raw=object_bytes(RAW_ROOT,refs["tablefile.zip"])
        with ZipFile(io.BytesIO(raw)) as z:
            members=[x for x in z.namelist() if x.lower().endswith(".csv")]
            check(len(members)==1,"Unexpected Destatis table archive")
            source_rows=csv.DictReader(io.StringIO(z.read(members[0]).decode("utf-8-sig")),delimiter=";")
            for row in source_rows:
                dims={v for k,v in row.items() if k.endswith("_variable_attribute_code")}
                if "WERTORG" not in dims: continue
                codes=[k for k in CODES if "WZ08-"+k in dims]
                if len(codes)!=1:continue
                industry=codes[0]
                if table=="42153-0001" and industry!="C":continue
                if table=="42153-0002" and industry=="C":continue
                mons=[v for v in dims if v.startswith("MONAT") and len(v)==7 and v[-2:].isdigit()]
                check(len(mons)==1 and "2015"<=row["time"]<="2026","Unexpected source period")
                period=row["time"]+"-"+mons[0][-2:]
                check(row["value_unit"].replace(" ","")=="2021=100" and row["value_variable_code"]=="PRO101","Wrong source index")
                value=Decimal(row["value"].replace(",","."))
                check(value.is_finite() and value>=0,"Invalid index value")
                key=(CODES[industry],period)
                check(key not in found,"Duplicate canonical period")
                found[key]=value
                lineage[key]=(refs["tablefile.zip"],event,retrieved,table)
    check(len(found)==705 and {x[0] for x in found}=={"C","C20","C24","C28","C29"},"Incomplete original Destatis series")
    with sqlite3.connect(EU_ROOT/"acquisitions.sqlite3") as eudb:
        acquisitions=eudb.execute("SELECT digest,received_utc FROM acquisitions").fetchall()
    check(len(acquisitions)==1,"Expected single pinned Eurostat vintage")
    digest,eu_retrieved=acquisitions[0]
    eu=json.loads(object_bytes(EU_ROOT,digest))
    check(eu["version"]=="2.0" and eu["class"]=="dataset","Eurostat response not JSON-stat v2")
    dim={key:eu["dimension"][key]["category"]["index"] for key in eu["id"]}
    check(dim["geo"]=={"DE":0} and dim["unit"]=={"I21":0} and
          dim["s_adj"]=={"NSA":0} and dim["indic_bt"]=={"PRD":0} and dim["freq"]=={"M":0},"Eurostat not equivalent definition")
    codes=dim["nace_r2"];times=dim["time"]
    check(set(codes)==set(CODES.values()) and len(times)==141,"Comparator scope mismatch")
    vals=eu["value"]
    for (sector,period),dest in found.items():
        index=codes[sector]*141+times[period]
        other=vals[str(index)] if isinstance(vals,dict) else vals[index]
        check(other is not None and Decimal(str(other))==dest,f"Cross-source numerical deviation {sector}/{period}")
    check(len(found)==705,"No partial verified series accepted")
    result={"schema_version":"1.0.0","status":"preview_validated",
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "release_scope":"protected_vercel_preview_only","public_release_authorized":False,
        "comparator_dataset":"Eurostat sts_inpr_m","comparator_raw_sha256":digest,
        "comparator_updated_at":eu.get("updated"),"verification":"705_of_705_exact",
        "source_quality_caveat":"GENESIS FFCsv does not supply per-cell release/revision flags",
        "series":[]}
    for original,euro in CODES.items():
        pairs=sorted([(month,found[(euro,month)],lineage[(euro,month)]) for sec,month in found if sec==euro])
        check(len(pairs)==141 and pairs[0][0]=="2015-01" and pairs[-1][0]=="2026-09","Series calendar not complete")
        rawsha,acquisition,retrieved,table=pairs[0][2]
        check(all(x[2]==pairs[0][2] for x in pairs),"Mixed source acquisition within series")
        result["series"].append({
            "industry_code":original,"dataset_id":table,"source":"Destatis GENESIS",
            "source_url":"https://genesis.destatis.de/datenbank/online/table/"+table,
            "geo":"DE","frequency":"M","unit":"index","classification":"WZ2008",
            "adjustment":"original","base_year":2021,"retrieved_at":retrieved,
            "raw_sha256":rawsha,"acquisition_id":acquisition,
            "official_verification":True,"publication_approved":False,"preview_verified":True,
            "observations":[{"period":month,"value":float(value),
                "source_status_flags":["source_quality_field_not_provided"],
                "missing_reason":None} for month,value,info in pairs]})
    destination=Path("site/data/historical.json")
    destination.write_text(json.dumps(result,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    check(len(result["series"])==5,"Incomplete five-series preview")
    print(json.dumps({"preview_status":"verified_unpublished","records":705,
        "sectors":5,"comparator_sha256":digest,"destatis_raw_sha256":sorted(set(x[0] for x in lineage.values())),
        "public_release_authorized":False}))
if __name__=="__main__":
    try:main()
    except Exception as error:
        print("Protected preview build blocked: "+str(error),file=sys.stderr);sys.exit(2)
