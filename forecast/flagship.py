"""Deterministic, unpublished candidate for German manufacturing index forecasting.

Issue #14: seasonal 12-month reference with damped local annual trend.
All intervals are estimated with TRAINING-ONLY rolling origin residuals.
No official forecast is issued unless a separate authenticated data validation
and independent model review explicitly authorize publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import statistics

from forecast.benchmarks import (
    ForecastError, Observation, HORIZONS, METHODS, MIN_TRAIN_MONTHS,
    _month_number, _month_string, _training, _validate_history, _origin_dates,
    _timestamp, as_of, predict, _metrics, _scale, _smape,
)

MODEL_ID = "fb-manufacturing-seasonal-damped-trend"
MODEL_VERSION = "1.0.0"
DEFAULT_DAMPING = 0.85
MIN_CALIBRATION_ERRORS = 20
INTERVAL_TARGET = 0.90
FORECAST_HORIZONS = tuple(range(1,13))
SOURCE_DATASET = "42153-0001"


def _numbers(values):
    if not isinstance(values,list) or len(values)<MIN_TRAIN_MONTHS:
        raise ForecastError("Candidate needs at least 60 contiguous training months.")
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or
           not math.isfinite(x) or x<0 for x in values):
        raise ForecastError("Candidate training values must be complete finite nonnegative indices.")


def point_forecast(values:list[float], horizon:int, *, damping:float=DEFAULT_DAMPING)->float:
    """Fixed-parameter model, with no tuning or future-dependent scaling.

    Seasonal base: value in same month of the most recent twelve-month window.
    Trend: difference of means of the last two full years, carried forward with
    geometric damping. Explicitly clamp predictions at zero.
    """
    _numbers(values)
    if not isinstance(horizon,int) or isinstance(horizon,bool) or not 1<=horizon<=12:
        raise ForecastError("Candidate supports horizons 1..12 only.")
    if not isinstance(damping,(int,float)) or isinstance(damping,bool) or not 0<damping<1:
        raise ForecastError("Damping must be a fixed number strictly between 0 and 1.")
    annual_change=statistics.mean(values[-12:])-statistics.mean(values[-24:-12])
    previous_year=values[-12+(horizon-1)]
    trend=annual_change*(damping*(1-damping**horizon)/(1-damping))
    return max(0.0,float(previous_year+trend))


def calibrate_intervals(train:list[float], *, alpha:float=1-INTERVAL_TARGET,
                        min_errors:int=MIN_CALIBRATION_ERRORS):
    """Symmetric absolute-error intervals, calibrated only on within-train origins.

    Each historical origin with >=60 months and observed target inside the
    available training prefix contributes one out-of-sample absolute error.
    Uses split-conformal rank ceil((n+1)*(1-alpha)); unavailable if rank>n.
    Overlapping origins are dependent; empirical coverage remains unverified.
    """
    _numbers(train)
    if not isinstance(alpha,(int,float)) or not 0<alpha<1:
        raise ForecastError("Interval alpha must lie strictly between 0 and 1.")
    if not isinstance(min_errors,int) or min_errors<20:
        raise ForecastError("At least twenty calibration errors required.")
    output={}
    n=len(train)
    for horizon in FORECAST_HORIZONS:
        residuals=[]
        for end in range(MIN_TRAIN_MONTHS,n-horizon+1):
            forecast=point_forecast(train[:end],horizon)
            residuals.append(abs(forecast-train[end+horizon-1]))
        count=len(residuals)
        rank=math.ceil((count+1)*(1-alpha))
        half_width=sorted(residuals)[rank-1] if count>=min_errors and rank<=count else None
        output[str(horizon)]={"half_width":half_width,
                              "calibration_n":count,
                              "nominal_coverage":1-alpha,
                              "method":"training_only_rolling_absolute_residual_quantile",
                              "diagnostic_only":True}
    return output


def _series_context(history, origin_at:str, origin_month:str, source:dict):
    if not isinstance(source,dict):
        raise ForecastError("Explicit source context required.")
    required={"dataset_id","industry_code","geo","frequency","unit",
              "base_year","adjustment","classification_revision",
              "raw_sha256","acquisition_id","official_source_certified"}
    if not required.issubset(source):
        raise ForecastError("Missing source lineage or manufacturing identity.")
    if (source["dataset_id"]!=SOURCE_DATASET or source["industry_code"]!="C"
        or source["geo"]!="DE" or source["frequency"]!="M" or source["unit"]!="index"
        or source["classification_revision"]!="WZ2008"
        or source["adjustment"] not in ("original","calendar_adjusted",
                                      "seasonally_adjusted","seasonal_calendar_adjusted")
        or not isinstance(source["base_year"],int) or isinstance(source["base_year"],bool)
        or not 1990<=source["base_year"]<=2100
        or not isinstance(source["raw_sha256"],str)
        or len(source["raw_sha256"])!=64
        or any(c not in "0123456789abcdef" for c in source["raw_sha256"])
        or not isinstance(source["acquisition_id"],str)
        or not source["acquisition_id"]):
        raise ForecastError("Source context does not match German manufacturing index.")
    if source["official_source_certified"] is not False:
        raise ForecastError("Issue 14 diagnostic engine never accepts official certification.")
    values,proof=_training(history,origin_month,origin_at)
    return values,proof


def forecast_package(history:list[Observation], *, origin_month:str,
                     origin_at:str, source:dict, damping:float=DEFAULT_DAMPING):
    """Generate exactly twelve diagnostic months with full lineage, never published."""
    history=_validate_history(history)
    _timestamp(origin_at)
    values,proof=_series_context(history,origin_at,origin_month,source)
    calibrated=calibrate_intervals(values)
    forecasts=[]
    for h in FORECAST_HORIZONS:
        estimate=point_forecast(values,h,damping=damping)
        info=calibrated[str(h)]
        radius=info["half_width"]
        forecasts.append({
          "target_month":_month_string(_month_number(origin_month)+h),
          "horizon_months":h,"index_projection":estimate,
          "lower":max(0.0,estimate-radius) if radius is not None else None,
          "upper":estimate+radius if radius is not None else None,
          "nominal_interval_coverage":INTERVAL_TARGET if radius is not None else None,
          "interval_calibration_n":info["calibration_n"],
          "interval_status":"diagnostic_uncalibrated" if radius is None else "training_only_empirically_calibrated_not_independently_validated"
        })
    seed_context={
       "model_id":MODEL_ID,"version":MODEL_VERSION,
       "origin_month":origin_month,"origin_at":origin_at,
       "source_sha256":source["raw_sha256"],
       "source_acquisition":source["acquisition_id"],
       "vintages":[{"month":v.month,"value":v.value,
                    "available_at":v.available_at,"source_vintage":v.source_vintage}
                   for v in history],
       "damping":damping}
    fingerprint=hashlib.sha256(json.dumps(seed_context,sort_keys=True,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return {
       "schema_version":"1.0.0","type":"forecast_diagnostic_not_official_observation",
       "model_id":MODEL_ID,"model_version":MODEL_VERSION,
       "model_parameters":{"seasonal_period":12,"annual_trend_window_months":24,
                           "damping":damping,"algorithm":"seasonal_last_year_plus_damped_mean_annual_change"},
       "scenario_id":"baseline_unadjusted", "origin_month":origin_month,
       "origin_at":origin_at,"observed_end_month":proof["last_month"],
       "training_months":len(values),"source":{"dataset_id":source["dataset_id"],
            "industry_code":"C","geo":"DE","unit":"index","base_year":source["base_year"],
            "adjustment":source["adjustment"],"classification_revision":"WZ2008",
            "raw_sha256":source["raw_sha256"],"acquisition_id":source["acquisition_id"],
            "latest_training_vintage":proof["latest_source_vintage"],
            "latest_training_available_at":proof["max_information_time"]},
       "forecast_months":forecasts,"max_horizon_months":12,
       "calibration_method":"train_only_rolling_origin_abs_error_90pct_quantile",
       "uncertainty_note":"Training-only, overlapping-origin residual coverage is not an independently validated 90% interval.",
       "evaluation_status":"synthetic_or_unverified_diagnostic",
       "official_source_certified":False,"publication_approved":False,
       "forecast_input_sha256":fingerprint,
       "model_release_gate":{"approved":False,
           "reason":"Authenticated point-in-time Destatis source and independent holdout validation unavailable."},
       "long_horizon_2030":{"status":"withheld","reason":"No empirically validated longer-horizon specification."}
    }


def evaluate_candidate(history:list[Observation],origins:list[dict],truth_cutoff:str,
                       *, final_holdout_start:str):
    """Evaluate on exactly the benchmark protocol's dates and vintages.

    Missing target, insufficient training or holdout intersections are excluded.
    Forecast errors use *as-of* training and a separately dated truth cutoff.
    Interval radius is estimated from the training prefix for EACH origin.
    """
    _timestamp(truth_cutoff)
    if not isinstance(final_holdout_start,str) or not len(final_holdout_start)==7:
        raise ForecastError("Locked final holdout month required.")
    _month_number(final_holdout_start)
    history=_validate_history(history)
    origins=_origin_dates(origins)
    truth=as_of(history,truth_cutoff)
    results=[]
    excluded=[]
    for origin in origins:
        om=origin["month"];at=origin["available_at"]
        if _timestamp(at)>_timestamp(truth_cutoff):
            raise ForecastError("Forecast origin cannot occur after evaluation cutoff.")
        try:
            train,proof=_training(history,om,at)
        except ForecastError as exc:
            excluded.append({"origin":om,"reason":str(exc)})
            continue
        scale=_scale(train)
        interval=calibrate_intervals(train)
        for horizon in HORIZONS:
            target=_month_string(_month_number(om)+horizon)
            if target>=final_holdout_start:
                excluded.append({"origin":om,"horizon":horizon,
                                 "reason":"Locked final 24-month holdout."})
                continue
            target_row=truth.get(target)
            if target_row is None or target_row.value is None:
                excluded.append({"origin":om,"horizon":horizon,
                                 "reason":"Target truth not available."})
                continue
            radius=interval[str(horizon)]["half_width"]
            for method in ("candidate",)+METHODS:
                f=point_forecast(train,horizon) if method=="candidate" else predict(method,train,horizon)
                if method=="candidate" and radius is not None:
                    lower=max(0.0,f-radius);upper=f+radius
                else:lower=upper=None
                results.append({
                  "origin":om,"target":target,"horizon":horizon,"method":method,
                  "origin_at":at,"actual":target_row.value,"forecast":f,
                  "target_vintage":target_row.source_vintage,
                  "information_latest_vintage":proof["latest_source_vintage"],
                  "information_max_available_at":proof["max_information_time"],
                  "mase":abs(f-target_row.value)/scale if scale is not None else None,
                  "smape":_smape(target_row.value,f),
                  "lower":lower,"upper":upper
                })
    metrics={}
    for method in ("candidate",)+METHODS:
        metrics[method]={str(h):_metrics([r for r in results
                          if r["method"]==method and r["horizon"]==h]) for h in HORIZONS}
    return {
       "protocol_version":"firmablick-forecast-evaluation-v1.0.0",
       "model_id":MODEL_ID,"model_version":MODEL_VERSION,
       "history_evidence":"not_independently_certified",
       "publication_approved":False,
       "final_holdout_start":final_holdout_start,"truth_cutoff":truth_cutoff,
       "predictions":results,"excluded":excluded,"metrics":metrics,
       "origin_count":len({r["origin"] for r in results}),
       "superiority_claim_permitted":False
    }


def predeclared_gate(evaluation:dict)->dict:
    """No path to public approval in Issue #14. Expose objective failure reasons."""
    if evaluation.get("history_evidence")!="official_independently_certified":
        return {"approved":False,"mode":"benchmark_only",
                "reason":"Authentic point-in-time source vintages not independently certified."}
    if evaluation.get("origin_count",0)<24:
        return {"approved":False,"mode":"benchmark_only",
                "reason":"Fewer than 24 eligible rolling origins."}
    for horizon in HORIZONS:
        candidate=evaluation["metrics"]["candidate"][str(horizon)]
        baseline=evaluation["metrics"]["seasonal_naive"][str(horizon)]
        if candidate["n"]<12 or candidate["n"]!=baseline["n"]:
            return {"approved":False,"mode":"benchmark_only",
                    "reason":f"Horizon {horizon}: insufficient comparable observations."}
        if candidate["mae"] is None or baseline["mae"] is None or (
                baseline["mae"]<=0 or candidate["mae"]>0.95*baseline["mae"]):
            return {"approved":False,"mode":"benchmark_only",
                    "reason":f"Horizon {horizon}: predeclared MAE improvement not established."}
        if candidate["interval_count"]<20 or candidate["interval_coverage"] is None or not (
           0.8<=candidate["interval_coverage"]<=0.98):
            return {"approved":False,"mode":"benchmark_only",
                    "reason":f"Horizon {horizon}: unverified prediction interval coverage."}
    return {"approved":False,"mode":"benchmark_only",
            "reason":"Independent locked final holdout and human statistical release approval not recorded."}
