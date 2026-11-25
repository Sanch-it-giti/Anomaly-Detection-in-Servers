"""Forward development benchmark: frozen checkpoints, strictly scoped data.

No fitting, reselection, confirmation access, calibration or adaptive policy.
"""
from contextlib import contextmanager,ExitStack
from dataclasses import asdict
from datetime import timedelta
import argparse,csv,hashlib,io,json,math,os,resource,sys,threading,time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .contracts import identifier
from .development_qualification_v1 import EPOCH,PRIMARY_IDS,validate_prefix_csv
from .real_adapters_v1 import digest_bytes
from .forward_streaming_v1 import ForwardSimulator
from .scoped_development_reader_v1 import extract_development_segment
from .streaming_v2 import _write_json

ROOT=Path(__file__).resolve().parents[2]
NEW_SOURCES=('src/dafr/scoped_development_reader_v1.py','src/dafr/forward_streaming_v1.py',
    'src/dafr/run_m4a_v1.py','tests/test_dafr_forward_v1.py','configs/dafr_m4a_execution_v1.json')


def write_new(path,value):
    with Path(path).open('x') as out:_write_json(out,value)


def peak_rss():
    n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform=='darwin' else n*1024)


def enforce_memory():
    if peak_rss()>4*1024**3:raise MemoryError('4 GiB process RSS budget exceeded')


def verify_history(root=ROOT):
    receipt=json.loads((Path(root)/'reports/dafr/m4a_preservation_v1.json').read_text())
    for path,sha in receipt['protected_sha256'].items():
        if digest_bytes((Path(root)/path).read_bytes())!=sha:raise ValueError('Historical artifact changed: '+path)


def load_config(root=ROOT):
    root=Path(root).resolve();payload=(root/'configs/dafr_m4a_execution_v1.json').read_bytes();c=json.loads(payload)
    if c.get('schema_version')!='dafr_m4a_execution_v1' or c.get('scope')!='FORWARD_FIXED_MODEL_DEVELOPMENT_ONLY':
        raise ValueError('Wrong forward execution scope')
    if c.get('m4a_execution_allowed') is not True or any(c.get(k) is not False for k in
            ('m3_training_allowed','training_authorized','refitting_allowed','confirmation_execution_allowed')):
        raise ValueError('No training or confirmation authorization is valid in M4A')
    if c['allowed_machine_ids']!=list(PRIMARY_IDS) or c['new_observations']!=[1152,1612] or c['historical_state_reconstruction']!=[0,1152] or c['horizons']!=[1,12]:
        raise ValueError('Forward boundaries changed')
    if (c['gate_genuine_bins'],c['persistence_max_age_ticks'],c['era_reset_missing_tick'],c['maximum_process_rss_bytes'])!=(24,3,4,4*1024**3):
        raise ValueError('Frozen gate or resource policy changed')
    if c['temporal_loss']!={'rolling_grid_ticks':48,'min_common_genuine_scores':12,'fixed_thirds':[[1152,1305],[1305,1458],[1458,1612]],'use':'Exploratory descriptive analysis only; no selector tuning or drift validation'}:
        raise ValueError('Descriptive windows must be prespecified')
    s=c['selection_receipt'];path=root/s['path']
    if digest_bytes(path.read_bytes())!=s['sha256']:raise ValueError('Selection receipt changed')
    selected=json.loads(path.read_text())
    if selected['selection_cutoff_index']!=1151 or {f:d['winner_candidate_index'] for f,d in selected['families'].items()}!={'arima':2,'xgboost':0}:
        raise ValueError('Selected models changed')
    return c,digest_bytes(payload)


def historical_prefix(machine,config,root=ROOT):
    if machine not in PRIMARY_IDS:raise ValueError('Historical source not admitted')
    spec=config['sources'][machine]['historical_prefix'];path=Path(root)/spec['path']
    if path.resolve()!=path:raise ValueError('Historical path redirection')
    payload=path.read_bytes()
    if digest_bytes(payload)!=spec['sha256']:raise ValueError('Historical source hash changed')
    mask=validate_prefix_csv(payload)
    return tuple(float(row['value']) if good else None for row,good in zip(csv.DictReader(io.StringIO(payload.decode())),mask))


@contextmanager
def prohibit_fitting():
    audit={'fit_call_attempts':0}
    def forbidden(*args,**kwargs):
        audit['fit_call_attempts']+=1
        raise AssertionError('Parameter fitting is prohibited in M4A')
    with patch.object(SARIMAX,'fit',forbidden),patch.object(xgb.XGBRegressor,'fit',forbidden),patch.object(xgb.Booster,'update',forbidden),patch.object(xgb,'train',forbidden):
        yield audit
    if audit['fit_call_attempts']:raise AssertionError('Fitting attempted')


