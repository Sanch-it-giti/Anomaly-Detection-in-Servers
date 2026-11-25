"""Frozen synthetic M5A demonstrations and independent saved-ledger auditing."""
from collections import deque
from dataclasses import asdict
from datetime import datetime, timedelta
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from .contracts import identifier
from .selector_v1 import ROOT,load_selector_config
from .selector_streaming_v1 import run_synthetic,synthetic_events
from .streaming_v2 import _write_json

SOURCES=('configs/dafr_m5a_synthetic_v1.json','src/dafr/selector_contracts_v1.py',
    'src/dafr/selector_v1.py','src/dafr/selector_streaming_v1.py','src/dafr/run_m5a_v1.py',
    'tests/test_dafr_selector_v1.py','reports/dafr/m5a_selector_design_v1.md')
SCENARIOS=('stable','regime_switch','horizon_divergence','gaps_failures')


def sha(path):
    # Opaque preservation hashing; never parse historical observation ledgers.
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify_preserved():
    receipt=json.loads((ROOT/'reports/dafr/m5a_preservation_v1.json').read_text())
    for name,expected in receipt['protected_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Protected historical artifact changed: '+name)
    return receipt['file_count']


def write_new(path,record):
    with path.open('x') as out:_write_json(out,record)


def read_jsonl(path):
    with path.open() as source:return [json.loads(line) for line in source]


def verify_synthetic_run(directory,scenario):
    """Only new synthetic artifacts are parsed. All assertions fail the run."""
    events=read_jsonl(directory/'events.jsonl')
    forecasts=read_jsonl(directory/'shadow_predictions.jsonl')+read_jsonl(directory/'policy_predictions.jsonl')
    outcomes=read_jsonl(directory/'outcomes.jsonl')
    fs={f['forecast_id']:f for f in forecasts};os={o['forecast_id']:o for o in outcomes}
    assert len(fs)==len(forecasts) and len(os)==len(outcomes)
    sequences=[e['sequence'] for e in events];assert sequences==sorted(set(sequences))
    ticks={e['record']['timestamp']:e['record'] for e in events if e['kind']=='tick'}
    fixture=list(synthetic_events(scenario));assert len(ticks)==len(fixture)
    for timestamp,value,reason in fixture:
        assert ticks[timestamp.isoformat()]['value']==value
        assert ticks[timestamp.isoformat()]['missing_reason']==reason
    scored=missing=pending=unissued=0
    for f in forecasts:
        origin,target=map(datetime.fromisoformat,(f['origin'],f['target']))
        assert target-origin==timedelta(minutes=5*f['horizon'])
        assert f['sequence']>ticks[f['origin']]['sequence']
        assert f['interval_status']==f['detector_status']=='not_implemented'
        if f['availability'] not in ('expert','baseline','fallback'):
            assert f['predicted_value'] is None and f['forecast_id'] not in os;unissued+=1;continue
        if f['availability']=='expert':
            assert f['learned_eligible'] and f['last_genuine_age_ticks']==0
            metadata=f['requested_metadata']
            for key in ('training_cutoff','scaling_cutoff','available_at'):
                assert metadata[key] is None or datetime.fromisoformat(metadata[key])<=origin
        if f['policy_id']=='adaptive' and f['availability']=='expert':
            source=fs[f['source_shadow_id']]
            assert source['policy_id']=='shadow_'+f['source_expert']
            for k in ('origin','target','horizon','context_sha256','predicted_value','source_version'):
                assert f[k]==source[k]
        if f['availability'] in ('fallback','baseline'):
            assert f['source_expert']=='persistence' and f['last_genuine_age_ticks']<=3
        if f['target'] not in ticks:
            assert f['forecast_id'] not in os;pending+=1;continue
        outcome=os[f['forecast_id']];tick=ticks[f['target']]
        assert f['sequence']<tick['sequence']<outcome['sequence']
        for k in ('origin','target','horizon','policy_id','predicted_value'):assert f[k]==outcome[k]
        assert outcome['actual']==tick['value']
        if tick['value'] is None:
            assert outcome['status']=='target_unavailable'
            assert all(outcome[k] is None for k in ('actual','signed_error','absolute_error','squared_error','interval_hit'));missing+=1
        else:
            assert outcome['status']=='scored';error=outcome['actual']-f['predicted_value']
            assert math.isclose(outcome['absolute_error'],abs(error),abs_tol=1e-12)
            assert math.isclose(outcome['squared_error'],error*error,abs_tol=1e-12);scored+=1
    assert len(forecasts)==scored+missing+pending+unissued
    buffers={1:deque(maxlen=288),12:deque(maxlen=288)};era=0;matched={1:0,12:0};incumbents={1:'arima',12:'arima'}
    dwell={1:fixture[0][0],12:fixture[0][0]};switches={1:0,12:0};contexts={};reset_count=0
    for event in events:
        kind,r=event['kind'],event['record']
        if kind=='tick':
            now=datetime.fromisoformat(r['timestamp'])
            cutoff=now-timedelta(minutes=5*287)
            for b in buffers.values():
                while b and datetime.fromisoformat(b[0]['target'])<cutoff:b.popleft()
        elif kind=='telemetry_reset':
            assert r['missing_streak']==4 and r['new_era']==era+1
            era+=1;reset_count+=1
            for h,b in buffers.items():b.clear();incumbents[h]='arima';dwell[h]=now
        elif kind=='matched_shadow_loss':
            h=r['horizon'];matched[h]+=1
            for i,fid in enumerate(r['forecast_ids']):
                f=fs[fid];o=os[fid]
                assert f['policy_id']==('shadow_arima','shadow_xgboost')[i] and f['availability']=='expert'
                assert o['status']=='scored' and o['target']==now.isoformat()
                for k in ('origin','target','horizon','era','context_sha256'):assert f[k]==r[k]
                assert f['source_version']==r['versions'][i] and o['absolute_error']==r['absolute_errors'][i]
                assert o['sequence']<event['sequence']
            if r['era']==era:buffers[h].append(r)
        elif kind=='adapter_update':contexts.setdefault(r['origin'],set()).add(r['context_sha256'])
        elif kind=='selector_state':
            h=r['horizon'];b=buffers[h]
            assert r['before']==incumbents[h] and r['matched_count']==len(b)
            assert r['earliest_target']==(b[0]['target'] if b else None)
            assert r['latest_target']==(b[-1]['target'] if b else None)
            if b:
                means=[sum(p['absolute_errors'][i] for p in b)/len(b) for i in (0,1)]
                assert all(math.isclose(a,z,abs_tol=1e-12) for a,z in zip(means,r['mean_absolute_errors']))
            if r['incumbent']!=r['before']:
                assert len(b)>=100 and now-dwell[h]>=timedelta(minutes=5*24)
                old,new=(('arima','xgboost').index(r[k]) for k in ('before','incumbent'))
                assert means[old]-means[new]+1e-12>=max(.1,.05*means[old])
                assert r['reason']=='matched_loss_switch';incumbents[h]=r['incumbent'];dwell[h]=now;switches[h]+=1
            assert r['switch_count']==switches[h]
    assert all(len(v)==1 for v in contexts.values()) and len(contexts)==len(ticks)
    assert sum(e['kind']=='expert_switch' for e in events)==sum(switches.values())
    summary=json.loads((directory/'summary.json').read_text())
    assert summary['switch_counts']=={str(k):v for k,v in switches.items()}
    assert summary['telemetry_resets']==reset_count
    return {'passed':True,'scenario':scenario,'grid_ticks':len(ticks),'decisions':len(forecasts),
        'scored':scored,'target_unavailable':missing,'boundary_pending':pending,'unissued_attempts':unissued,
        'matched_pairs':matched,'switch_counts':switches,'telemetry_resets':reset_count,
        'shared_context_ticks':len(contexts),'synthetic_ledgers_only':True}


