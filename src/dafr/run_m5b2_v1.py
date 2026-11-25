"""Frozen retrospective diagnostic; links existing forecasts, never fits/models."""
from dataclasses import asdict
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
import argparse
import csv
import hashlib
import json
import math
import resource
import sys
import time

from .contracts import identifier
from .selector_v1 import ROOT
from .retrospective_sources_v1 import LABEL,MACHINES,load_config,load_m4a_input
from .retrospective_replay_v1 import RetrospectiveReplayV1
from .streaming_v2 import _write_json

SOURCES=('configs/dafr_m5b2_retrospective_v1.json','src/dafr/retrospective_sources_v1.py',
    'src/dafr/retrospective_replay_v1.py','src/dafr/run_m5b2_v1.py','src/dafr/audit_m5b2_v1.py',
    'tests/test_dafr_retrospective_v1.py')


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify_history():
    inventory=json.loads((ROOT/'reports/dafr/m5b2_preservation_v1.json').read_text())
    for name,sha in inventory['protected_sha256'].items():
        if file_sha(ROOT/name)!=sha:raise ValueError('Historical artifact changed: '+name)
    return inventory['file_count']


def write_new(path,value):
    with Path(path).open('x') as out:_write_json(out,value)


def write_csv(path,rows):
    with Path(path).open('x',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def error_metrics(errors):
    return {'count':len(errors),'mae':sum(abs(e) for e in errors)/len(errors) if errors else None,
        'rmse':math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None}


def comparisons(inputs,replay):
    sources={s.forecast.forecast_id:s.forecast for f in inputs.frames for s in f.forecasts}
    scored={p:{} for p in ('persistence','arima','xgboost','adaptive')}
    expert={p:set() for p in scored}
    for frame in inputs.frames:
        for o in frame.outcomes:
            if o.status!='scored':continue
            key=(o.origin,o.target,o.horizon);scored[o.policy_id][key]=o.signed_error
            if o.policy_id=='persistence' or sources[o.forecast_id].availability=='expert':expert[o.policy_id].add(key)
    adaptive={d.decision_id:d for d in replay.decisions}
    for o in replay.outcomes:
        if o.status!='scored':continue
        key=(o.origin,o.target,o.horizon);scored['adaptive'][key]=o.signed_error
        if adaptive[o.decision_id].availability=='expert':expert['adaptive'].add(key)
    rows=[]
    for h in (1,12):
        for scope in ('expert_matched','complete_policy_matched'):
            sets=[{k for k in (expert[p] if scope=='expert_matched' else scored[p]) if k[2]==h} for p in scored]
            keys=set.intersection(*sets)
            for policy in scored:
                rows.append({'label':LABEL,'machine':inputs.machine,'horizon':h,'scope':scope,'policy':policy,
                    **error_metrics([scored[policy][k] for k in sorted(keys)]),
                    'own_complete_genuine_count':sum(k[2]==h for k in scored[policy]),
                    'own_expert_genuine_count':sum(k[2]==h for k in expert[policy])})
    return rows


def macro_metrics(rows):
    output=[]
    for h in (1,12):
        for scope in ('expert_matched','complete_policy_matched'):
            for policy in ('persistence','arima','xgboost','adaptive'):
                group=[r for r in rows if (r['horizon'],r['scope'],r['policy'])==(h,scope,policy)]
                supported=len(group)==3 and all(r['count']>0 for r in group)
                output.append({'label':LABEL,'horizon':h,'scope':scope,'policy':policy,'machine_count':len(group),
                    'total_common_targets':sum(r['count'] for r in group),'all_machines_supported':supported,
                    'mae':sum(r['mae'] for r in group)/3 if supported else None,
                    'rmse':sum(r['rmse'] for r in group)/3 if supported else None})
    return output


def availability(inputs,replay,steps):
    rows=[];source_ids={s.forecast.forecast_id:s.forecast for f in inputs.frames for s in f.forecasts}
    for h in (1,12):
        for policy in ('persistence','arima','xgboost','adaptive'):
            if policy=='adaptive':
                ds=[d for d in replay.decisions if d.horizon==h];os=[o for o in replay.outcomes if o.horizon==h]
                pending=set(replay.pending_ids);id_key='decision_id'
            else:
                ds=[f for f in source_ids.values() if f.horizon==h and f.policy_id==policy]
                os=[o for frame in inputs.frames for o in frame.outcomes if o.horizon==h and o.policy_id==policy]
                resolved={o.forecast_id for o in os};pending={d.forecast_id for d in ds if d.issued and d.forecast_id not in resolved};id_key='forecast_id'
            rows.append({'label':LABEL,'machine':inputs.machine,'horizon':h,'policy':policy,'decisions':len(ds),
                **{name:sum(d.availability==name for d in ds) for name in ('expert','baseline','fallback','abstained')},
                'genuine_scored':sum(o.status=='scored' for o in os),'missing_targets':sum(o.status=='target_unavailable' for o in os),
                'pending':sum(getattr(d,id_key) in pending for d in ds)})
    support=[]
    for h in (1,12):
        snapshots=[next(s for s in step.selections if s.horizon==h) for step in steps]
        eligible=[i for i,(step,s) in enumerate(zip(steps,snapshots)) if s.matched_count>=100 and step.context.learned_eligible and
            all(next(x for x in inputs.frames[i].forecasts if x.forecast.policy_id==p and x.forecast.horizon==h).forecast.availability=='expert' for p in ('arima','xgboost')) and s.dwell_elapsed_ticks>=24]
        ready=[s.timestamp for s in snapshots if s.matched_count>=100]
        switches=[asdict(s) for s in snapshots if s.switched]
        support.append({'label':LABEL,'machine':inputs.machine,'horizon':h,'switches':len(switches),'switch_records':switches,
            'first_100_pair_origin':ready[0] if ready else None,'ready_ticks':len(ready),'eligible_to_consider_switch_ticks':len(eligible),
            'first_eligible_origin':snapshots[eligible[0]].timestamp if eligible else None,
            'maximum_support':max(s.matched_count for s in snapshots),'final_support':snapshots[-1].matched_count,
            'age_expirations':sum(step.state.expired_by_age[(0 if h==1 else 1)] for step in steps),
            'capacity_evictions':sum(step.state.capacity_evictions[(0 if h==1 else 1)] for step in steps),
            'telemetry_resets':sum(step.state.reset for step in steps),
            'lifetime_matched_pairs':sum(p.horizon==h for step in steps for p in step.pairs)})
    return rows,support


def private_plots(directory,inputs,replay,steps):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    directory.mkdir(exist_ok=False)
    indices=np.arange(1152,1612);times={f.tick.timestamp:i for i,f in enumerate(inputs.frames)}
    colors={'persistence':'#888888','arima':'#3973ac','xgboost':'#32917a','adaptive':'#aa4477'}
    for h in (1,12):
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True)
        actual=[f.tick.value if f.tick.genuine else np.nan for f in inputs.frames]
        axes[0].plot(indices,actual,color='black',lw=1,label='Genuine CPU')
        for policy,color in colors.items():
            forecast=np.full(460,np.nan);errors=np.full(460,np.nan)
            if policy=='adaptive':ds=[d for d in replay.decisions if d.horizon==h];os=[o for o in replay.outcomes if o.horizon==h]
            else:
                ds=[s.forecast for f in inputs.frames for s in f.forecasts if s.forecast.policy_id==policy and s.forecast.horizon==h]
                os=[o for f in inputs.frames for o in f.outcomes if o.policy_id==policy and o.horizon==h]
            for d in ds:
                if d.target in times and d.predicted_value is not None:forecast[times[d.target]]=d.predicted_value
            for o in os:
                if o.status=='scored':errors[times[o.target]]=o.absolute_error
            axes[0].plot(indices,forecast,color=color,lw=.8,alpha=.8,label=policy)
            axes[1].plot(indices,errors,color=color,lw=.8,label=policy)
        axes[0].set_title(f'{LABEL}\n{inputs.machine}, h={h}, complete policies')
        axes[0].set_ylabel('CPU utilization (%)');axes[0].legend(ncol=3,fontsize=8)
        axes[1].set_ylabel('Genuine exact-target absolute error');axes[1].set_xlabel('Original five-minute grid index')
        fig.tight_layout();fig.savefig(directory/f'forecast_errors_h{h}.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
    for ax,h in zip(axes,(1,12)):
        ss=[next(s for s in step.selections if s.horizon==h) for step in steps]
        ax.plot(indices,[s.matched_count for s in ss],color='#3973ac',label='Genuine matched support')
        ax.axhline(100,color='#777777',ls='--',label='100-pair minimum')
        ax.scatter([1152+i for i,s in enumerate(ss) if s.switched],[s.matched_count for s in ss if s.switched],color='#aa4477',marker='*',s=85,label='Loss-based switch')
        ax.set_ylabel(f'h={h} matched pairs');ax.set_ylim(0,305);ax.legend(fontsize=8,loc='lower right')
    axes[0].set_title(f'{LABEL}\n{inputs.machine}: independent horizon support and switches')
    axes[1].set_xlabel('Original five-minute origin index');fig.tight_layout();fig.savefig(directory/'support_switches.png',dpi=140);plt.close(fig)


def aggregate_plots(report,macro):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for scope in ('expert_matched','complete_policy_matched'):
        fig,axes=plt.subplots(2,2,figsize=(11,7))
        for row,h in enumerate((1,12)):
            for col,metric in enumerate(('mae','rmse')):
                ax=axes[row,col];group=[r for r in macro if r['horizon']==h and r['scope']==scope]
                values=[r[metric] if r[metric] is not None else float('nan') for r in group]
                bars=ax.bar([r['policy'] for r in group],values,color=['#888888','#3973ac','#32917a','#aa4477'])
                ax.bar_label(bars,fmt='%.3f',padding=3,fontsize=8);ax.set_ylabel(f'h={h} macro {metric.upper()} (CPU pp)')
                finite=[v for v in values if not math.isnan(v)]
                if finite:ax.set_ylim(0,max(finite)*1.2)
        fig.suptitle(f'{LABEL}\n{scope}; equal-machine averages',fontsize=12)
        fig.tight_layout(rect=(0,0,1,.92));fig.savefig(report/(scope+'.png'),dpi=150);plt.close(fig)


def run(run_id,output_root=ROOT):
    identifier(run_id);config,_,config_sha=load_config()
    output=Path(output_root).resolve()/'data/processed/dafr/m5b2_retrospective_v1'/run_id
    report=Path(output_root).resolve()/'reports/dafr/m5b2_v1'/run_id
    for p in (output,report):
        if p.resolve()!=p:raise ValueError('Output redirection forbidden')
        if p.exists():raise FileExistsError('Retrospective run ID already exists')
    gate=json.loads((ROOT/'reports/dafr/m5b2_replay_gate_v1.json').read_text())
    if gate.get('passed') is not True or any(gate['source_sha256'].get(s)!=file_sha(ROOT/s) for s in SOURCES):raise ValueError('Current successful source/test gate required')
    output.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    write_new(output/'manifest.json',{'label':LABEL,'run_id':run_id,'configuration':config,'config_sha256':config_sha,
        'created_wallclock_utc':datetime.now(timezone.utc),'model_fits':0,'models_loaded':0,'source_preflight':'Previously completed; not rerun wholesale',
        'algorithm_available_after_source_index':1611,'retrospective_simulated_event_time_only':True})
    start=time.perf_counter();completion={'status':'failed','label':LABEL}
    metric_rows=[];availability_rows=[];supports=[];audits={};runtimes=[]
    try:
        for machine in MACHINES:
            inputs=load_m4a_input(machine);directory=output/machine;directory.mkdir(exist_ok=False)
            write_new(directory/'source_manifest.json',{'label':LABEL,'source_artifacts_sha256':dict(inputs.source_hashes),
                'prefix_slots':23,'pre_block_losses_imported':0,'pre_block_forecasts_imported':0,'initial_era':inputs.initial_era})
            replay=RetrospectiveReplayV1(run_id,inputs,config_sha);steps=[];begin=time.perf_counter()
            with ExitStack() as stack:
                handles={name:stack.enter_context((directory/(name+'.jsonl')).open('x')) for name in
                    ('events','decisions','outcomes','selections','matched_losses','switches','resets')}
                for frame in inputs.frames:
                    if rss_bytes()>4*1024**3:raise MemoryError('4 GiB process RSS budget exceeded')
                    step=replay.advance(frame);steps.append(step)
                    for e in step.events:
                        _write_json(handles['events'],{'label':LABEL,'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)})
                        name={'selector_state':'selections','matched_shadow_loss':'matched_losses','expert_switch':'switches','telemetry_reset':'resets'}.get(e.kind)
                        if name:_write_json(handles[name],{'label':LABEL,'sequence':e.sequence,'record':asdict(e.record)})
                    for d in step.decisions:_write_json(handles['decisions'],asdict(d))
                    for o in step.outcomes:_write_json(handles['outcomes'],asdict(o))
            replay_seconds=time.perf_counter()-begin
            metric_rows.extend(comparisons(inputs,replay));av,sup=availability(inputs,replay,steps);availability_rows.extend(av);supports.extend(sup)
            write_new(directory/'summary.json',{'label':LABEL,'availability':av,'support':sup,'pending_decision_ids':replay.pending_ids})
            private_plots(directory/'private_figures',inputs,replay,steps)
            from .audit_m5b2_v1 import verify_machine
            audits[machine]=verify_machine(directory,inputs)
            for independent in audits[machine]['recomputed_comparisons']:
                row=next(r for r in metric_rows if (r['machine'],r['horizon'],r['scope'],r['policy'])==(
                    machine,independent['horizon'],independent['scope'],independent['policy']))
                if row['count']!=independent['count'] or any(
                    (row[key] is None)!=(independent[key] is None) or row[key] is not None and not math.isclose(row[key],independent[key],abs_tol=1e-12)
                    for key in ('mae','rmse')):raise ValueError('Independent comparison audit failed')
            runtimes.append({'machine':machine,'replay_with_ledger_io_seconds':replay_seconds,'peak_process_rss_bytes':rss_bytes()})
        macro=macro_metrics(metric_rows)
        write_new(report/'comparisons.json',metric_rows);write_csv(report/'comparisons.csv',metric_rows)
        write_new(report/'macro_comparisons.json',macro);write_csv(report/'macro_comparisons.csv',macro)
        write_csv(report/'availability.csv',availability_rows);write_new(report/'support_switching.json',supports)
        write_new(report/'ledger_verification.json',audits)
        aggregate_plots(report,macro)
        write_new(report/'runtime.json',{'label':LABEL,'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
            'rss_budget_bytes':4*1024**3,'machines':runtimes,'models_loaded':0,'model_fits':0})
        write_new(report/'preservation_verification.json',{'label':LABEL,'historical_hashes_verified':verify_history(),'passed':True,
            'confirmation_execution_allowed':False,'new_observations_accessed':False})
        completion={'status':'completed','label':LABEL,'machines':list(MACHINES),'new_model_fits':0,'confirmation_execution_allowed':False}
    except BaseException as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:write_new(output/'completion.json',completion)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    print(run(p.parse_args().run_id))
