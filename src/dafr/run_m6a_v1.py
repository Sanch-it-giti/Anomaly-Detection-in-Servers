"""Source-gated synthetic-only M6A experiments and event-ledger verification."""
from dataclasses import asdict
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,resource,sys,time

from .contracts import identifier
from .drift_contracts_v1 import LABEL
from .drift_v1 import ROOT,load_drift_config
from .drift_fixtures_v1 import FIXTURES,START,fixture_events
from .drift_streaming_v1 import SyntheticDriftStreamV1
from .streaming_v2 import _write_json

SOURCES=('configs/dafr_m6a_synthetic_v1.json','src/dafr/drift_contracts_v1.py','src/dafr/drift_v1.py',
    'src/dafr/drift_streaming_v1.py','src/dafr/drift_fixtures_v1.py','src/dafr/run_m6a_v1.py',
    'tests/test_dafr_drift_v1.py','reports/dafr/m6a_drift_detection_design_v1.md')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def write_new(path,value):
    with Path(path).open('x') as out:_write_json(out,value)


def verify_history():
    inventory=json.loads((ROOT/'reports/dafr/m6a_preservation_v1.json').read_text())
    for name,expected in inventory['protected_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Historical artifact changed: '+name)
    return inventory['file_count']


def rss_bytes():
    n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform=='darwin' else n*1024)


