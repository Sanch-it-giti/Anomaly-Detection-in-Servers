"""Exclusive real-backend/synthetic-only interval verification runs."""
from contextlib import ExitStack
from dataclasses import asdict,dataclass
from datetime import timedelta
from collections import defaultdict
import copy,csv,json,math,time
from pathlib import Path
from statistics import mean

from .interval_real_streaming_v1 import RealIntervalStreamingV1,load_m7b_config
from .drift_real_streaming_v1 import RealBackendDriftStreamV1
from .adaptive_real_fixtures_v1 import build_fixture_checkpoints,fixture_events,declared_failure,forbid_replay_fitting,write_new
from .adaptive_checkpoint_registry_v1 import verify_historical_checkpoints
from .run_m7a_v1 import diagnostics
from .audit_m7a_v1 import file_sha
from .audit_m7b_v1 import audit_backend_intervals
from .run_m6a_v1 import rss_bytes
from .development_qualification_v1 import EPOCH
from .drift_v1 import ROOT
from .streaming_v2 import _write_json
from .contracts import identifier

SOURCES=('configs/dafr_m7b_synthetic_backend_v1.json','src/dafr/interval_real_contracts_v1.py',
 'src/dafr/interval_real_v1.py','src/dafr/interval_real_streaming_v1.py','src/dafr/audit_m7b_v1.py',
 'src/dafr/run_m7b_v1.py','tests/test_dafr_intervals_real_v1.py','reports/dafr/m7b_integration_design_v1.md')


@dataclass(frozen=True,slots=True)
class CaseV1:
    name: str


def events(name):
    if name=='growing':
        for i in range(360):
            yield EPOCH+timedelta(minutes=5*(97+i)),43+(1+7*i/359)*math.sin(.18*i)+math.sin(1.1*i),None
    else:yield from fixture_events(name)


def verify_preservation():
    inventory=json.loads((ROOT/'reports/dafr/m7b_preservation_v1.json').read_text())
    for n,h in inventory['protected_sha256'].items():
        if file_sha(ROOT/n)!=h:raise ValueError('Historical file changed: '+n)
    return {'historical_hashes_verified':inventory['file_count'],'checkpoints':verify_historical_checkpoints()}


def common_diagnostics(name,steps):
    groups=defaultdict(dict)
    for step in steps:
        for r in step.intervals:
            f=r.forecast;groups[f.origin,f.horizon,r.nominal_percent][f.policy_id]=r
    outcomes={o.interval_id:o for s in steps for o in s.interval_outcomes};data=defaultdict(list)
    for (origin,h,p),policies in groups.items():
        scored={policy:outcomes.get(r.interval_id) for policy,r in policies.items()}
        if len(scored)!=4 or any(o is None or o.status!='scored' for o in scored.values()):continue
        if len({r.forecast.context_sha256 for r in policies.values()})!=1:raise ValueError('Unmatched context')
        for policy,o in scored.items():data[h,p,policy].append(o)
    return [{'label':'SYNTHETIC ENGINEERING DIAGNOSTIC ONLY','fixture':name,'horizon':h,'nominal_percent':p,'policy':policy,
        'common_genuine_available_count':len(data[h,p,policy]),
        'empirical_coverage':mean(o.covered for o in data[h,p,policy]) if data[h,p,policy] else None,
        'mean_width':mean(o.width for o in data[h,p,policy]) if data[h,p,policy] else None,
        'mean_interval_score':mean(o.interval_score for o in data[h,p,policy]) if data[h,p,policy] else None}
        for h in (1,12) for p in (90,95) for policy in ('shadow_arima','shadow_xgboost','adaptive','persistence')]