def metrics(items):
    if not items:return {'count':0,'mae':None,'rmse':None}
    return {'count':len(items),'mae':sum(o.absolute_error for o in items)/len(items),
        'rmse':math.sqrt(sum(o.squared_error for o in items)/len(items))}


def global_index(timestamp):return int((timestamp-EPOCH).total_seconds()/300)-1


def collect_metrics(simulator,machine):
    forecasts={f.forecast_id:f for f in simulator.ledger.decisions}
    scores=[o for o in simulator.ledger.outcomes if o.status=='scored']
    sets={}
    for h in (1,12):
        for policy in ('persistence','arima','xgboost'):
            sets[(policy,h)]={(o.origin,o.target):o for o in scores if o.policy_id==policy and o.horizon==h
                and (policy=='persistence' or forecasts[o.forecast_id].availability=='expert')}
    rows=[];common_keys={};common_scores={}
    for h in (1,12):
        keys=set.intersection(*(set(sets[(p,h)]) for p in ('persistence','arima','xgboost')))
        common_keys[h]=keys
        for policy in ('persistence','arima','xgboost'):
            matched=[sets[(policy,h)][k] for k in sorted(keys)]
            common_scores[(policy,h)]=matched
            decisions=[f for f in forecasts.values() if f.policy_id==policy and f.horizon==h]
            complete=[o for o in scores if o.policy_id==policy and o.horizon==h]
            pending=set(simulator.ledger.pending_ids)
            rows.append({'machine':machine,'policy':policy,'horizon':h,'expert_matched':metrics(matched),
                'complete_policy':metrics(complete),'genuine_own_expert_targets':len(sets[(policy,h)]),
                'decisions':len(decisions),'expert_issuance':sum(f.availability=='expert' for f in decisions),
                'baseline_issuance':sum(f.availability=='baseline' for f in decisions),
                'fallbacks':sum(f.availability=='fallback' for f in decisions),'abstentions':sum(not f.issued for f in decisions),
                'stale_fallback_abstentions':sum(f.reason=='fallback_stale' for f in decisions),
                'missing_targets':sum(o.policy_id==policy and o.horizon==h and o.status=='target_unavailable' for o in simulator.ledger.outcomes),
                'pending':sum(f.forecast_id in pending for f in decisions)})
    return rows,common_scores


def macro_rows(rows,key='expert_matched'):
    result=[]
    for h in (1,12):
        for policy in ('persistence','arima','xgboost'):
            group=[r for r in rows if r['policy']==policy and r['horizon']==h]
            supported=len(group)==3 and all(r[key]['count']>0 for r in group)
            result.append({'policy':policy,'horizon':h,'metric_scope':key,'machine_count':len(group),
                'count':sum(r[key]['count'] for r in group),'mae':sum(r[key]['mae'] for r in group)/3 if supported else None,
                'rmse':sum(r[key]['rmse'] for r in group)/3 if supported else None,
                'equal_machine_support_complete':supported})
    return result


def missingness(values):
    gaps=[];length=0
    for v in values:
        if v is None:length+=1
        elif length:gaps.append(length);length=0
    if length:gaps.append(length)
    return {'grid_bins':len(values),'genuine_bins':sum(v is not None for v in values),
        'missing_bins':sum(v is None for v in values),'coverage':sum(v is not None for v in values)/len(values),
        'missing_runs':len(gaps),'longest_missing_run_bins':max(gaps,default=0),
        'gap_length_histogram':{str(n):gaps.count(n) for n in sorted(set(gaps))},
        'gaps_touching_boundaries_included':True}


def temporal_summary(machine,common,config):
    rows=[]
    for start,end in config['temporal_loss']['fixed_thirds']:
        for h in (1,12):
            for policy in ('persistence','arima','xgboost'):
                items=[o for o in common[(policy,h)] if start<=global_index(o.target)<end]
                rows.append({'machine':machine,'start_index':start,'end_index':end,'horizon':h,'policy':policy,**metrics(items)})
    return rows


