"""Prespecified development-only fitting and chronological validation.

CLI requires a successful backend-test receipt matching these exact sources.
All output directories are exclusive. This module never loads suffixes/keys.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import csv
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import resource
import sys
import threading
import time
import warnings

import numpy as np
import xgboost as xgb

from .development_qualification_v1 import EPOCH, PRIMARY_IDS, PREFIX_DIRECTORY, validate_prefix_csv, example_origins
from .contracts import identifier
from .real_adapters_v1 import (ArtifactReference,IDENTITY,FEATURE_SPEC,canonical_hash,digest_bytes,sarimax_model)
from .real_streaming_v1 import RealStreamingSimulator
from .streaming_v2 import _write_json

ROOT=Path(__file__).resolve().parents[2]
NEW_SOURCES=("src/dafr/real_adapters_v1.py","src/dafr/real_streaming_v1.py","src/dafr/run_m3b2_v1.py",
             "tests/test_dafr_real_backends_v1.py","configs/dafr_m3b2_execution_v1.json")


def write_new(path,value):
    with Path(path).open("x") as handle:_write_json(handle,value)


def peak_rss():
    n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform=="darwin" else n*1024)


def enforce_memory(limit=4*1024**3):
    if peak_rss()>limit:raise MemoryError("Process exceeded the frozen 4 GiB RSS budget")


def load_execution(root=ROOT):
    root=Path(root).resolve()
    cfg=json.loads((root/"configs/dafr_m3b2_execution_v1.json").read_text())
    if (cfg.get("schema_version"),cfg.get("scope"))!=("dafr_m3b2_execution_v1","SELECTED_DEVELOPMENT_PREFIX_INNER_PILOT_ONLY"):
        raise ValueError("Wrong execution scope")
    if cfg.get("training_authorized") is not True or cfg.get("m3_training_allowed") is not True or cfg.get("confirmation_execution_allowed") is not False:
        raise ValueError("Training authorization/confirmation lock mismatch")
    if cfg["allowed_machine_ids"]!=list(PRIMARY_IDS) or cfg["fit"]!=[0,864] or cfg["validation"]!=[864,1152] or cfg["horizons"]!=[1,12]:
        raise ValueError("Only the frozen three-machine inner pilot is authorized")
    if cfg["maximum_process_rss_bytes"]!=4*1024**3 or cfg["numeric_threads"]!=1 or cfg["confirmation_or_suffix_access_allowed"] is not False:
        raise ValueError("Resource/data boundary changed")
    path=root/"configs/dafr_m3b_development_manifest_v1.json"
    if cfg["plan_path"]!=str(path.relative_to(root)) or digest_bytes(path.read_bytes())!=cfg["plan_sha256"]:
        raise ValueError("Frozen plan fingerprint mismatch")
    plan=json.loads(path.read_text())
    for machine in PRIMARY_IDS:
        expected={"path":str(PREFIX_DIRECTORY/f"{machine}.csv"),"sha256":plan["machine_evidence"][machine]["source_sha256"]}
        if cfg["source_files"][machine]!=expected:raise ValueError("Source admission changed")
    return cfg,plan


def load_source(machine,cfg,root=ROOT):
    if machine not in PRIMARY_IDS or machine not in cfg["allowed_machine_ids"]:
        raise ValueError("Reserves/confirmation machines cannot enter this pilot")
    path=Path(root).resolve()/PREFIX_DIRECTORY/f"{machine}.csv"
    if path.resolve()!=path:raise ValueError("Source symlink redirection")
    payload=path.read_bytes()
    if digest_bytes(payload)!=cfg["source_files"][machine]["sha256"]:raise ValueError("Source hash mismatch")
    mask=validate_prefix_csv(payload)
    rows=list(csv.DictReader(io.StringIO(payload.decode())))
    values=tuple(float(r["value"]) if good else None for r,good in zip(rows,mask))
    return values,mask


def training_arrays(fit_values,horizon):
    if len(fit_values)>864:raise ValueError("Training cannot receive validation observations")
    mask=tuple(v is not None for v in fit_values)
    origins=example_origins(mask,horizon,0,len(mask))
    features=np.asarray([[fit_values[i-o] for o in FEATURE_SPEC["origin_offsets"]] for i in origins],dtype=np.float32)
    targets=np.asarray([fit_values[i+horizon] for i in origins],dtype=np.float32)
    return features,targets,origins


def save_artifact(directory,machine,source_hash,fit_values,family,candidate_index,plan,
                  *,synthetic=False,known_params=None):
    """Fit only supplied fit values; synthetic known-parameter fixtures bypass optimization."""
    directory=Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=False)
    if not synthetic and (machine not in PRIMARY_IDS or len(fit_values)!=864):
        raise ValueError("Wrong training source/window")
    if family not in ("arima","xgboost") or type(candidate_index) is not int or candidate_index not in (0,1,2):
        raise ValueError("Candidate not in frozen registry")
    started=datetime.now(timezone.utc).isoformat(); start=time.perf_counter()
    cutoff=EPOCH+timedelta(seconds=300*len(fit_values))
    m={"scope":"synthetic_backend_test" if synthetic else "selected_development_inner_pilot",
       "machine_id":machine,"source_sha256":source_hash,"fit_values_sha256":canonical_hash(list(fit_values)),
       "fit_grid_size":len(fit_values),"family":family,"candidate_index":candidate_index,
       "version":f"{family}_c{candidate_index+1}_"+canonical_hash(list(fit_values))[:10],
       "training_cutoff":cutoff.isoformat(),"checkpoint_cutoff":cutoff.isoformat(),
       "identity_scaler":True,"status":"accepted","warnings":[],"hashes":{},
       "build_started_wall_clock_utc":started,"selection_uses_validation":False,
       "replay_availability_assumption":"Prespecified candidate prebuilt offline before validation; event-time cutoff is not physical build time",
       "dependencies":{p:importlib.metadata.version(p) for p in ("numpy","statsmodels","xgboost")},
       "python":sys.version,"seed":42}
    write_new(directory/"scaler.json",IDENTITY); write_new(directory/"features.json",FEATURE_SPEC)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        try:
            if family=="arima":
                order=plan["arima"]["candidate_orders"][candidate_index]; m["order"]=order
                model=sarimax_model([np.nan if v is None else v for v in fit_values],order)
                if known_params is not None:
                    if not synthetic:raise ValueError("Known parameters are backend fixtures only")
                    result=model.filter(known_params)
                else:
                    result=model.fit(method="lbfgs",maxiter=200,disp=False)
                params=np.asarray(result.params,dtype=float)
                roots={name:np.asarray(getattr(result,name)) for name in ("arroots","maroots")}
                converged=bool(result.mle_retvals.get("converged",False)) if known_params is None else True
                variance=float(params[result.param_names.index("sigma2")])
                invalid=[]
                if not converged:invalid.append("not_converged")
                if not np.all(np.isfinite(params)) or not np.isfinite(result.llf) or not np.isfinite(result.aic):invalid.append("nonfinite_objective_or_parameters")
                if variance<=0 or not np.isfinite(variance):invalid.append("invalid_variance")
                for name,r in roots.items():
                    if r.size and (not np.all(np.isfinite(r)) or np.any(np.abs(r)<=1+1e-6)):invalid.append(name+"_invalid")
                m["diagnostics"]={"converged":converged,"llf":float(result.llf) if np.isfinite(result.llf) else None,
                    "aic":float(result.aic) if np.isfinite(result.aic) else None,"sigma2":variance if np.isfinite(variance) else None,
                    "nobs":int(result.nobs),"loglikelihood_burn":int(result.loglikelihood_burn),
                    "roots":{name:[{"real":float(v.real),"imag":float(v.imag),"modulus":float(abs(v))} for v in r if np.isfinite(v)] for name,r in roots.items()},
                    "rejection_reasons":invalid}
                if not np.all(np.isfinite(params)):m["status"]="rejected"
                else:write_new(directory/"params.json",params.tolist())
                m["parameter_sha256"]=digest_bytes(params.astype(np.float64).tobytes())
                if invalid:m["status"]="rejected"
                m["training_targets_sha256"]=canonical_hash([[i,v] for i,v in enumerate(fit_values) if v is not None])
            else:
                settings=plan["xgboost"]["candidate_configurations"][candidate_index]
                m["configuration"]={**plan["xgboost"]["fixed_settings"],**settings}
                m["weight_sha256"]={}; m["training_examples"]={}
                for h in (1,12):
                    x,y,origins=training_arrays(fit_values,h)
                    model=xgb.XGBRegressor(**m["configuration"])
                    model.fit(x,y)
                    # Persist the native booster, matching the registered load
                    # type. The sklearn saver adds a wrapper-only attribute.
                    model.get_booster().save_model(directory/f"model_h{h}.json")
                    m["weight_sha256"][str(h)]=digest_bytes(bytes(model.get_booster().save_raw(raw_format="json")))
                    m["training_examples"][str(h)]={"count":len(origins),"origin_index_sha256":canonical_hash(origins),
                        "target_index_sha256":canonical_hash([i+h for i in origins]),
                        "targets_float32_sha256":digest_bytes(y.tobytes()),"features_float32_sha256":digest_bytes(x.tobytes()),
                        "latest_target_index":max(i+h for i in origins)}
                    enforce_memory()
        except MemoryError:
            raise
        except (ValueError,ArithmeticError,RuntimeError,np.linalg.LinAlgError,xgb.core.XGBoostError) as error:
            m["status"]="rejected"; m["exception"]={"type":type(error).__name__,"message":str(error)}
        m["warnings"]=[{"category":w.category.__name__,"message":str(w.message)} for w in captured]
        if family=="arima" and any(w.category.__name__=="ConvergenceWarning" for w in captured):
            m["status"]="rejected"
            m.setdefault("diagnostics",{}).setdefault("rejection_reasons",[]).append("ConvergenceWarning")
    enforce_memory()
    m["build_completed_wall_clock_utc"]=datetime.now(timezone.utc).isoformat()
    m["fit_seconds"]=time.perf_counter()-start
    m["process_peak_rss_bytes_at_fit_end"]=peak_rss()
    for path in directory.iterdir():
        if path.is_file():m["hashes"][path.name]=digest_bytes(path.read_bytes())
    write_new(directory/"metadata.json",m)
    return ArtifactReference(directory,digest_bytes((directory/"metadata.json").read_bytes()),source_hash,m["fit_values_sha256"],machine),m


def metrics(items):
    if not items:return {"count":0,"mae":None,"rmse":None}
    return {"count":len(items),"mae":sum(o.absolute_error for o in items)/len(items),
            "rmse":math.sqrt(sum(o.squared_error for o in items)/len(items))}


def replay_trial(directory,reference,values):
    directory.mkdir(parents=True,exist_ok=False)
    trial_id=f"{directory.parents[1].name}-{reference.machine_id}-{directory.name}"
    simulator=RealStreamingSimulator(trial_id,"alibaba_development_inner",reference,values[:864])
    write_new(directory/"bootstrap.json",{"fit_state_cutoff":simulator._versions[reference.directory.name.split('_')[0]].available_at,
        "initial_era_from_fit_mask":simulator.bootstrap_era,"history_slots":23,"duplicate_model_updates":0})
    start=time.perf_counter()
    with (directory/"events.jsonl").open("x") as events,(directory/"predictions.jsonl").open("x") as predictions:
        for i in range(864,1152):
            value=values[i]
            step=simulator.advance(EPOCH+timedelta(seconds=300*(i+1)),value,"quality_failed" if value is None else None)
            for kind,event in step.ordered():_write_json(events,{"kind":kind,"record":asdict(event)})
            for f in step.decisions:_write_json(predictions,asdict(f))
            enforce_memory()
    forecasts={f.forecast_id:f for f in simulator.ledger.decisions}
    outcomes=[o for o in simulator.ledger.outcomes if o.status=="scored"]
    persistence={(o.origin,o.horizon):o for o in outcomes if o.policy_id=="persistence"}
    family=next(iter(simulator._adapters))
    rows=[]
    for h in (1,12):
        decisions=[f for f in forecasts.values() if f.policy_id==family and f.horizon==h]
        scored=[o for o in outcomes if o.policy_id==family and o.horizon==h]
        common=[o for o in scored if forecasts[o.forecast_id].learned_eligible]
        expert=[o for o in common if forecasts[o.forecast_id].availability=="expert"]
        row={"machine_id":reference.machine_id,"family":family,"horizon":h,
             "matched_gate_policy":metrics(common),"persistence_matched_gate":metrics([persistence[(o.origin,h)] for o in common]),
             "expert_only":metrics(expert),"persistence_same_expert_origins":metrics([persistence[(o.origin,h)] for o in expert]),
             "complete_policy":metrics(scored),"persistence_complete_policy":metrics([o for o in outcomes if o.policy_id=="persistence" and o.horizon==h]),
             "expert_predictions":sum(f.availability=="expert" for f in decisions),
             "fallbacks":sum(f.availability=="fallback" for f in decisions),"abstentions":sum(not f.issued for f in decisions),
             "missing_targets":sum(o.policy_id==family and o.horizon==h and o.status=="target_unavailable" for o in simulator.ledger.outcomes),
             "pending":sum(f.forecast_id in simulator.ledger.pending_ids for f in decisions),
             "numerical_update_events":0,"numerical_forecast_events":0}
        rows.append(row)
    # Failure counts come from the complete immutable event ledger, not inferred
    # from fallback frequency (history-gate fallback is not a numerical error).
    for line in (directory/"events.jsonl").read_text().splitlines():
        event=json.loads(line); rec=event["record"]
        if event["kind"]=="adapter_update" and rec["status"]=="numerical_failure":
            for row in rows:row["numerical_update_events"]+=1
        if event["kind"]=="adapter_attempt" and rec["status"]=="numerical_failure":
            next(r for r in rows if r["horizon"]==rec["horizon"])["numerical_forecast_events"]+=1
    summary={"metrics":rows,"replay_seconds":time.perf_counter()-start,"resources":simulator.resource_reports(),
        "process_peak_rss_bytes_through_replay":peak_rss(),"pending_forecast_ids":simulator.ledger.pending_ids,
        "label":"DEVELOPMENT VALIDATION"}
    write_new(directory/"summary.json",summary)
    return rows,summary


def choose_global(rows,fit_receipts):
    results={}
    for family in ("arima","xgboost"):
        candidates=[]
        for c in (0,1,2):
            fits=[m for m in fit_receipts if m["family"]==family and m["candidate_index"]==c]
            scores=[r for r in rows if r["family"]==family and r["candidate_index"]==c and r["horizon"]==1]
            valid=len(fits)==3 and all(m["status"]=="accepted" for m in fits) and len(scores)==3
            candidates.append({"candidate_index":c,"eligible":valid,
                "macro_h1_mae":sum(r["matched_gate_policy"]["mae"] for r in scores)/3 if valid else None,
                "macro_h1_rmse":sum(r["matched_gate_policy"]["rmse"] for r in scores)/3 if valid else None})
        eligible=[c for c in candidates if c["eligible"]]
        if eligible:
            best=min(c["macro_h1_mae"] for c in eligible)
            winner=min([c for c in eligible if c["macro_h1_mae"]<=best+1e-9],key=lambda c:(c["macro_h1_rmse"],c["candidate_index"]))["candidate_index"]
        else:winner=None
        results[family]={"winner_candidate_index":winner,"candidates":candidates}
    return {"label":"DEVELOPMENT VALIDATION ONLY","selected_after_all_replays":True,
        "selection_cutoff_index":1151,"h12_selected_separately":False,"families":results}


def export_reports(directory,rows,selection,receipts,runtime):
    if directory.resolve()!=directory:raise ValueError("Symlinked report directory")
    directory.mkdir(parents=True,exist_ok=False)
    write_new(directory/"selection.json",selection)
    write_new(directory/"metrics.json",rows)
    write_new(directory/"runtime.json",runtime)
    flat=[]
    for r in rows:
        q={k:v for k,v in r.items() if not isinstance(v,dict)}
        for key,value in r.items():
            if isinstance(value,dict):q.update({f"{key}_{k}":v for k,v in value.items()})
        flat.append(q)
    with (directory/"validation_metrics.csv").open("x",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for h in (1,12):
        names=[]; scores=[]
        for family in ("arima","xgboost"):
            for c in (0,1,2):
                rr=[r for r in rows if r["family"]==family and r["candidate_index"]==c and r["horizon"]==h]
                names.append(f"{family} C{c+1}");scores.append(sum(r["matched_gate_policy"]["mae"] for r in rr)/3)
        baseline=[r for r in rows if r["family"]=="xgboost" and r["candidate_index"]==0 and r["horizon"]==h]
        names.append("persistence");scores.append(sum(r["persistence_matched_gate"]["mae"] for r in baseline)/3)
        fig,ax=plt.subplots(figsize=(10,4.5));ax.bar(names,scores,color=["#3973ac"]*3+["#32917a"]*3+["#888888"])
        ax.set_ylabel("Macro MAE (CPU percentage points)");ax.set_title(f"DEVELOPMENT VALIDATION — h={h}; matched genuine targets")
        ax.tick_params(axis="x",rotation=25);fig.tight_layout();fig.savefig(directory/f"matched_mae_h{h}.png",dpi=160);plt.close(fig)
    lines=["# M3B-2 model selection — DEVELOPMENT VALIDATION", "", "No independent final-test or DAF-R improvement claim. Winners are designated only after all candidate replays.","",
        "| Family | Selected candidate | Macro h=1 MAE | Macro h=1 RMSE |", "|---|---:|---:|---:|"]
    for family,item in selection["families"].items():
        winner=item["winner_candidate_index"]
        if winner is None:lines.append(f"| {family} | No eligible candidate | — | — |")
        else:
            score=item["candidates"][winner];lines.append(f"| {family} | C{winner+1} | {score['macro_h1_mae']:.6f} | {score['macro_h1_rmse']:.6f} |")
    lines += ["", "All h=12 results use those same settings. AIC was recorded but not used to select ARIMA.","",
        "See validation_metrics.csv for per-machine/horizon expert-only matched accuracy, persistence on identical origins, common-gate policy accuracy and complete-policy availability.","",
        "A failed fit is excluded from global promotion; its fallback ledger remains in the tables. Candidate plots include complete common-gate policies, including fallback, so a rejected fit can resemble persistence and is not an accepted ARIMA result."]
    (directory/"model_selection.md").write_text("\n".join(lines)+"\n")
    write_new(directory/"fit_diagnostics.json",receipts)


def verify_history():
    receipt=json.loads((ROOT/"reports/dafr/m3b2_preservation_v1.json").read_text())
    for p,h in receipt["protected_sha256"].items():
        if digest_bytes((ROOT/p).read_bytes())!=h:raise ValueError(f"Protected artifact changed: {p}")


def run(run_id,backend_receipt):
    identifier(run_id);cfg,plan=load_execution();verify_history()
    receipt=json.loads(Path(backend_receipt).read_text())
    if receipt.get("passed") is not True:raise ValueError("Successful backend tests required")
    for source in NEW_SOURCES:
        if receipt["source_sha256"].get(source)!=digest_bytes((ROOT/source).read_bytes()):
            raise ValueError("Backend receipt is stale; rerun tests before real fitting")
    base=ROOT/"data/processed/dafr/m3b2_development_v1";modelbase=ROOT/"models/dafr/m3b2_development_v1"
    for parent in (base,modelbase):
        if parent.resolve()!=parent:raise ValueError("Symlinked output path")
        parent.mkdir(parents=True,exist_ok=True)
    output=base/run_id;output.mkdir(exist_ok=False)
    reports=ROOT/"reports/dafr/m3b2_v1"/run_id
    if reports.exists() or reports.resolve()!=reports:raise FileExistsError("Report namespace already reserved or redirected")
    models=modelbase/run_id;models.mkdir(exist_ok=False)
    write_new(output/"execution_manifest.json",{"execution":cfg,"backend_receipt":receipt,"run_id":run_id,
        "training_authorized_only_here":True,"confirmation_execution_allowed":False})
    stop=threading.Event()
    def watchdog():
        while not stop.wait(.05):
            if peak_rss()>cfg["maximum_process_rss_bytes"]:
                write_new(output/"resource_stop.json",{"reason":"RSS exceeded 4 GiB","rss":peak_rss()})
                os._exit(70)
    thread=threading.Thread(target=watchdog,daemon=True);thread.start()
    all_rows=[];fits=[];runtimes=[];started=time.perf_counter()
    completion={"status":"failed"}
    try:
        for machine in PRIMARY_IDS:
            values,mask=load_source(machine,cfg)
            for family in ("arima","xgboost"):
                for candidate in (0,1,2):
                    enforce_memory()
                    name=f"{family}_c{candidate+1}"
                    reference,fit=save_artifact(models/machine/name,machine,cfg["source_files"][machine]["sha256"],values[:864],family,candidate,plan)
                    if family=="xgboost" and fit["status"]=="accepted":
                        for h in (1,12):
                            expected=plan["machine_evidence"][machine]["per_horizon"][str(h)]
                            actual=fit["training_examples"][str(h)]
                            if actual["count"]!=expected["xgboost_direct_training_examples"] or actual["origin_index_sha256"]!=expected["training_origin_index_sha256"]:
                                raise ValueError("Actual training examples differ from frozen plan")
                    fits.append(fit)
                    rows,summary=replay_trial(output/machine/name,reference,values)
                    for row in rows:
                        row.update(candidate_index=candidate,fit_status=fit["status"])
                        if row["matched_gate_policy"]["count"]!=plan["machine_evidence"][machine]["per_horizon"][str(row["horizon"])]["arima_xgboost_lstm_common_validation_pairs"]:
                            raise ValueError("Scoring denominator differs from frozen plan")
                    all_rows.extend(rows);runtimes.append({"machine":machine,"family":family,"candidate":candidate,**{k:v for k,v in summary.items() if k not in ("metrics","pending_forecast_ids")}})
                    write_new(output/machine/name/"fit_receipt.json",{"metadata_sha256":reference.metadata_sha256,"model_directory":str(reference.directory)})
        selection=choose_global(all_rows,fits)
        runtime={"elapsed_seconds":time.perf_counter()-started,"peak_process_rss_bytes":peak_rss(),"rss_limit_bytes":4*1024**3,
            "measurement":"Process high-water mark; cumulative across serial candidates, not incremental per-model RAM", "trials":runtimes}
        export_reports(ROOT/"reports/dafr/m3b2_v1"/run_id,all_rows,selection,fits,runtime)
        verify_history()
        completion={"status":"completed","trials":18,"parameter_fits_prespecified":27,"confirmation_execution_allowed":False,
                    "elapsed_seconds":time.perf_counter()-started,"peak_process_rss_bytes":peak_rss()}
    except Exception as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:
        stop.set();thread.join(timeout=1);write_new(output/"completion.json",completion)
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id",required=True);parser.add_argument("--backend-receipt",required=True)
    args=parser.parse_args();print(run(args.run_id,args.backend_receipt))