def run_case(directory,spec):
    if spec not in FIXTURES:raise ValueError('Predefined synthetic fixtures only')
    directory=Path(directory)
    if directory.resolve()!=directory:raise ValueError('Output redirection')
    directory.mkdir(parents=True,exist_ok=False);completion={'status':'failed','label':LABEL};start=time.perf_counter()
    try:
        sim=SyntheticDriftStreamV1(directory.name,spec.failure_origins);alerts=[];counts=Counter()
        write_new(directory/'manifest.json',{'label':LABEL,'scope':'SYNTHETIC_ONLY','fixture':asdict(spec),
            'config_sha256':sim.execution_sha256,'reference_expert':'persistence','reference_version':'rule_v2',
            'confirmation_execution_allowed':False,'selector_changes':False,'model_fits':0})
        from contextlib import ExitStack
        with ExitStack() as stack:
            files={name:stack.enter_context((directory/(name+'.jsonl')).open('x')) for name in
                ('events','forecasts','outcomes','detector_updates','alerts','telemetry_resets')}
            for row in fixture_events(spec):
                if rss_bytes()>4*1024**3:raise MemoryError('4 GiB process RSS budget exceeded')
                step=sim.advance(*row)
                for e in step.events:
                    _write_json(files['events'],{'label':LABEL,'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)})
                    stream='alerts' if e.kind in ('statistical_alarm','warning_entered') else 'telemetry_resets' if e.kind=='telemetry_reset' else 'detector_updates' if e.kind in ('detector_clock','detector_update') else None
                    if stream:_write_json(files[stream],{'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)})
                    counts[e.kind]+=1
                    if e.kind=='detector_update' and e.record.clipped:counts[f'clipped_h{e.record.horizon}']+=1
                for f in step.decisions:_write_json(files['forecasts'],asdict(f))
                for o in step.outcomes:_write_json(files['outcomes'],asdict(o))
                alerts.extend(step.alerts)
        rows=[]
        for h in (1,12):
            alarms=[a for a in alerts if a.horizon==h and a.kind=='statistical_alarm']
            indices=[int((a.available_at-START).total_seconds()/300) for a in alarms]
            post=[i for i in indices if spec.change_start is not None and i>=spec.change_start]
            false=sum(spec.change_start is None or i<spec.change_start for i in indices)
            first=post[0] if post else None
            detector=sim.detectors[h]
            rows.append({'label':LABEL,'fixture':spec.name,'horizon':h,'grid_ticks':spec.length,
                'change_kind':spec.change_kind,'known_fixture_change_tick':spec.change_start,
                'alarm_count':len(alarms),'warning_entries':sum(a.horizon==h and a.kind=='warning_entered' for a in alerts),
                'false_or_prechange_alarms':false,'postchange_alarms':len(post),'first_postchange_alarm_tick':first,
                'first_detection_delay_ticks':first-spec.change_start if first is not None else None,
                'first_detection_delay_minutes':5*(first-spec.change_start) if first is not None else None,
                'fixture_change_not_alarmed':spec.change_start is not None and first is None,
                'alarm_ticks':indices,'accepted_genuine_errors':detector.lifetime_errors,'ignored_old_era_errors':detector.ignored_old_errors,
                'final_recent_support':len(detector.recent),'final_normalization_count':len(detector._normalization),
                'final_era_monitor_clips':detector.clips,'telemetry_resets':counts['telemetry_reset']})
            rows[-1]['clipped_monitor_inputs_all_eras']=counts[f'clipped_h{h}']
        ds=sim.ledger.decisions;os=sim.ledger.outcomes
        summary={'label':LABEL,'fixture':spec.name,'rows':rows,'source_grid_ticks':sim._ticks,'source_genuine_ticks':sim._genuine,
            'decisions':len(ds),'scored':sum(o.status=='scored' for o in os),'missing_targets':sum(o.status=='target_unavailable' for o in os),
            'pending':len(sim.ledger.pending_ids),'abstentions':sum(not f.issued for f in ds),
            'declared_forecast_failures':counts['reference_failure'],'telemetry_resets':counts['telemetry_reset'],
            'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
            'model_refits':0,'adaptive_switches':0,'real_data_used':False}
        write_new(directory/'summary.json',summary);completion={'label':LABEL,'status':'completed','grid_ticks':sim._ticks}
    except BaseException as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:write_new(directory/'completion.json',completion)
    return summary


def verify_case(directory,spec):
    """Independently check alert support, causality, cooldown and exact sources."""
    def rows(name):
        with (directory/(name+'.jsonl')).open() as source:return [json.loads(line) for line in source]
    events=rows('events');forecasts=rows('forecasts');outcomes=rows('outcomes')
    ids={f['forecast_id']:f for f in forecasts};os={o['event_id']:o for o in outcomes}
    def require(condition):
        if not condition:raise ValueError('Synthetic drift ledger audit failed')
    require(len(ids)==len(forecasts) and len(os)==len(outcomes))
    sequence=[e['sequence'] for e in events];require(sequence==sorted(set(sequence)))
    require(forecasts==[e['record'] for e in events if e['kind'] in ('reference_forecast','reference_abstention')])
    require(outcomes==[e['record'] for e in events if e['kind'] in ('scored','target_unavailable')])
    for name,kinds in (('alerts',('statistical_alarm','warning_entered')),('detector_updates',('detector_clock','detector_update')),('telemetry_resets',('telemetry_reset',))):
        require(rows(name)==[{'sequence':e['sequence'],'kind':e['kind'],'record':e['record']} for e in events if e['kind'] in kinds])
    ticks={e['record']['timestamp']:e for e in events if e['kind']=='tick'}
    fixture=list(fixture_events(spec));require(len(ticks)==len(fixture))
    for t,v,r in fixture:require((ticks[t.isoformat()]['record']['value'],ticks[t.isoformat()]['record']['missing_reason'])==(v,r))
    for o in outcomes:
        f=ids[o['forecast_id']];arrival=ticks[o['target']]
        require(f['origin']==o['origin'] and f['horizon']==o['horizon'] and f['predicted_value']==o['predicted_value'])
        require(f['sequence']<arrival['sequence']<o['sequence'])
        require(o['actual']==arrival['record']['value'])
        if o['status']=='target_unavailable':require(all(o[k] is None for k in ('actual','signed_error','absolute_error','squared_error','interval_hit')))
        else:require(o['absolute_error']==abs(o['actual']-f['predicted_value']))
    last_alarm={};alerts=0
    for e in events:
        r=e['record']
        if e['kind']=='genuine_reference_error':
            require(r['outcome']['status']=='scored' and r['outcome']['target'] in ticks)
            require(r['outcome']==os[r['outcome']['event_id']])
        if e['kind'] not in ('statistical_alarm','warning_entered'):continue
        alerts+=1;o=os[r['source_outcome_id']];f=ids[r['source_forecast_id']]
        require(o['forecast_id']==f['forecast_id'] and r['available_at']==o['target'] and o['status']=='scored' and o['sequence']<e['sequence'])
        require(r['genuine_support']>=64 and r['statistic']>=r['threshold'] and r['telemetry_era']==f['era'])
        require(r['source_expert']=='persistence' and r['source_version']=='rule_v2' and not r['cooldown_active_before'])
        key=(r['horizon'],r['telemetry_era']);now=r['available_at']
        from datetime import datetime,timedelta
        if key in last_alarm:require(datetime.fromisoformat(now)>=last_alarm[key]+timedelta(minutes=120))
        if e['kind']=='statistical_alarm':last_alarm[key]=datetime.fromisoformat(now)
    summary=json.loads((directory/'summary.json').read_text())
    require(summary['decisions']==summary['scored']+summary['missing_targets']+summary['pending']+summary['abstentions'])
    return {'label':LABEL,'passed':True,'fixture':spec.name,'source_outcomes':len(outcomes),'alerts_and_warnings_verified':alerts,
        'missing_values_never_used_as_errors':True,'adaptive_switches':0}


def demonstrate(run_id):
    identifier(run_id);load_drift_config();verify_history()
    gate=json.loads((ROOT/'reports/dafr/m6a_synthetic_gate_v1.json').read_text())
    if gate.get('passed') is not True or any(gate['source_sha256'].get(p)!=sha(ROOT/p) for p in SOURCES):raise ValueError('Current successful source/test gate required')
    output=ROOT/'data/processed/dafr/m6a_synthetic_v1'/run_id;report=ROOT/'reports/dafr/m6a_v1'/run_id
    for p in (output,report):
        if p.resolve()!=p:raise ValueError('Output redirection')
        if p.exists():raise FileExistsError('Run ID already exists')
    output.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    results={};audits={};rows=[]
    for spec in FIXTURES:
        directory=output/spec.name;results[spec.name]=run_case(directory,spec)
        audits[spec.name]=verify_case(directory,spec);rows.extend(results[spec.name]['rows'])
    write_new(report/'synthetic_summary.json',results);write_new(report/'ledger_verification.json',audits)
    with (report/'detection_summary.csv').open('x',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write_new(report/'preservation_verification.json',{'label':LABEL,'passed':True,'historical_hashes_verified':verify_history(),'confirmation_execution_allowed':False})
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    print(demonstrate(p.parse_args().run_id))