def create_plots(directory,machine,values,simulator,common,config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory.mkdir(exist_ok=False)
    x=np.arange(1152,1612);actual=np.array([np.nan if v is None else v for v in values])
    colors={'persistence':'#777777','arima':'#3973ac','xgboost':'#32917a'}
    for h in (1,12):
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True)
        axes[0].plot(x,actual,label='Genuine CPU',color='black',linewidth=1)
        for policy in colors:
            line=np.full(460,np.nan)
            for f in simulator.ledger.forecasts:
                j=global_index(f.target)
                if f.policy_id==policy and f.horizon==h and 1152<=j<1612:line[j-1152]=f.predicted_value
            axes[0].plot(x,line,label=policy+(' + fallback' if policy!='persistence' else ''),color=colors[policy],alpha=.8,linewidth=.8)
            error=np.full(460,np.nan)
            for o in common[(policy,h)]:error[global_index(o.target)-1152]=o.absolute_error
            axes[1].plot(x,error,label=policy,color=colors[policy],linewidth=.8)
        axes[0].set_ylabel('CPU utilization (%)');axes[0].legend(ncol=2)
        axes[1].set_ylabel('Expert-matched absolute error');axes[1].set_xlabel('Original five-minute grid index')
        axes[0].set_title(f'M4A FORWARD DEVELOPMENT — {machine}, h={h}; missing positions retained')
        fig.tight_layout();fig.savefig(directory/f'forecast_errors_{machine}_h{h}.png',dpi=150);plt.close(fig)
        fig,ax=plt.subplots(figsize=(11,4.5))
        for policy in colors:
            errors={global_index(o.target):o.absolute_error for o in common[(policy,h)]};line=[]
            for i in x:
                recent=[errors[j] for j in range(max(1152,i-47),i+1) if j in errors]
                line.append(sum(recent)/len(recent) if len(recent)>=12 else np.nan)
            ax.plot(x,line,label=policy,color=colors[policy])
        ax.set_title(f'Exploratory past-only 48-grid-tick MAE — {machine}, h={h}')
        ax.set_xlabel('Exact target index (five-minute grid)');ax.set_ylabel('Matched MAE (CPU percentage points)')
        ax.legend();fig.tight_layout();fig.savefig(directory/f'temporal_loss_{machine}_h{h}.png',dpi=150);plt.close(fig)