def demonstrate(run_id):
    identifier(run_id);load_selector_config();protected=verify_preserved()
    gate=json.loads((ROOT/'reports/dafr/m5a_synthetic_gate_v1.json').read_text())
    if gate.get('passed') is not True:raise ValueError('Successful synthetic test gate required')
    if any(gate['source_sha256'].get(p)!=sha(ROOT/p) for p in SOURCES):raise ValueError('Source gate changed')
    parent=ROOT/'reports/dafr/m5a_v1'
    if parent.resolve()!=parent:raise ValueError('Report output redirection forbidden')
    parent.mkdir(parents=True,exist_ok=True);report=parent/run_id;report.mkdir(exist_ok=False)
    results={};audits={};rows=[]
    for scenario in SCENARIOS:
        directory=run_synthetic(run_id+'-'+scenario,scenario)
        results[scenario]=json.loads((directory/'summary.json').read_text())
        audits[scenario]=verify_synthetic_run(directory,scenario)
        for row in results[scenario]['policy_and_shadow_accounting']:rows.append({'scenario':scenario,**row})
    assert verify_preserved()==protected
    write_new(report/'synthetic_summary.json',results)
    write_new(report/'ledger_verification.json',audits)
    with (report/'availability_accounting.csv').open('x',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write_new(report/'preservation_verification.json',{'passed':True,'historical_hashes_verified':protected,
        'checkpoint_fingerprints_preserved':True,'historical_data_parsed_by_selector':False,
        'regression_fixture_reads_separately_approved':True,'confirmation_execution_allowed':False,
        'protected_inventory_sha256':sha(ROOT/'reports/dafr/m5a_preservation_v1.json')})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    print(demonstrate(parser.parse_args().run_id))
