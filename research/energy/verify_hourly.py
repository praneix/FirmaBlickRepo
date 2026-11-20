"""Reproduce all 2025 energy market charts from original archived source bytes.

No AI calculations. Source: Fraunhofer Energy-Charts, original BNetzA SMARD,
CC BY 4.0. Run: python3 research/energy/verify_hourly.py
"""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import math

ROOT = Path(__file__).resolve().parent / "data"
RAW = ROOT / "energy_charts_smard_de_lu_2025_raw.json"
REPORTED = ROOT / "smard_2025_verified_hourly_summary.json"

def calculate():
    original=json.loads(RAW.read_bytes())
    stamps=original["unix_seconds"]
    prices=original["price"]
    assert len(stamps)==len(prices)==15387
    start=stamps[0]
    end=start+365*24*3600
    assert datetime.fromtimestamp(start,timezone.utc).isoformat()=="2024-12-31T23:00:00+00:00"
    assert original["unit"]=="EUR/MWh"
    sums=[0.0]*8760; seconds=[0]*8760
    for i,(stamp,value) in enumerate(zip(stamps,prices)):
        nxt=stamps[i+1] if i+1<len(stamps) else end
        assert nxt-stamp in (900,3600), "Unknown interval resolution or gap"
        assert isinstance(value,(int,float)) and math.isfinite(value)
        a=stamp
        while a<nxt:
            hour=(a-start)//3600
            delta=min(nxt,start+(hour+1)*3600)-a
            assert 0<=hour<8760
            sums[hour]+=value*delta
            seconds[hour]+=delta
            a+=delta
    assert all(n==3600 for n in seconds), "Incomplete hourly equivalent"
    hourly=[s/n for s,n in zip(sums,seconds)]
    avg=sum(hourly)/len(hourly)
    assert abs(avg-89.32)<0.01, "Failed published BNetzA annual mean parity"
    neg=sum(x<0 for x in hourly)
    # Not an error: the published 573 negative hours uses a different convention
    # for the native 15-minute market from Oct 2025. Preserve both numbers.
    assert neg==576
    ordered=sorted(hourly)
    dtz=ZoneInfo("Europe/Berlin")
    months={}
    for hour,x in enumerate(hourly):
        clock=datetime.fromtimestamp(start+3600*hour,timezone.utc).astimezone(dtz)
        key=f"{clock.year:04d}-{clock.month:02d}"
        months.setdefault(key,[]).append(x)
    assert len(months)==12 and all(x.startswith("2025-") for x in months)
    report={
        "raw_observation_count":len(prices),
        "hourly_equivalents":len(hourly),
        "annual_mean_eur_mwh":round(avg,5),
        "published_annual_mean_eur_mwh":89.32,
        "derived_negative_hourly_mean_count":neg,
        "published_negative_hour_count":573,
        "negative_hour_method_discrepancy":3,
        "quantile_5_eur_mwh":ordered[int((8760-1)*.05)],
        "quantile_50_eur_mwh":ordered[int((8760-1)*.50)],
        "quantile_95_eur_mwh":ordered[int((8760-1)*.95)],
        "monthly":{k:{"hours":len(v),"mean":round(sum(v)/len(v),2)} for k,v in sorted(months.items())},
        "publication_approved":False,
    }
    return report

if __name__=="__main__":
    stats=calculate()
    check=json.loads(REPORTED.read_text())
    assert abs(stats["annual_mean_eur_mwh"]-check["time_weighted_average_eur_mwh"])<0.00001
    assert stats["derived_negative_hourly_mean_count"]==check["negative_hourly_equivalent_count"]
    print(json.dumps(stats,indent=2))