def run_case(directory,reference,name):
    directory=Path(directory);directory.mkdir(exist_ok=False)
    config,integration_sha=load_m7b_config()
    if name not in config['scenarios']:raise ValueError('Unapproved fixture')
    start=time.perf_counter();steps=[]
    with forbid_replay_fitting() as fitting:
        sim=RealIntervalStreamingV1(name,reference);disabled=copy.deepcopy(sim);disabled.intervals_enabled=False
        legacy=RealBackendDriftStreamV1(name,reference)
        write_new(directory/'manifest.json',{'scope':config['scope'],'integration_sha256':integration_sha,
            'registry_sha256':reference.sha256,'registered_experts':{n:{'version':v.version,
            'metadata_sha256':sim._pins[n]['metadata_sha256'],'parameter_sha256':sim._parameters[n]} for n,v in sim._versions.items()}})
        with ExitStack() as stack:
            names=('ticks','forecasts','outcomes','intervals','scores','interval_outcomes','timeline',
                'source_events','disabled_source_events','legacy_source_events','drift_events','disabled_drift_events','legacy_drift_events')
            files={n:stack.enter_context((directory/(n+'.jsonl')).open('x')) for n in names}
            for i,row in enumerate(events(name)):
                if rss_bytes()>config['maximum_process_rss_bytes']:raise MemoryError('4 GiB replay RSS limit')
                with declared_failure(sim,name,i):a=sim.advance(*row)
                with declared_failure(disabled,name,i):b=disabled.advance(*row)
                with declared_failure(legacy.backend,name,i):c=legacy.advance(*row)
                if a.backend!=b.backend or a.backend!=c.backend:raise ValueError('Point centers/selection/state changed')
                if a.monitor_events!=b.monitor_events or [(e.kind,e.record) for e in a.monitor_events]!=[(e.kind,e.record) for e in c.monitor_events]:raise ValueError('Drift payload changed')
                steps.append(a);_write_json(files['ticks'],{'tick':asdict(a.backend.tick),'era':sim._era})
                sources={'forecasts':a.backend.decisions,'outcomes':a.backend.outcomes,'intervals':a.intervals,'scores':a.scores,
                    'interval_outcomes':a.interval_outcomes,'timeline':a.timeline,'source_events':a.backend.events,
                    'disabled_source_events':b.backend.events,'legacy_source_events':c.backend.events,
                    'drift_events':a.monitor_events,'disabled_drift_events':b.monitor_events}
                for n,records in sources.items():
                    for r in records:_write_json(files[n],asdict(r))
                for e in c.monitor_events:_write_json(files['legacy_drift_events'],{'kind':e.kind,'record':asdict(e.record)})
        for n,a in sim._adapters.items():
            if a.parameter_sha256!=sim._parameters[n]:raise ValueError('Model parameters changed')
    result={'fixture':name,'rows':diagnostics(CaseV1(name),steps),'common_rows':common_diagnostics(name,steps),
        'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
        'replay_fit_attempts':fitting['fit_attempts'],'point_selector_drift_parity':True,'confirmation_execution_allowed':False}
    write_new(directory/'summary.json',result)
    write_new(directory/'hashes.json',{p.name:file_sha(p) for p in directory.iterdir() if p.is_file()})
    return result


def demonstrate(run_id):
    identifier(run_id);root=ROOT/'data/processed/dafr/m7b_synthetic_backend_v1'/run_id
    report=ROOT/'reports/dafr/m7b_v1'/run_id
    if root.exists() or report.exists():raise FileExistsError('M7B run already exists')
    config,sha=load_m7b_config();gate=json.loads((ROOT/'reports/dafr/m7b_backend_gate_v1.json').read_text())
    if gate['existing_tests']!=381 or gate['failures'] or gate['errors']:raise ValueError('Passing regression gate required')
    for n,h in gate['sha256'].items():
        if file_sha(ROOT/n)!=h:raise ValueError('Source gate changed')
    before=verify_preservation();root.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();reference=build_fixture_checkpoints(root/'synthetic_checkpoints')
    pins={str(p.relative_to(root)):file_sha(p) for p in (root/'synthetic_checkpoints').rglob('*') if p.is_file()}
    write_new(root/'manifest.json',{'configuration':config,'configuration_sha256':sha,'source_gate':gate,'synthetic_checkpoint_sha256':pins})
    summaries=[];audits={}
    for name in config['scenarios']:
        summaries.append(run_case(root/name,reference,name));audits[name]=audit_backend_intervals(root/name)
    for n,h in pins.items():
        if file_sha(root/n)!=h:raise ValueError('Synthetic fixture checkpoint changed')
    for key,filename in (('rows','coverage_width_availability.csv'),('common_rows','common_target_comparisons.csv')):
        rows=[r for s in summaries for r in s[key]]
        with (report/filename).open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'status':'COMPLETE_STOP_AFTER_M7B','scope':config['scope'],'audits':audits,'summaries':summaries,
        'preservation':verify_preservation(),'elapsed_seconds_including_build_and_audits':time.perf_counter()-start,
        'peak_process_rss_bytes':rss_bytes(),'confirmation_execution_allowed':False,'m8_started':False}
    write_new(report/'verification.json',result);write_new(root/'completion.json',{'status':'complete'})
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True)
    r=demonstrate(p.parse_args().run_id)
    print(json.dumps({'status':r['status'],'audits':r['audits'],'seconds':r['elapsed_seconds_including_build_and_audits']},indent=2))