def write_csv(path,rows):
    with path.open('x',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def benchmark(run_id,gate_receipt,root=ROOT):
    identifier(run_id);root=Path(root).resolve();config,config_sha=load_config(root);verify_history(root)
    gate=json.loads(Path(gate_receipt).read_text())
    if gate.get('passed') is not True:raise ValueError('Successful engineering gate required')
    for source in NEW_SOURCES:
        if gate['source_sha256'].get(source)!=digest_bytes((root/source).read_bytes()):raise ValueError('Stale engineering gate')
    base=root/'data/processed/dafr/m4a_development_v1';reports_base=root/'reports/dafr/m4a_v1'
    for parent in (base,reports_base):
        if parent.resolve()!=parent:raise ValueError('Output symlink redirection')
        parent.mkdir(parents=True,exist_ok=True)
    output=base/run_id;report=reports_base/run_id
    if output.exists() or report.exists():raise FileExistsError('Forward run ID already reserved')
    output.mkdir(exist_ok=False);report.mkdir(exist_ok=False)
    write_new(output/'execution_manifest.json',{'config':config,'config_sha256':config_sha,'gate':gate,
        'run_id':run_id,'confirmation_execution_allowed':False,'parameters_refitted':False})
    start=time.perf_counter();stop=threading.Event();completion={'status':'failed'}
    def watchdog():
        while not stop.wait(.05):
            if peak_rss()>4*1024**3:
                write_new(output/'resource_stop.json',{'rss':peak_rss(),'reason':'RSS exceeded 4 GiB'});os._exit(70)
    thread=threading.Thread(target=watchdog,daemon=True);thread.start()
    all_rows=[];all_temporal=[];runtime=[];qualities={};extractions={};state_checks={}
    try:
        with prohibit_fitting() as no_fit:
            for machine in PRIMARY_IDS:
                machine_dir=output/machine;machine_dir.mkdir(exist_ok=False)
                prefix=historical_prefix(machine,config,root)
                reconstruction_start=time.perf_counter()
                sim=ForwardSimulator(run_id+'-'+machine,machine,config,prefix,config_sha,root)
                reconstruct_seconds=time.perf_counter()-reconstruction_start
                # Integrity and full historical state reconstruction precede
                # reading any newly authorized CPU values for this machine.
                state_checks[machine]=sim.reconstructed_hashes
                with (machine_dir/'reconstruction.jsonl').open('x') as out:
                    for kind,event in sim.reconstruction_events:_write_json(out,{'kind':kind,'record':asdict(event)})
                write_new(machine_dir/'bootstrap.json',{'selection_cutoff_index':1151,'reconstruction_indices':[864,1152],
                    'reconstruction_seconds':reconstruct_seconds,'state_hashes_match_m3b2':True,
                    'state_sha256':sim.reconstructed_hashes,'initial_era':sim.reconstruction_era,'past_forecasts_issued':0,
                    'pending_m3b2_forecasts_imported':0,'error_buffers_seeded_with_past_scores':False})
                values,reasons,receipt=extract_development_segment(root,machine,config,machine_dir/'scoped_input')
                extractions[machine]=receipt;qualities[machine]=missingness(values)
                tick_with_io=[];failure_counts={'numerical_updates':0,'numerical_forecasts':0,'stale_state_responses':0,'era_resets':0}
                replay_start=time.perf_counter()
                with ExitStack() as stack:
                    events=stack.enter_context((machine_dir/'events.jsonl').open('x'))
                    policy_logs={}
                    for policy in ('persistence','arima','xgboost'):
                        p=machine_dir/policy;p.mkdir(exist_ok=False)
                        policy_logs[policy]=(stack.enter_context((p/'predictions.jsonl').open('x')),stack.enter_context((p/'outcomes.jsonl').open('x')))
                    for k,value in enumerate(values):
                        tick_start=time.perf_counter();i=1152+k
                        step=sim.advance(EPOCH+timedelta(seconds=300*(i+1)),value,'quality_failed' if value is None else None)
                        failure_counts['era_resets']+=step.reset is not None
                        for event in step.updates:
                            failure_counts['numerical_updates']+=event.status=='numerical_failure'
                            failure_counts['stale_state_responses']+=event.result.model_state_cutoff<step.tick.timestamp
                        for event in step.attempts:failure_counts['numerical_forecasts']+=event.status=='numerical_failure'
                        for kind,event in step.ordered():_write_json(events,{'kind':kind,'record':asdict(event)})
                        for f in step.decisions:_write_json(policy_logs[f.policy_id][0],sim.envelopes[f.forecast_id].payload())
                        for o in step.outcomes:_write_json(policy_logs[o.policy_id][1],asdict(o))
                        enforce_memory();tick_with_io.append(time.perf_counter()-tick_start)
                rows,common=collect_metrics(sim,machine);all_rows.extend(rows)
                all_temporal.extend(temporal_summary(machine,common,config))
                timing={'machine':machine,'reconstruction_seconds':reconstruct_seconds,'replay_seconds':time.perf_counter()-replay_start,
                    'peak_process_rss_bytes':peak_rss(),'tick_p95_without_io_seconds':float(np.quantile(sim.tick_seconds,.95)),
                    'tick_p95_with_serialization_buffered_writes_seconds':float(np.quantile(tick_with_io,.95)),
                    'policy_issue_p95_seconds':{f'{p}_h{h}':float(np.quantile(v,.95)) for (p,h),v in sim.policy_seconds.items()},
                    'adapter_resources':sim.resource_reports(),'failures':failure_counts}
                runtime.append(timing)
                write_new(machine_dir/'summary.json',{'rows':rows,'quality':qualities[machine],'runtime':timing,'pending_ids':sim.ledger.pending_ids})
                create_plots(machine_dir/'private_figures',machine,values,sim,common,config)
                enforce_memory()
            no_fit_result=dict(no_fit)
        macro=macro_rows(all_rows);complete_macro=macro_rows(all_rows,'complete_policy')
        write_new(report/'forward_metrics.json',all_rows);write_new(report/'macro_metrics.json',macro+complete_macro)
        write_new(report/'temporal_descriptive.json',all_temporal);write_new(report/'missingness.json',qualities)
        write_new(report/'runtime.json',{'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':peak_rss(),
            'rss_limit_bytes':4*1024**3,'serial_threads':1,'machines':runtime,'no_fit_guard':no_fit_result})
        write_new(report/'scope_audit.json',{'extractions':extractions,'reconstructed_state_matches':state_checks,
            'source_read_ahead':False,'forbidden_blocks_opened':False,'confirmation_access':False,
            'no_fit_guard':no_fit_result,'selection_performed':False,'new_execution_config_sha256':config_sha})
        flat=[]
        for r in all_rows:
            row={k:v for k,v in r.items() if not isinstance(v,dict)}
            for key,val in r.items():
                if isinstance(val,dict):row.update({f'{key}_{k}':v for k,v in val.items()})
            flat.append(row)
        write_csv(report/'forward_metrics.csv',flat);write_csv(report/'macro_metrics.csv',macro+complete_macro)
        write_csv(report/'temporal_descriptive.csv',all_temporal)
        verify_history(root)
        completion={'status':'completed','new_global_indices':[1152,1612],'new_rows_per_machine':460,
            'models_refitted':False,'selection_performed':False,'confirmation_execution_allowed':False,
            'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':peak_rss()}
    except BaseException as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:
        stop.set();thread.join(timeout=1);write_new(output/'completion.json',completion)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);parser.add_argument('--gate-receipt',required=True)
    args=parser.parse_args();print(benchmark(args.run_id,args.gate_receipt))
