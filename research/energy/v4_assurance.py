"""Issue #42: independently verify public source facts and deterministic calculations.
This script does not authorize the energy report to be published.
Run: python3 research/energy/v4_assurance.py
"""
from decimal import Decimal
from pathlib import Path
import json, math, sys, traceback
from verify_hourly import calculate
ROOT=Path(__file__).resolve().parent
EU=ROOT/"data/eurostat_nrg_pc_205_2026_s1_DE_FR_ES_raw.json"
CHECK={
"IC":{"DE":Decimal("205.8"),"FR":Decimal("156.7"),"ES":Decimal("133.6")},
"ID":{"DE":Decimal("174.2"),"FR":Decimal("123.9"),"ES":Decimal("117.7")},
"IE":{"DE":Decimal("146.4"),"FR":Decimal("97.9"),"ES":Decimal("104.8")},
"IF":{"DE":Decimal("137.9"),"FR":Decimal("79.4"),"ES":Decimal("91.7")},
"IG":{"DE":Decimal("126.7"),"FR":Decimal("72.2"),"ES":Decimal("77.7")}
}
BANDS={"IC":"MWH500-1999","ID":"MWH2000-19999","IE":"MWH20000-69999","IF":"MWH70000-149999","IG":"MWH_GE150000"}
def require(ok,msg):
 if not ok: raise AssertionError(msg)
def eurostat_index(obj,band,country):
 indices={id_:obj["dimension"][id_]["category"]["index"] for id_ in obj["id"]}
 categories={"freq":"S","siec":"E7000","nrg_cons":BANDS[band],"unit":"KWH","tax":"X_VAT","currency":"EUR","geo":country,"time":"2026-S1"}
 i=0
 for name,size in zip(obj["id"],obj["size"]): i=i*size+indices[name][categories[name]]
 return str(i)
def check_eurostat():
 d=json.loads(EU.read_text())
 require(d["source"]=="ESTAT" and d["updated"].startswith("2026-10-19"),"SOURCE_VINTAGE_NOT_PINNED")
 require(d["id"]==["freq","siec","nrg_cons","unit","tax","currency","geo","time"],"DIMENSION_SEQUENCE_CHANGED")
 require(d["dimension"]["tax"]["category"]["label"]["X_VAT"].lower().startswith("excluding vat and other recoverable"),"TAX_LEVEL_CHANGED")
 require(d["dimension"]["unit"]["category"]["label"]["KWH"]=="Kilowatt-hour","PRICE_UNIT_CHANGED")
 checked=0
 for band,countries in CHECK.items():
  for country,amount in countries.items():
   idx=eurostat_index(d,band,country)
   val=Decimal(str(d["value"][idx]))*1000
   require(val==amount,f"BAD_TARIFF_{band}_{country}_{val}")
   if country=="DE":require(d["status"].get(idx)=="p",f"GERMANY_PROVISIONAL_FLAG_MISSING_{band}")
   checked+=1
 require(checked==15,"REQUIRED_CELLS_MISSING")
 require(CHECK["IE"]["DE"]-CHECK["IE"]["FR"]==Decimal("48.5"),"IE_FR_DELTA")
 require(CHECK["IE"]["DE"]-CHECK["IE"]["ES"]==Decimal("41.6"),"IE_ES_DELTA")
 return checked
def bess_npv(gross=175000,opex=25000,discount=.08,degrade=.02,capex=850000,years=10):
 return -capex + sum((gross*(1-degrade)**(t-1)-opex)/(1+discount)**t for t in range(1,years+1))
def financial():
 expected={1:69938.05900403694,.8:-147599.95979147765,.7:-256368.96918923513}
 for factor,target in expected.items():
  actual=bess_npv(gross=175000*factor)
  require(abs(actual-target)<.01,f"BESS_NPV_MISMATCH_{factor}")
 require(sum([92,25,15,8,5])==145,"HYPOTHETICAL_TARIFF_STACK")
 require(40000*145==5800000,"TARIFF_COST_40GWH")
 require(40000*20==800000,"EBITDA_SENSITIVITY")
 require(20000*30-250000-150000-400000==-200000,"RELOCATION_ILLUSTRATION")
 return expected
def market():
 d=calculate()
 require(d["hourly_equivalents"]==8760 and d["raw_observation_count"]==15387,"PRICE_TIME_COVERAGE")
 require(abs(d["annual_mean_eur_mwh"]-89.32172)<.00001,"2025_MEAN_DIFFERENCE")
 require(d["derived_negative_hourly_mean_count"]==576,"RECONSTRUCTED_NEGATIVE_COUNT")
 require(d["published_negative_hour_count"]==573,"PUBLISHED_NEGATIVE_COUNT")
 require(d["negative_hour_method_discrepancy"]==3,"UNRESOLVED_COUNT_MISMATCH_UNDISCLOSED")
 require(d["publication_approved"] is False,"MARKET_PUBLICATION_GUARD")
 return d
def run():
 vals=check_eurostat(); financial(); prices=market()
 m=json.loads((ROOT/"v4_candidate_manifest.json").read_text())
 require(m["publication_approved"] is False and m["owner_approval_required"] is True,"REPORT_RELEASE_GUARD")
 require(m["status"]=="EDITORIAL_REVIEW_REQUIRED","REPORT_STATE")
 require(m["pages"]==20 and m["sample_pages"]==5,"REPORT_ASSET_PAGE_COUNTS")
 require(m["open_evidence_gaps"].get("negative_hour_count_573_vs_576")=="UNRESOLVED_EXPLICITLY_DISCLOSED","RECONCILIATION_MISREPRESENTED")
 require(m["open_evidence_gaps"].get("commercial_publication_rights")=="AWAITING_REVIEW","RIGHTS_GATE")
 return {"status":"NUMERICAL_CLAIMS_VERIFIED_REPORT_NOT_APPROVED","eurostat_exact_tariff_cells":vals,"real_2025_hourly_equivalents":prices["hourly_equivalents"],"published_negative_hours":573,"reconstructed_negative_hourly_means":576,"model_base_npv_eur":round(bess_npv(),2),"report_status":m["status"]}
if __name__=="__main__":
 try:print(json.dumps(run(),indent=2))
 except Exception as e:
  traceback.print_exc(); print("V4_ASSURANCE_FAILED: "+repr(e),file=sys.stderr);sys.exit(2)
