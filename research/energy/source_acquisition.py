"""Credential-free official-data acquisition, for the FirmaBlick energy flagship.
Failures are explicitly recorded; no manufactured statistical observations.
"""
import urllib.request,urllib.parse,json,hashlib,datetime,time,pathlib,sys
O=pathlib.Path("artifacts/energy-research");O.mkdir(parents=True,exist_ok=True)
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"FirmaBlickResearch/0.1 (contact via firmablick.com)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as r:
        b=r.read(25_000_000)
    return json.loads(b),hashlib.sha256(b).hexdigest()
notes={"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"sources":{}}
base="https://www.smard.de/app/chart_data/4169/DE"
try:
    ind,digest=fetch(base+"/index_hour.json")
    stamps=ind["timestamps"]
    since=int(datetime.datetime(2025,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
    until=int(datetime.datetime(2026,11,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
    selected=[t for t in stamps if since-7*86400000<=t<until]
    rows=[]; errors=[]
    for n,t in enumerate(selected):
        u=f"{base}/4169_DE_hour_{t}.json"
        try:
            payload,sha=fetch(u)
            if not isinstance(payload.get("series"),list):raise ValueError("missing series")
            for pair in payload["series"]:
                if isinstance(pair,list) and len(pair)==2 and isinstance(pair[0],int) and since<=pair[0]<until:
                    rows.append([pair[0],pair[1]])
        except Exception as e:
            errors.append({"week_start_ms":t,"reason":str(e)[:140]})
        if n%12==0:print("SMARD batches",n+1,"/",len(selected),flush=True)
    seen={}
    for stamp,price in rows:
        if stamp in seen and seen[stamp]!=price:raise ValueError("Conflicting source prices")
        seen[stamp]=price
    rows=[[t,seen[t]] for t in sorted(seen)]
    payload={"scope":"SMARD 4169 DE day-ahead hourly 2025-01 to 2026-10; ISO UTC timestamps","series":rows,"errors":errors,"index_sha256":digest}
    (O/"smard_hourly_2025_2026.json").write_text(json.dumps(payload,separators=(",",":")))
    notes["sources"]["smard"]={"requested_windows":len(selected),"failed_windows":len(errors),"retrieved_points":len(rows),"first_timestamp":rows[0][0] if rows else None,"last_timestamp":rows[-1][0] if rows else None,"raw_index_sha256":digest,"error_samples":errors[:5],"status":"PARTIAL" if errors else "COMPLETE"}
except Exception as e:notes["sources"]["smard"]={"status":"FAILED","reason":str(e)[:300]}
params=[("geo","DE"),("geo","FR"),("geo","ES"),("nrg_cons","MWH2000-19999"),("siec","E7000"),("unit","KWH"),("currency","EUR"),("tax","X_VAT"),("sinceTimePeriod","2024-S1")]
url="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_205?"+urllib.parse.urlencode(params)
try:
    data,sha=fetch(url)
    (O/"eurostat_prices_raw.json").write_text(json.dumps(data,separators=(",",":")))
    notes["sources"]["eurostat"]={"status":"RETRIEVED","sha256":sha,"dimensions":data.get("id"),"sizes":data.get("size"),"updated":data.get("updated"),"units":"EUR/kWh excluding VAT and other recoverable taxes","band":"2,000–19,999 MWh/year","countries":["DE","FR","ES"]}
except Exception as e:notes["sources"]["eurostat"]={"status":"FAILED","reason":str(e)[:300]}
(O/"retrieval_manifest.json").write_text(json.dumps(notes,indent=2))
print(json.dumps(notes,indent=2),flush=True)
