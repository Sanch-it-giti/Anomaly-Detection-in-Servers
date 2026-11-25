"""Exclusive synthetic real-backend integration execution and saved-ledger audit."""
from collections import Counter
from contextlib import ExitStack
import copy
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import time

from .adaptive_real_fixtures_v1 import (build_fixture_checkpoints, fixture_events,
    declared_failure, forbid_replay_fitting, write_new)
from .adaptive_checkpoint_registry_v1 import verify_historical_checkpoints
from .drift_real_streaming_v1 import RealBackendDriftStreamV1, load_m6b_config
from .drift_contracts_v1 import GenuineReferenceErrorV1
from .contracts_v2 import ForecastRecordV2, TargetOutcomeV2
from .drift_v1 import ROOT, PageHinkleyErrorV1, load_drift_config
from .run_m6a_v1 import sha, rss_bytes
from .development_qualification_v1 import EPOCH
from .streaming_v2 import _write_json, _json_default
from .contracts import identifier

SOURCES=('configs/dafr_m6b_synthetic_backend_v1.json','src/dafr/drift_real_streaming_v1.py',
    'src/dafr/run_m6b_v1.py','tests/test_dafr_drift_real_v1.py','reports/dafr/m6b_integration_design_v1.md')


def verify_preservation():
    p=json.loads((ROOT/'reports/dafr/m6b_preservation_v1.json').read_text())
    for name,expected in p['protected_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Protected artifact changed: '+name)
    verify_historical_checkpoints()
    return p['file_count']


def synthetic_events(name):
    if name=='sustained':
        value=20.
        for i in range(280):
            if i:value+=.1 if i<160 else .5
            yield EPOCH+timedelta(minutes=5*(97+i)),value,None
    elif name in ('gaps_failures','update_failure'):yield from fixture_events(name)
    else:raise ValueError('Declared synthetic scenarios only')


def run_case(directory,reference,scenario):
    directory=Path(directory);directory.mkdir(exist_ok=False)
    config,_=load_m6b_config()
    if scenario not in config['scenarios']:raise ValueError('Undeclared scenario')
    started=time.perf_counter();counts=Counter();parity=True
    with forbid_replay_fitting() as fitting:
        enabled=RealBackendDriftStreamV1(scenario,reference)
        disabled=copy.deepcopy(enabled);disabled.monitoring_enabled=False
        with ExitStack() as stack:
            files={n:stack.enter_context((directory/(n+'.jsonl')).open('x')) for n in
                ('backend_events','forecasts','outcomes','monitor_events','disabled_forecasts')}
            for i,row in enumerate(synthetic_events(scenario)):
                if rss_bytes()>config['maximum_process_rss_bytes']:raise MemoryError('4 GiB RSS limit')
                with declared_failure(enabled.backend,scenario,i):a=enabled.advance(*row)
                with declared_failure(disabled.backend,scenario,i):b=disabled.advance(*row)
                if a.backend!=b.backend:raise ValueError('Monitoring altered backend output/state provenance')
                for e in a.backend.events:
                    _write_json(files['backend_events'],asdict(e));counts['backend_'+e.kind]+=1
                for f in a.backend.decisions:_write_json(files['forecasts'],asdict(f))
                for f in b.backend.decisions:_write_json(files['disabled_forecasts'],asdict(f))
                for o in a.backend.outcomes:_write_json(files['outcomes'],asdict(o))
                for e in a.monitor_events:
                    _write_json(files['monitor_events'],asdict(e));counts[e.kind]+=1
        for name,a in enabled.backend._adapters.items():
            if a.parameter_sha256!=enabled.backend._parameters[name]:raise ValueError('Model parameters changed')
    summary={'label':'SYNTHETIC REAL-BACKEND ENGINEERING VERIFICATION ONLY','scenario':scenario,
        'monitoring_enabled_disabled_backend_parity':parity,'counts':dict(counts),
        'elapsed_seconds':time.perf_counter()-started,'peak_process_rss_bytes':rss_bytes(),
        'replay_fit_attempts':fitting['fit_attempts'],'confirmation_execution_allowed':False,
        'pending':len(enabled.backend.ledger.pending_ids),
        'detectors':{h:asdict(d.snapshot()) for h,d in enabled.detectors.items()}}
    write_new(directory/'summary.json',summary)
    write_new(directory/'hashes.json',{p.name:sha(p) for p in directory.iterdir() if p.is_file()})
    return summary


