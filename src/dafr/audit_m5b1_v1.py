"""Independent auditing of new synthetic real-backend artifacts only."""
from collections import deque
from datetime import datetime,timedelta
import json
import math

from .adaptive_checkpoint_registry_v1 import RegistryReferenceV1,load_fixture_bank,synthetic_fit_values
from .adaptive_real_fixtures_v1 import fixture_events


def rows(path):
    with path.open() as handle:return [json.loads(line) for line in handle]


def verify_backend_run(directory,expected_events=None):
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['scope']=='SYNTHETIC_REAL_BACKEND_FIXTURE' and manifest['real_data_execution_allowed'] is False
    from pathlib import Path
    reference=RegistryReferenceV1(Path(manifest['registry_path']),manifest['registry_sha256'])
    adapters,pins,registry,fit=load_fixture_bank(reference)
    fixture=list(fixture_events(manifest['scenario'])) if expected_events is None else list(expected_events)
    events=rows(directory/'events.jsonl');fs=rows(directory/'shadow_predictions.jsonl')+rows(directory/'policy_predictions.jsonl')
    os=rows(directory/'outcomes.jsonl');by_id={f['forecast_id']:f for f in fs};outcomes={o['forecast_id']:o for o in os}
    assert len(by_id)==len(fs) and len(outcomes)==len(os)
    sequence=[e['sequence'] for e in events];assert sequence==sorted(set(sequence))
    ticks={e['record']['timestamp']:e['record'] for e in events if e['kind']=='tick'}
    states={e['record']['timestamp']:e['record'] for e in events if e['kind']=='state'}
    assert list(ticks)==[t.isoformat() for t,v,r in fixture]
    history=list(synthetic_fit_values()[-23:]);last_genuine=fixture[0][0]-timedelta(minutes=5);gates={};ages={}
    for t,v,r in fixture:
        tick=ticks[t.isoformat()];assert (tick['value'],tick['missing_reason'])==(v,r)
        history=(history+[v])[-24:];gates[t.isoformat()]=all(x is not None for x in history)
        if v is not None:last_genuine=t
        ages[t.isoformat()]=int((t-last_genuine).total_seconds()/300)
    contexts={};counts={'decisions':len(fs),'scored':0,'target_unavailable':0,'pending':0,'unissued':0}
    for f in fs:
        origin,target=map(datetime.fromisoformat,(f['origin'],f['target']))
        assert f['dataset_id']=='synthetic_m5b1_v1' and f['machine_id']=='synthetic'
        assert target-origin==timedelta(minutes=5*f['horizon'])
        assert f['learned_eligible']==gates[f['origin']] and f['last_genuine_age_ticks']==ages[f['origin']]
        assert f['sequence']>states[f['origin']]['sequence']>ticks[f['origin']]['sequence']
        assert f['registry_sha256']==reference.sha256
        contexts.setdefault(f['origin'],set()).add(f['context_sha256'])
        m=f['requested_metadata']
        if m:
            p=pins[m['expert_id']]
            assert m['version']==p['version'] and f['requested_checkpoint_sha256']==p['metadata_sha256']
            assert f['requested_parameter_sha256']==p['loaded_parameter_sha256']
            for cutoff in (m['training_cutoff'],m['available_at'],m['scaling_cutoff'],f['requested_state_cutoff']):
                assert cutoff is None or datetime.fromisoformat(cutoff)<=origin
        issued=f['availability'] in ('expert','fallback','baseline')
        if not issued:
            assert f['predicted_value'] is None and f['forecast_id'] not in outcomes;counts['unissued']+=1;continue
        if f['availability']=='expert':
            assert f['learned_eligible'] and f['requested_state_cutoff']==f['origin']
            if f['policy_id']=='adaptive':
                source=by_id[f['source_shadow_id']]
                assert source['policy_id']=='shadow_'+f['selection']['incumbent']
                for k in ('origin','target','horizon','context_sha256','predicted_value','source_expert','source_version'):assert f[k]==source[k]
        else:assert f['source_expert']=='persistence' and f['last_genuine_age_ticks']<=3
        if f['target'] not in ticks:
            assert f['forecast_id'] not in outcomes and target>fixture[-1][0];counts['pending']+=1;continue
        o=outcomes[f['forecast_id']];tick=ticks[f['target']]
        for k in ('origin','target','horizon','policy_id','predicted_value'):assert f[k]==o[k]
        assert f['sequence']<tick['sequence']<o['sequence']<states[f['target']]['sequence']
        assert o['actual']==tick['value']
        if tick['value'] is None:
            assert o['status']=='target_unavailable' and all(o[k] is None for k in ('actual','absolute_error','squared_error','signed_error','interval_hit'))
            counts['target_unavailable']+=1
        else:
            error=tick['value']-f['predicted_value'];assert o['status']=='scored'
            assert math.isclose(o['absolute_error'],abs(error),abs_tol=1e-12) and math.isclose(o['squared_error'],error*error,abs_tol=1e-12)
            counts['scored']+=1
    assert len(fs)==sum(counts[k] for k in ('scored','target_unavailable','pending','unissued'))
    buffers={1:deque(maxlen=288),12:deque(maxlen=288)};incumbents={1:'arima',12:'arima'}
    dwell={1:fixture[0][0],12:fixture[0][0]};switches={1:0,12:0};matched={1:0,12:0};updates={'arima':0,'xgboost':0};era=0;resets=0
    for event in events:
        kind,r=event['kind'],event['record']
        if kind=='tick':
            now=datetime.fromisoformat(r['timestamp']);cutoff=now-timedelta(minutes=5*287)
            for b in buffers.values():
                while b and datetime.fromisoformat(b[0]['target'])<cutoff:b.popleft()
        elif kind=='telemetry_reset':
            assert r['missing_streak']==4 and r['new_era']==era+1;era+=1;resets+=1
            for h,b in buffers.items():b.clear();incumbents[h]='arima';dwell[h]=now
        elif kind=='matched_shadow_loss':
            h=r['horizon'];matched[h]+=1
            for i,fid in enumerate(r['forecast_ids']):
                f=by_id[fid];o=outcomes[fid]
                assert f['policy_id']==('shadow_arima','shadow_xgboost')[i] and f['availability']=='expert'
                for k in ('origin','target','horizon','era','context_sha256'):assert f[k]==r[k]
                assert o['status']=='scored' and o['target']==now.isoformat() and o['absolute_error']==r['absolute_errors'][i]
                assert o['sequence']<event['sequence'] and f['source_version']==r['versions'][i]
            if r['era']==era:buffers[h].append(r)
        elif kind=='adapter_update':
            updates[r['metadata']['expert_id']]+=1
            assert r['result']['observation_cutoff']==now.isoformat()
            if r['status']=='ok':assert r['result']['model_state_cutoff']==now.isoformat()
        elif kind=='selector_state':
            h=r['horizon'];b=buffers[h]
            assert r['before']==incumbents[h] and r['matched_count']==len(b)
            assert r['earliest_target']==(b[0]['target'] if b else None) and r['latest_target']==(b[-1]['target'] if b else None)
            if b:
                means=[sum(p['absolute_errors'][i] for p in b)/len(b) for i in (0,1)]
                assert all(math.isclose(a,z,abs_tol=1e-12) for a,z in zip(means,r['mean_absolute_errors']))
            if r['incumbent']!=r['before']:
                assert len(b)>=100 and now-dwell[h]>=timedelta(minutes=5*24)
                old,new=(('arima','xgboost').index(r[k]) for k in ('before','incumbent'))
                assert means[old]-means[new]+1e-12>=max(.1,.05*means[old]) and r['reason']=='matched_loss_switch'
                for expert in ('arima','xgboost'):
                    assert any(f['policy_id']=='shadow_'+expert and f['horizon']==h and f['origin']==now.isoformat() and f['availability']=='expert' for f in fs)
                incumbents[h]=r['incumbent'];dwell[h]=now;switches[h]+=1
            assert r['switch_count']==switches[h]
    assert all(len(v)==1 for v in contexts.values()) and len(contexts)==len(fixture)
    assert all(n==len(fixture) for n in updates.values())
    return {'passed':True,**counts,'grid_ticks':len(fixture),'matched_pairs':matched,'switches':switches,'telemetry_resets':resets,
        'exact_updates_per_expert':updates,'final_support':{h:len(b) for h,b in buffers.items()},
        'checkpoint_registry_verified':True,'synthetic_ledgers_only':True}
