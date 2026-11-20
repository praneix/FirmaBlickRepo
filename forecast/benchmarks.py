"""Predeclared, vintage-aware German manufacturing forecasting benchmark harness.

Reference implementation only. Historical data cannot be scored as a real-time
backtest without time-stamped point-in-time source availability. Standard library.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import statistics
from typing import Mapping

PROTOCOL_VERSION="firmablick-forecast-evaluation-v1.0.0"
METHODS=("last_value","seasonal_naive","drift")
HORIZONS=(1,3,6,12)
MIN_TRAIN_MONTHS=60
SEASON=12
FINAL_HOLDOUT_MONTHS=24
MIN_EVAL_ORIGINS=12
MASE_EPSILON=1e-12


class ForecastError(ValueError):
    pass


@dataclass(frozen=True)
class Observation:
    month: str
    value: float | None
    available_at: str
    source_vintage: str
    def __post_init__(self):
        if not isinstance(self.month,str) or len(self.month)!=7 or self.month[4]!="-":
            raise ForecastError("Observation month must use YYYY-MM.")
        month_number=self.month[5:]
        if not(self.month[:4].isdigit() and month_number.isdigit() and 1<=int(month_number)<=12):
            raise ForecastError("Invalid monthly source period.")
        if self.value is not None and (isinstance(self.value,bool) or
                                      not isinstance(self.value,(int,float)) or
                                      not math.isfinite(self.value) or self.value<0):
            raise ForecastError("Volume index must be nonnegative finite or missing.")
        _timestamp(self.available_at)
        if not isinstance(self.source_vintage,str) or not self.source_vintage:
            raise ForecastError("Source vintage identifier required.")


def _timestamp(s:str)->datetime:
    if not isinstance(s,str) or not s.endswith("Z"):
        raise ForecastError("Source availability must be explicit UTC.")
    try:
        dt=datetime.fromisoformat(s.replace("Z","+00:00"))
        if dt.utcoffset().total_seconds()!=0:
            raise ValueError("Non UTC")
        return dt
    except (ValueError,AttributeError) as exc:
        raise ForecastError("Invalid source availability timestamp.") from exc


def _month_number(s:str)->int:
    return int(s[:4])*12 + int(s[5:])-1


def _month_string(n:int)->str:
    return f"{n//12:04d}-{n%12+1:02d}"


def _fingerprint(rows):
    canonical=[{"month":x.month,"value":x.value,"available_at":x.available_at,
                "source_vintage":x.source_vintage} for x in rows]
    return hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _validate_history(history:list[Observation]):
    if not isinstance(history,list) or not history:
        raise ForecastError("History must be nonempty.")
    if any(not isinstance(x,Observation) for x in history):
        raise ForecastError("History requires timestamped Observation records.")
    ordered=sorted(history,key=lambda x:(_month_number(x.month),_timestamp(x.available_at),x.source_vintage))
    identities=[(o.month,o.available_at,o.source_vintage) for o in ordered]
    if len(set(identities))!=len(identities):
        raise ForecastError("Duplicated source observation identity.")
    return ordered


def as_of(history:list[Observation], origin_time:str):
    """Only values released by this instant, latest available revision per month."""
    cutoff=_timestamp(origin_time)
    available={}
    for row in _validate_history(history):
        stamp=_timestamp(row.available_at)
        if stamp<=cutoff:
            previous=available.get(row.month)
            if previous is None or stamp>_timestamp(previous.available_at):
                available[row.month]=row
            elif stamp==_timestamp(previous.available_at) and row.source_vintage!=previous.source_vintage:
                raise ForecastError("Ambiguous simultaneous source vintages.")
    return available


def _training(history,origin_month,origin_at):
    observations=as_of(history,origin_at)
    limit=_month_number(origin_month)
    selected={month:row for month,row in observations.items() if _month_number(month)<=limit}
    if not selected: raise ForecastError("No genuinely available training observations.")
    months=sorted(selected,key=_month_number)
    if _month_number(months[-1])!=limit:
        raise ForecastError("Origin month's official observation was not available at forecast time.")
    first=_month_number(months[0])
    if len(months)<MIN_TRAIN_MONTHS or _month_number(months[-1])-first+1!=len(months):
        raise ForecastError("Missing training months or insufficient sixty-month history.")
    if any(row.value is None for row in selected.values()):
        raise ForecastError("Training data contains unreconciled missing observations.")
    return [selected[_month_string(n)].value for n in range(first,limit+1)], {
        "first_month":months[0],"last_month":months[-1],
        "latest_source_vintage":selected[months[-1]].source_vintage,
        "max_information_time":max(x.available_at for x in selected.values())
    }


def predict(method:str,values:list[float],horizon:int):
    if method not in METHODS: raise ForecastError("Unknown benchmark.")
    if not isinstance(horizon,int) or horizon<1 or horizon>12:
        raise ForecastError("Unsupported forecast horizon.")
    if len(values)<MIN_TRAIN_MONTHS or any(v is None or not math.isfinite(v) for v in values):
        raise ForecastError("Insufficient complete training sequence.")
    if method=="last_value": return float(values[-1])
    if method=="seasonal_naive": return float(values[-SEASON+((horizon-1)%SEASON)])
    drift=(values[-1]-values[0])/(len(values)-1)
    return float(values[-1]+horizon*drift)


def _scale(train:list[float]):
    diffs=[abs(train[i]-train[i-SEASON]) for i in range(SEASON,len(train))]
    if not diffs:return None
    denom=statistics.mean(diffs)
    return denom if denom>MASE_EPSILON else None


def _smape(a:float,f:float):
    denom=abs(a)+abs(f)
    return None if denom<=MASE_EPSILON else 200*abs(a-f)/denom


def _metrics(records):
    if not records:return {"n":0,"mae":None,"bias":None,"mase":None,"smape":None,
                           "interval_coverage":None,"interval_count":0,"mean_interval_width":None}
    errors=[r["forecast"]-r["actual"] for r in records]
    smapes=[r["smape"] for r in records if r["smape"] is not None]
    mase=[r["mase"] for r in records if r["mase"] is not None]
    intervals=[r for r in records if r["lower"] is not None and r["upper"] is not None]
    return {
      "n":len(records),"mae":statistics.mean(abs(e) for e in errors),
      "bias":statistics.mean(errors),
      "mase":statistics.mean(mase) if mase else None,
      "smape":statistics.mean(smapes) if smapes else None,
      "interval_coverage":statistics.mean(r["lower"]<=r["actual"]<=r["upper"] for r in intervals) if intervals else None,
      "interval_count":len(intervals),
      "mean_interval_width":statistics.mean(r["upper"]-r["lower"] for r in intervals) if intervals else None
    }


def _origin_dates(origins):
    if not isinstance(origins,list) or not origins:raise ForecastError("Rolling origin schedule required.")
    last=-1
    for o in origins:
        if not isinstance(o,dict) or set(o)!={"month","available_at"}:
            raise ForecastError("Origin must specify exact month and decision-time UTC.")
        n=_month_number(o["month"])
        _timestamp(o["available_at"])
        if n<=last:raise ForecastError("Origins must be unique and chronological.")
        last=n
    return origins


def run_backtest(history:list[Observation],origins:list[dict],truth_cutoff:str,
                 *, intervals:Mapping[str,Mapping[int,float]]|None=None,
                 allow_diagnostic=True, final_holdout_start:str|None=None):
    """Rolling expanding-window multi-horizon scores.

    Results here are diagnostic until independently certified archival evidence
    validates that source vintages reflect *actual* point-in-time releases.
    An origin's training data is strictly as-of its decision time. Target truth
    is the latest observation available by truth_cutoff, with that evaluation
    cutoff explicitly reported. Intervals must be PRECALIBRATED externally;
    no in-sample/future residuals are used to invent coverage.
    """
    _timestamp(truth_cutoff)
    history=_validate_history(history)
    origins=_origin_dates(origins)
    if len(origins)<MIN_EVAL_ORIGINS and not allow_diagnostic:
        raise ForecastError("Too few eligible origins for formal evaluation.")
    truth=as_of(history,truth_cutoff)
    if final_holdout_start is not None:
        if not isinstance(final_holdout_start,str) or len(final_holdout_start)!=7:
            raise ForecastError("Final holdout start must use YYYY-MM.")
        _month_number(final_holdout_start)
    elif not allow_diagnostic:
        raise ForecastError("Frozen holdout boundary required for formal evaluation.")
    output=[]
    excluded=[]
    for origin in origins:
        origin_month=origin["month"]
        available_at=origin["available_at"]
        if _timestamp(available_at)>_timestamp(truth_cutoff):
            raise ForecastError("Origin cannot fall after truth evaluation cutoff.")
        try:
            training,proof=_training(history,origin_month,available_at)
        except ForecastError as exc:
            excluded.append({"origin":origin_month,"reason":str(exc)})
            continue
        scale=_scale(training)
        for horizon in HORIZONS:
            target=_month_string(_month_number(origin_month)+horizon)
            if final_holdout_start is not None and target>=final_holdout_start:
                excluded.append({"origin":origin_month,"horizon":horizon,
                                 "target":target,"reason":"Locked final 24-month holdout."})
                continue
            candidate=truth.get(target)
            if candidate is None or candidate.value is None:
                excluded.append({"origin":origin_month,"horizon":horizon,
                                 "target":target,"reason":"Target truth unavailable by evaluation cutoff."})
                continue
            for method in METHODS:
                forecast=predict(method,training,horizon)
                bound=(intervals or {}).get(method,{}).get(horizon)
                if bound is not None and (not isinstance(bound,(float,int)) or
                                          not math.isfinite(bound) or bound<0):
                    raise ForecastError("Interval halfwidth must be finite and nonnegative.")
                lower=max(0.0,forecast-bound) if bound is not None else None
                upper=forecast+bound if bound is not None else None
                output.append({
                  "origin":origin_month,"origin_at":available_at,"target":target,
                  "horizon":horizon,"method":method,"forecast":forecast,
                  "actual":candidate.value,"target_vintage":candidate.source_vintage,
                  "information_latest_vintage":proof["latest_source_vintage"],
                  "information_max_available_at":proof["max_information_time"],
                  "training_count":len(training),"seasonal_scale":scale,
                  "mase":abs(forecast-candidate.value)/scale if scale is not None else None,
                  "smape":_smape(candidate.value,forecast),
                  "lower":lower,"upper":upper
                })
    metrics={}
    for method in METHODS:
        subset=[r for r in output if r["method"]==method]
        metrics[method]={
          str(h):_metrics([r for r in subset if r["horizon"]==h]) for h in HORIZONS
        }
    return {
      "protocol_version":PROTOCOL_VERSION,
      "assessment":"synthetic_or_unverified_diagnostic" if allow_diagnostic else "vintage_replay_unverified_source",
      "real_time_claim_permitted":False,
      "official_source_certified":False,
      "final_holdout_start":final_holdout_start,
      "history_sha256":_fingerprint(history),"truth_cutoff":truth_cutoff,
      "origins_requested":len(origins),"origins_eligible":len({r["origin"] for r in output}),
      "metrics":metrics,"predictions":output,"excluded":excluded,
      "publication_approved":False,
      "interval_policy":"precalibrated_nonnegative_halfwidth_only; none means coverage unavailable"
    }


def release_decision(backtest:dict,*,final_holdout_unlocked=False,model_metrics=None):
    """Frozen predeclared gate for *future* models; no model is proposed in #13."""
    if backtest.get("assessment")!="vintage_aware_evaluation" or backtest.get("official_source_certified") is not True:
        return {"approved":False,"reason":"Certified point-in-time official-source evidence is required."}
    if not final_holdout_unlocked:
        return {"approved":False,"reason":"Final 24-month holdout must remain locked until candidate freeze."}
    if model_metrics is None:
        return {"approved":False,"reason":"Issue #13 benchmarks only; no candidate model submitted."}
    if backtest.get("origins_eligible",0)<24:
        return {"approved":False,"reason":"At least 24 eligible rolling origins required."}
    for horizon in HORIZONS:
        baseline=backtest["metrics"]["seasonal_naive"][str(horizon)]
        candidate=model_metrics.get(str(horizon),{})
        if baseline["n"]<12 or candidate.get("n",0)<12:
            return {"approved":False,"reason":f"Horizon {horizon} has fewer than 12 comparable forecasts."}
        if baseline["mae"] is None or not isinstance(candidate.get("mae"),(int,float)):
            return {"approved":False,"reason":f"Horizon {horizon} missing MAE."}
        if candidate["mae"]>0.95*baseline["mae"]:
            return {"approved":False,"reason":f"Horizon {horizon} fails predeclared 5% MAE improvement."}
        if candidate.get("coverage_n",0)<20 or not (0.80<=candidate.get("coverage",float("nan"))<=0.98):
            return {"approved":False,"reason":f"Horizon {horizon} interval coverage outside gate."}
    return {"approved":True,"reason":"Numerical gate passed; still requires official-data provenance and model governance signoff."}