def decoded(cls,data):
    data=dict(data)
    for key in ('origin','target','last_genuine_cutoff','support_latest_target','training_cutoff',
                'scaling_cutoff','version_available_at'):
        if data.get(key) is not None:data[key]=datetime.fromisoformat(data[key])
    return cls(**data)


def audit_case(directory):
    """Independently replay detector receipts from saved original reference links."""
    directory=Path(directory)
    pins=json.loads((directory/'hashes.json').read_text())
    for name,expected in pins.items():
        if sha(directory/name)!=expected:raise ValueError('Saved ledger changed: '+name)
    read=lambda name:[json.loads(s) for s in (directory/(name+'.jsonl')).read_text().splitlines()]
    forecasts=read('forecasts');disabled=read('disabled_forecasts');outcomes=read('outcomes')
    if forecasts!=disabled:raise ValueError('Forecast parity mismatch')
    fs={f['forecast_id']:f for f in forecasts};os={o['event_id']:o for o in outcomes}
    if len(fs)!=len(forecasts) or len(os)!=len(outcomes):raise ValueError('Duplicate ledger identifiers')
    for o in outcomes:
        f=fs[o['forecast_id']]
        for k in ('target','origin','horizon','predicted_value','policy_id','policy_version'):
            if f[k]!=o[k]:raise ValueError('Exact-target linkage mismatch')
        if o['status']=='scored':
            if abs(o['actual']-o['predicted_value'])!=o['absolute_error']:raise ValueError('Invented error')
        elif o['absolute_error'] is not None:raise ValueError('Missing target error')
    config,sha256=load_drift_config();ds={h:PageHinkleyErrorV1(h,sha256,config) for h in (1,12)}
    backend=read('backend_events');barriers={}
    for event in backend:
        r=event['record']
        if event['kind']=='tick':now=r['timestamp']
        barriers[now]=max(barriers.get(now,0),event['sequence'])
    _,m6b_sha=load_m6b_config()
    expected_update=None;expected_alerts=[];last_sequence=0;links=0;linked_ids=set()
    for e in read('monitor_events'):
        if e['sequence']!=last_sequence+1:raise ValueError('Monitor sequence violation')
        if e['m6b_configuration_sha256']!=m6b_sha:raise ValueError('Monitor configuration mismatch')
        last_sequence=e['sequence'];r=e['record'];kind=e['kind']
        timestamp=r['sample']['outcome']['target'] if kind=='reference_error_link' else r['available_at']
        if e['backend_barrier_sequence']!=barriers[timestamp]:raise ValueError('Monitor before issuance barrier')
        if kind=='detector_clock':
            snapshot=ds[r['horizon']].clock(datetime.fromisoformat(timestamp),r['telemetry_era'])
            if json.loads(json.dumps(asdict(snapshot),default=_json_default))!=r:raise ValueError('Clock replay mismatch')
        elif kind=='reference_error_link':
            f,o=r['original_forecast'],r['original_outcome']
            if o['event_id'] in linked_ids:raise ValueError('Duplicate reference error')
            linked_ids.add(o['event_id'])
            if f!=fs[f['forecast_id']] or o!=os[o['event_id']]:raise ValueError('Original reference changed')
            if (f['policy_id'],f['availability'],f['source_expert'],f['source_version'])!=('persistence','baseline','persistence','rule_v2'):
                raise ValueError('Non-reference error')
            view=r['sample']['forecast'];out=r['sample']['outcome']
            for k in ('forecast_id','origin','target','horizon','era','predicted_value','context_sha256','sequence'):
                if view[k]!=f[k]:raise ValueError('Projection changed source')
            for k,v in o.items():
                if k!='policy_version' and out[k]!=v:raise ValueError('Projection changed outcome')
            sample=GenuineReferenceErrorV1(decoded(ForecastRecordV2,view),decoded(TargetOutcomeV2,out))
            update=ds[o['horizon']].observe(sample);expected_update=asdict(update.snapshot)
            expected_alerts.extend(asdict(a) for a in update.alerts);links+=1
        elif kind=='detector_update':
            if json.loads(json.dumps(expected_update,default=_json_default))!=r:raise ValueError('Detector replay mismatch')
            expected_update=None
        elif kind in ('warning_entered','statistical_alarm'):
            if not expected_alerts or json.loads(json.dumps(expected_alerts.pop(0),default=_json_default))!=r:raise ValueError('Alert replay mismatch')
        elif kind=='detector_telemetry_reset':
            if json.loads(json.dumps(asdict(ds[r['horizon']].snapshot()),default=_json_default))!=r:
                raise ValueError('Reset replay mismatch')
        else:raise ValueError('Unknown monitoring event')
    if expected_update is not None or expected_alerts:raise ValueError('Unrecorded detector response')
    eligible={o['event_id'] for o in outcomes if o['policy_id']=='persistence' and o['status']=='scored'}
    if linked_ids!=eligible:raise ValueError('Missing or extra reference errors')
    return {'status':'passed','forecasts':len(fs),'outcomes':len(os),'reference_links':links,
            'monitoring_parity':True,'detector_replayed':True,'saved_hashes_verified':len(pins)}


