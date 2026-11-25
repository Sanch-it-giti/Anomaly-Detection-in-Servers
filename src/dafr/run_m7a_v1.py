"""Source-gated synthetic M7A execution; no dataset/checkpoint/model reader."""
from collections import defaultdict
from contextlib import ExitStack
import copy,csv,json,time
from dataclasses import asdict
from pathlib import Path
from statistics import mean,median
from .interval_streaming_v1 import SyntheticIntervalStreamV1
from .interval_fixtures_v1 import FIXTURES,fixture_events,fixture_specs
from .interval_v1 import load_interval_config
from .audit_m7a_v1 import audit_interval_run,file_sha
from .run_m6a_v1 import rss_bytes
from .drift_v1 import ROOT
from .contracts import identifier
from .streaming_v2 import _write_json

SOURCES=('configs/dafr_m7a_synthetic_v1.json','src/dafr/interval_contracts_v1.py','src/dafr/interval_v1.py',
    'src/dafr/interval_streaming_v1.py','src/dafr/interval_fixtures_v1.py','src/dafr/audit_m7a_v1.py',
    'src/dafr/run_m7a_v1.py','tests/test_dafr_intervals_v1.py','reports/dafr/m7a_interval_design_v1.md')


def write_new(path,value):
    with Path(path).open('x') as out:_write_json(out,value)


def verify_preservation():
    inventory=json.loads((ROOT/'reports/dafr/m7a_preservation_v1.json').read_text())
    for name,expected in inventory['protected_sha256'].items():
        if file_sha(ROOT/name)!=expected:raise ValueError('Protected artifact changed: '+name)
    # Pure byte checks, intentionally no real model libraries/checkpoint loading.
    registry=json.loads((ROOT/'configs/dafr_m5b1_checkpoint_registry_v1.json').read_text());count=0
    for families in registry['historical_checkpoints'].values():
        for spec in families.values():
            for name,expected in spec['artifact_sha256'].items():
                if file_sha(ROOT/spec['directory']/name)!=expected:raise ValueError('Checkpoint changed')
                count+=1
    return {'historical_hashes':inventory['file_count'],'historical_checkpoint_files':count,'historical_models_loaded':False}


def diagnostics(spec,steps):
    groups=defaultdict(list);outcomes={o.interval_id:o for s in steps for o in s.interval_outcomes}
    for s in steps:
        for r in s.intervals:groups[r.forecast.policy_id,r.forecast.horizon,r.nominal_percent].append(r)
    rows=[]
    for (policy,h,p),records in sorted(groups.items()):
        issued=[r for r in records if r.forecast.issued];available=[r for r in issued if r.status=='available']
        arrived=[outcomes[r.interval_id] for r in issued if r.interval_id in outcomes]
        genuine=[o for o in arrived if o.status!='target_unavailable'];scored=[o for o in genuine if o.status=='scored']
        widths=[r.upper-r.lower for r in available]
        rows.append({'label':'SYNTHETIC ENGINEERING DIAGNOSTIC ONLY','fixture':spec.name,'policy':policy,'horizon':h,'nominal_percent':p,
            'attempts':len(records),'issued_centers':len(issued),'unissued_attempts':len(records)-len(issued),
            'fallback_centers':sum(r.forecast.availability=='fallback' for r in records),
            'available_intervals':len(available),'availability_among_issued':len(available)/len(issued) if issued else None,
            'genuine_matured_centers':len(genuine),'genuine_available_intervals':len(scored),
            'availability_among_genuine_matured':len(scored)/len(genuine) if genuine else None,
            'covered':sum(o.covered for o in scored),'empirical_coverage_available_only':mean(o.covered for o in scored) if scored else None,
            'absolute_coverage_gap':abs(mean(o.covered for o in scored)-p/100) if scored else None,
            'raw_intervals_outside_cpu_range':sum(r.lower<0 or r.upper>100 for r in available),
            'mean_issued_width':mean(widths) if widths else None,'median_issued_width':median(widths) if widths else None,
            'mean_genuine_scored_width':mean(o.width for o in scored) if scored else None,
            'mean_interval_score':mean(o.interval_score for o in scored) if scored else None,
            'missing_targets':sum(o.status=='target_unavailable' for o in arrived),'pending':len(issued)-len(arrived)})
    return rows


