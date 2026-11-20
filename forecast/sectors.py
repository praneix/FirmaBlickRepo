"""Issue #16: independently gated WZ2008 sector forecast evaluations.

Diagnostic engineering implementation. Never confers model release authority.
Each C28/C29/C24/C20 has independent input, source identity, score and status.
The public website remains historical-only until a distinct authorization path
and validated official vintages exist for that precise sector.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import math
import statistics
from typing import Mapping

from forecast.benchmarks import (
    Observation, ForecastError, HORIZONS, METHODS, MIN_TRAIN_MONTHS,
    _month_number, _month_string, _origin_dates, _timestamp, _training,
    _validate_history, as_of, predict, _metrics, _scale, _smape,
)
from forecast.flagship import point_forecast, calibrate_intervals, MODEL_VERSION

SECTOR_ORDER=("28","29","24","20")
SECTOR_NAMES={
    "28":"Machinery and equipment",
    "29":"Motor vehicles and parts",
    "24":"Basic metals",
    "20":"Chemicals and chemical products",
}
SECTOR_MODEL_VERSIONS={code:"1.0.0-"+code for code in SECTOR_ORDER}
SECTOR_MODELS={code:"fb-sector-"+code+"-seasonal-damped-trend" for code in SECTOR_ORDER}
SOURCE_DATASET="42153-0002"
MIN_ORIGINS=24
HOLDOUT_MONTHS=24
REGIME_THRESHOLD=0.20
MIN_TRAIN_CALIBRATION=80


def _status(code,reason,*,source=None,diagnostic=None,shocks=None):
    return {
        "industry_code":code,"industry_name":SECTOR_NAMES[code],
        "model_id":SECTOR_MODELS[code],"model_version":SECTOR_MODEL_VERSIONS[code],
        "status":"historical_only","release_recommendation":"historical_only",
        "release_approved":False,"publication_approved":False,
        "reason":reason,"source":source,"diagnostic":diagnostic,"structural_breaks":shocks,
        "forecast_months":[],"public_forecast_available":False,
    }


def _source_context(code,source):
    if not isinstance(source,dict):
        raise ForecastError("Source identity and lineage required for each sector.")
    required={
        "dataset_id","industry_code","geo","frequency","unit","base_year",
        "adjustment","classification_revision","raw_sha256","acquisition_id",
        "official_source_certified",
    }
    if not required.issubset(source):
        raise ForecastError("Source metadata incomplete; sector remains historical-only.")
    if (source["dataset_id"]!=SOURCE_DATASET or source["industry_code"]!=code or
        source["geo"]!="DE" or source["frequency"]!="M" or source["unit"]!="index" or
        source["classification_revision"]!="WZ2008" or
        source["adjustment"] not in ("original","calendar_adjusted","seasonally_adjusted",
                                     "seasonal_calendar_adjusted") or
        type(source["base_year"]) is not int or not 1990<=source["base_year"]<=2100 or
        not isinstance(source["raw_sha256"],str) or len(source["raw_sha256"])!=64 or
        any(ch not in "0123456789abcdef" for ch in source["raw_sha256"]) or
        not isinstance(source["acquisition_id"],str) or not source["acquisition_id"] or
        source["official_source_certified"] is not False):
        raise ForecastError("Source mismatch or unsupported official-certification claim.")
    return {k:source[k] for k in sorted(required)}


def _shock_diagnostics(training):
    """Transparent descriptive break alert; NOT an automatic causal assertion."""
    if len(training)<MIN_TRAIN_MONTHS:
        return {"status":"insufficient_history","events":[],"threshold":REGIME_THRESHOLD}
    events=[]
    for i in range(12,len(training)):
        prior=training[i-12]
        delta=None if prior==0 else (training[i]-prior)/prior
        if delta is not None and abs(delta)>REGIME_THRESHOLD:
            events.append({"relative_month_index":i,
                           "year_over_year_change":round(delta,8),
                           "flag":"large_yoy_change_not_attributed"})
    return {"status":"descriptive_unvalidated","threshold":REGIME_THRESHOLD,
            "events":events,"has_shock_flags":bool(events),
            "note":"A 20% year-on-year change flags a candidate break; its cause is unknown."}


def _fingerprint(code,source,observations,origin_time,origin_month):
    known=as_of(observations,origin_time)
    available=[
        {"month":key,"value":item.value,"available_at":item.available_at,
         "source_vintage":item.source_vintage}
        for key,item in sorted(known.items()) if _month_number(key)<=_month_number(origin_month)
    ]
    payload={"sector":code,"source":source,"observations":available,
             "model_version":SECTOR_MODEL_VERSIONS[code],"origin_time":origin_time}
    return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def _evaluate_one(history,origins,truth_cutoff,holdout_start):
    """Matched sector-specific comparisons on exactly same eligible cells."""
    _timestamp(truth_cutoff)
    if not isinstance(holdout_start,str) or len(holdout_start)!=7:
        raise ForecastError("Locked final holdout boundary required.")
    _month_number(holdout_start)
    rows=_validate_history(history)
    schedule=_origin_dates(origins)
    truth=as_of(rows,truth_cutoff)
    metrics_records=[]
    excluded=[]
    training_shocks=[]
    for origin in schedule:
        if _timestamp(origin["available_at"])>_timestamp(truth_cutoff):
            raise ForecastError("Forecast origin is after truth cutoff.")
        try:
            training,proof=_training(rows,origin["month"],origin["available_at"])
            shock=_shock_diagnostics(training)
            if shock["has_shock_flags"]:
                training_shocks.append({"origin":origin["month"],
                                        "events_count":len(shock["events"])})
        except ForecastError as exc:
            excluded.append({"origin":origin["month"],"reason":str(exc)})
            continue
        scale=_scale(training)
        intervals=calibrate_intervals(training)
        for horizon in HORIZONS:
            target=_month_string(_month_number(origin["month"])+horizon)
            if target>=holdout_start:
                excluded.append({"origin":origin["month"],"horizon":horizon,
                                 "reason":"Final 24-month holdout remains locked."})
                continue
            actual=truth.get(target)
            if actual is None or actual.value is None:
                excluded.append({"origin":origin["month"],"horizon":horizon,
                                 "reason":"Target observation not available."})
                continue
            for method in ("candidate",)+METHODS:
                p=point_forecast(training,horizon) if method=="candidate" else predict(method,training,horizon)
                radius=intervals[str(horizon)]["half_width"] if method=="candidate" else None
                metrics_records.append({
                    "origin":origin["month"],"target":target,"horizon":horizon,
                    "method":method,"forecast":p,"actual":actual.value,
                    "origin_at":origin["available_at"],
                    "information_max_available_at":proof["max_information_time"],
                    "information_latest_vintage":proof["latest_source_vintage"],
                    "target_vintage":actual.source_vintage,
                    "lower":max(0.0,p-radius) if radius is not None else None,
                    "upper":p+radius if radius is not None else None,
                    "mase":abs(p-actual.value)/scale if scale is not None else None,
                    "smape":_smape(actual.value,p),
                })
    metrics={
        method:{str(h):_metrics([row for row in metrics_records if row["method"]==method
                                 and row["horizon"]==h]) for h in HORIZONS}
        for method in ("candidate",)+METHODS
    }
    return {
        "metrics":metrics,"predictions":metrics_records,"excluded":excluded,
        "eligible_origins":len({r["origin"] for r in metrics_records}),
        "shock_history":training_shocks,
        "holdout_start":holdout_start,"truth_cutoff":truth_cutoff,
        "training_mode":"source_vintage_as_of_per_origin",
        "publication_approved":False,
    }


def _release_reason(report,training_shocks):
    """Never promote on fixture evidence; describe each independent gate."""
    if report["eligible_origins"]<MIN_ORIGINS:
        return "Insufficient eligible sector-specific rolling origins (minimum 24)."
    for horizon in HORIZONS:
        candidate=report["metrics"]["candidate"][str(horizon)]
        reference=report["metrics"]["seasonal_naive"][str(horizon)]
        if candidate["n"]<12 or candidate["n"]!=reference["n"]:
            return f"Horizon {horizon}: insufficient paired observations."
        if reference["mae"] is None or reference["mae"]<=0 or (
            candidate["mae"] is None or candidate["mae"]>0.95*reference["mae"]):
            return f"Horizon {horizon}: 5% seasonal-naive MAE improvement not established."
        if candidate["interval_count"]<20 or candidate["interval_coverage"] is None or not (
            0.8<=candidate["interval_coverage"]<=0.98):
            return f"Horizon {horizon}: independent interval coverage acceptance not established."
    if training_shocks:
        return "Potential structural breaks require independent evaluation and review."
    return "Diagnostic benchmark passed numeric checks; independent official-vintage, holdout and release approval remain outstanding."


def evaluate_sector(code,history,source,origins,truth_cutoff,*,holdout_start,
                    aggregate_approved=False,orders_indicator=None):
    if code not in SECTOR_ORDER:
        raise ForecastError("Unapproved industry code for sector forecasting.")
    # Explicit ban on exporting aggregate approval; unrelated input is ignored.
    _=aggregate_approved
    if orders_indicator is not None:
        # Adding exogenous regressors without out-of-sample incremental value
        # requires a future separately versioned candidate, never in v1.
        return _status(code,"Orders indicator unvalidated; exogenous model is disabled.")
    try:
        pinned=_source_context(code,source)
        observations=_validate_history(history)
        schedule=_origin_dates(origins)
        report=_evaluate_one(observations,schedule,truth_cutoff,holdout_start)
        last=schedule[-1]
        train,proof=_training(observations,last["month"],last["available_at"])
        shock=_shock_diagnostics(train)
        reason=_release_reason(report,report["shock_history"])
        result=_status(code,reason,source=pinned,diagnostic=report,shocks=shock)
        result["forecast_input_sha256"]=_fingerprint(code,pinned,observations,last["available_at"],last["month"])
        result["observed_end_month"]=proof["last_month"]
        result["origin_at"]=last["available_at"]
        result["source_vintage"]=proof["latest_source_vintage"]
        result["candidate_horizons"]=list(range(1,13))
        result["candidate_diagnostic_not_released"]={
            "model_id":SECTOR_MODELS[code],"model_version":SECTOR_MODEL_VERSIONS[code],
            "training_months":len(train),
            "index_projections":[point_forecast(train,h) for h in range(1,13)],
            "uncertainty":"Unverified training-only residual bounds; no public intervals.",
            "publication_approved":False,
        }
        return result
    except (ForecastError,ValueError,TypeError,KeyError,ZeroDivisionError) as exc:
        return _status(code,"Validation rejected sector candidate: "+str(exc)[:240])


def evaluate_portfolio(sector_inputs:Mapping[str,dict],*,aggregate_approved=False):
    """Always reports all four codes; no cross-sector pooling or promotion."""
    if not isinstance(sector_inputs,Mapping):
        raise ForecastError("Independent sector inputs must be a dictionary.")
    if set(sector_inputs)-set(SECTOR_ORDER):
        raise ForecastError("Portfolio contains an unapproved sector code.")
    outcome=[]
    for code in SECTOR_ORDER:
        payload=sector_inputs.get(code)
        if payload is None:
            outcome.append(_status(code,"Sector inputs unavailable; historical-only."))
            continue
        try:
            outcome.append(evaluate_sector(
                code,payload["history"],payload["source"],payload["origins"],
                payload["truth_cutoff"],holdout_start=payload["holdout_start"],
                aggregate_approved=aggregate_approved,
                orders_indicator=payload.get("orders_indicator")))
        except (KeyError,TypeError) as exc:
            outcome.append(_status(code,"Missing independent source, origin or holdout inputs."))
    return {
        "schema_version":"1.0.0",
        "source":"Destatis GENESIS 42153-0002",
        "evaluation_order":list(SECTOR_ORDER),
        "sectors":outcome,"publication_approved":False,
        "forecast_release_flags":{code:False for code in SECTOR_ORDER},
        "aggregate_release_transfer_permitted":False,
        "official_source_certified":False,
        "external_acceptance_pending":True,
        "user_visible_mode":"historical_only",
    }