def demonstrate(run_id):
    identifier(run_id)
    root=ROOT/'data/processed/dafr/m6b_synthetic_backend_v1'/run_id
    report=ROOT/'reports/dafr/m6b_v1'/run_id
    if root.exists() or report.exists():raise FileExistsError('M6B run already exists')
    c,execution_sha=load_m6b_config()
    gate=json.loads((ROOT/'reports/dafr/m6b_backend_gate_v1.json').read_text())
    if gate['tests_passed']<315:raise ValueError('Regression gate missing')
    for n,h in gate['sha256'].items():
        if sha(ROOT/n)!=h:raise ValueError('M6B source gate mismatch')
    protected=verify_preservation();root.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();reference=build_fixture_checkpoints(root/'synthetic_checkpoints')
    checkpoint_pins={str(p.relative_to(root)):sha(p) for p in (root/'synthetic_checkpoints').rglob('*') if p.is_file()}
    write_new(root/'manifest.json',{'scope':c['scope'],'configuration_sha256':execution_sha,
        'source_gate':gate,'checkpoint_sha256':checkpoint_pins,'confirmation_execution_allowed':False})
    summaries=[];audits={}
    for scenario in c['scenarios']:
        summaries.append(run_case(root/scenario,reference,scenario));audits[scenario]=audit_case(root/scenario)
    for n,h in checkpoint_pins.items():
        if sha(root/n)!=h:raise ValueError('Synthetic checkpoint changed')
    verify_preservation()
    result={'scope':c['scope'],'status':'complete','protected_hashes':protected,'summaries':summaries,
        'audits':audits,'total_elapsed_seconds_including_checkpoint_build_and_audits':time.perf_counter()-start,
        'peak_process_rss_bytes':rss_bytes(),'confirmation_execution_allowed':False}
    write_new(report/'verification.json',result)
    write_new(root/'completion.json',{'status':'complete','report':str(report.relative_to(ROOT))})
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True)
    print(json.dumps(demonstrate(parser.parse_args().run_id),default=str,indent=2))