def run_case(directory,spec):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    if spec not in FIXTURES:raise ValueError('Declared fixture only')
    config,sha=load_interval_config();start=time.perf_counter();steps=[]
    sim=SyntheticIntervalStreamV1(spec.name,fixture_specs(spec));disabled=copy.deepcopy(sim);disabled.enabled=False
    with ExitStack() as stack:
        names=('ticks','forecasts','outcomes','intervals','scores','interval_outcomes',
               'source_events','disabled_source_events','drift_events','disabled_drift_events')
        files={n:stack.enter_context((directory/(n+'.jsonl')).open('x')) for n in names}
        for row in fixture_events(spec):
            if rss_bytes()>config['maximum_process_rss_bytes']:raise MemoryError('4 GiB RSS guard')
            a=sim.advance(*row);b=disabled.advance(*row)
            if a.source!=b.source or a.drift!=b.drift:raise ValueError('Intervals altered point/selection/drift outputs')
            steps.append(a);_write_json(files['ticks'],{'tick':asdict(a.source.tick),'era':sim.source._era})
            for name,records in (('forecasts',a.source.decisions),('outcomes',a.source.outcomes),('intervals',a.intervals),
                ('scores',a.scores),('interval_outcomes',a.interval_outcomes),('source_events',a.source.events),
                ('disabled_source_events',b.source.events),('drift_events',a.drift.events),('disabled_drift_events',b.drift.events)):
                for r in records:_write_json(files[name],asdict(r))
    result={'fixture':spec.name,'scope':config['scope'],'configuration_sha256':sha,'grid_ticks':len(steps),
        'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
        'point_selector_drift_parity':True,'rows':diagnostics(spec,steps),'confirmation_execution_allowed':False}
    write_new(directory/'summary.json',result)
    write_new(directory/'hashes.json',{p.name:file_sha(p) for p in directory.iterdir() if p.is_file()})
    return result


def demonstrate(run_id):
    identifier(run_id)
    output=ROOT/'data/processed/dafr/m7a_synthetic_v1'/run_id
    report=ROOT/'reports/dafr/m7a_v1'/run_id
    if output.exists() or report.exists():raise FileExistsError('M7A run already exists')
    config,sha=load_interval_config();gate=json.loads((ROOT/'reports/dafr/m7a_synthetic_gate_v1.json').read_text())
    if gate['existing_tests']!=341 or gate['failures'] or gate['errors']:raise ValueError('Test gate failed')
    for n,h in gate['sha256'].items():
        if file_sha(ROOT/n)!=h:raise ValueError('Source gate changed')
    before=verify_preservation();output.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    write_new(output/'manifest.json',{'configuration':config,'configuration_sha256':sha,'source_gate':gate,'scope':config['scope']})
    start=time.perf_counter();summaries=[];audits={}
    for spec in FIXTURES:
        summaries.append(run_case(output/spec.name,spec));audits[spec.name]=audit_interval_run(output/spec.name)
    preservation=verify_preservation();rows=[row for s in summaries for row in s['rows']]
    with (report/'coverage_width_availability.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result={'status':'COMPLETE_STOP_AFTER_M7A','label':'SYNTHETIC ENGINEERING DIAGNOSTIC ONLY',
        'preservation':preservation,'audits':audits,'summaries':summaries,
        'elapsed_seconds_including_audits':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
        'confirmation_execution_allowed':False,'refits':0,'selector_changes':False,'detector_changes':False}
    write_new(report/'verification.json',result);write_new(output/'completion.json',{'status':'completed','preservation':preservation})
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True)
    result=demonstrate(p.parse_args().run_id)
    print(json.dumps({'status':result['status'],'audits':result['audits'],'seconds':result['elapsed_seconds_including_audits']},indent=2))
