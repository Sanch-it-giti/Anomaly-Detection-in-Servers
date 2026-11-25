"""Independent saved-ledger audit; does not invoke the selector or replay."""
from collections import deque
from dataclasses import asdict
from datetime import datetime,timedelta
import json
import math

from .retrospective_sources_v1 import LABEL


def read_rows(path):
    with path.open() as source:return [json.loads(line) for line in source]


def require(condition,message):
    if not condition:raise ValueError('Retrospective audit: '+message)


def verify_machine(directory,inputs):
    decisions=read_rows(directory/'decisions.jsonl');outcomes=read_rows(directory/'outcomes.jsonl')
    events=read_rows(directory/'events.jsonl')
    require(len(decisions)==len(inputs.frames)*2,'incomplete adaptive decisions')
    ids={d['decision_id']:d for d in decisions};resolved={o['decision_id']:o for o in outcomes}
    require(len(ids)==len(decisions) and len(resolved)==len(outcomes),'duplicate records')
    seq=[e['sequence'] for e in events];require(seq==sorted(set(seq)),'event sequences')
    require(all(e['label']==LABEL for e in events),'diagnostic labeling')
    emitted=[e['record'] for e in events if e['kind']=='adaptive_decision']
    require(emitted==decisions,'decision/event ledger mismatch')
    require([e['record'] for e in events if e['kind'] in ('adaptive_scored','adaptive_target_unavailable')]==outcomes,'outcome/event mismatch')
    source_refs={s.reference.forecast_id:s for f in inputs.frames for s in f.forecasts}
    source_outcomes={o.forecast_id:o for f in inputs.frames for o in f.outcomes}
    times={f.tick.timestamp for f in inputs.frames}
    groups=[]
    for e in events:
        if e['kind']=='source_tick':groups.append([])
        require(bool(groups),'events before first tick');groups[-1].append(e)
    require(len(groups)==len(inputs.frames),'tick groups')
    buffer={1:deque(maxlen=288),12:deque(maxlen=288)}
    inc={1:'arima',12:'arima'};changes={1:inputs.frames[0].tick.timestamp,12:inputs.frames[0].tick.timestamp}
    switches={1:0,12:0};era=inputs.initial_era;reset_count=0;pair_counts={1:0,12:0}
    scored=missing=pending=abstentions=0
    for frame,group in zip(inputs.frames,groups):
        now=frame.tick.timestamp
        require(group[0]['record']['timestamp']==now.isoformat() and group[0]['record']['value']==frame.tick.value,'tick values/time')
        actual_source=[e['record'] for e in group if e['kind'] in ('source_scored','source_target_unavailable')]
        require({o['forecast_id'] for o in actual_source}=={o.forecast_id for o in frame.outcomes},'premature/missing shadow outcomes')
        for o in actual_source:
            require(o['target']==now.isoformat(),'future source loss')
            original=source_outcomes[o['forecast_id']]
            require(o['absolute_error']==original.absolute_error and o['actual']==original.actual,'modified source losses')
        reset=frame.reset is not None
        previous=(inc[1],inc[12])
        if reset:
            era+=1;reset_count+=1
            for h in (1,12):buffer[h].clear();inc[h]='arima';changes[h]=now
        require(era==frame.state.era,'telemetry era')
        cutoff=now-timedelta(minutes=5*287);expired=[]
        for h in (1,12):
            n=0
            while buffer[h] and buffer[h][0]['target']<cutoff:buffer[h].popleft();n+=1
            expired.append(n)
        paired={}
        for o in frame.outcomes:
            s=source_refs[o.forecast_id];f=s.forecast
            if f.policy_id in ('arima','xgboost') and f.availability=='expert' and o.status=='scored':
                paired.setdefault((f.origin,f.target,f.horizon,f.era,f.context_sha256),{})[f.policy_id]=(s,o)
        expected_pairs=[];capacity=[0,0]
        for key,pair in paired.items():
            if set(pair)!={'arima','xgboost'}:continue
            a,ao=pair['arima'];x,xo=pair['xgboost'];h=key[2]
            row={'origin':key[0],'target':key[1],'era':key[3],
                'errors':(ao.absolute_error,xo.absolute_error),'ids':(a.forecast.forecast_id,x.forecast.forecast_id),
                'versions':(a.forecast.source_version,x.forecast.source_version),'context':key[4],'horizon':h}
            expected_pairs.append(row);pair_counts[h]+=1
            if key[3]==era:
                if len(buffer[h])==288:capacity[0 if h==1 else 1]+=1
                buffer[h].append(row)
        pair_events=[e for e in group if e['kind']=='matched_shadow_loss']
        require(len(pair_events)==len(expected_pairs),'matched loss accounting')
        for e,row in zip(pair_events,expected_pairs):
            p=e['record']
            require(p['target']==now.isoformat() and tuple(p['forecast_ids'])==row['ids'] and tuple(p['absolute_errors'])==row['errors'] and tuple(p['versions'])==row['versions'],'matched evidence modified or unmatched')
        state_event=next(e for e in group if e['kind']=='causal_state');state=state_event['record']
        require(state['expired_by_age']==expired and state['capacity_evictions']==capacity,'support expiration/capacity accounting')
        require(state['previous_incumbents']==list(previous) and state['reset']==reset,'reset/default provenance')
        require(sum(e['kind']=='telemetry_reset' for e in group)==int(reset),'telemetry event count')
        for e in group:
            if e['kind'].startswith('source_') and e['kind']!='source_tick' or e['kind'] in ('adaptive_scored','adaptive_target_unavailable','matched_shadow_loss'):
                require(e['sequence']<state_event['sequence'],'feedback after selection state')
        bank={(s.forecast.policy_id,s.forecast.horizon):s for s in frame.forecasts}
        snapshots=[e for e in group if e['kind']=='selector_state']
        require(len(snapshots)==2,'independent horizon snapshots missing')
        for e,h in zip(snapshots,(1,12)):
            snapshot=e['record'];b=buffer[h];before=inc[h]
            means=tuple(sum(p['errors'][i] for p in b)/len(b) for i in (0,1)) if b else None
            elapsed=int((now-changes[h]).total_seconds()/300);margin=None
            available={p for p in ('arima','xgboost') if bank[p,h].forecast.availability=='expert'}
            if not frame.state.learned_eligible:reason='history_gate'
            elif before not in available:reason='incumbent_unavailable'
            elif available!={'arima','xgboost'}:reason='challenger_unavailable'
            elif len(b)<100:reason='insufficient_matched_support'
            else:
                challenger='xgboost' if before=='arima' else 'arima'
                old,new=means[('arima','xgboost').index(before)],means[('arima','xgboost').index(challenger)]
                gain=old-new;margin=max(.1,.05*old)
                if abs(gain)<=1e-12:reason='tie_hold_incumbent'
                elif gain<=0 or gain+1e-12<margin:reason='hysteresis_hold'
                elif elapsed<24:reason='dwell_hold'
                else:reason='matched_loss_switch';inc[h]=challenger;switches[h]+=1;changes[h]=now
            require((snapshot['timestamp'],snapshot['horizon'],snapshot['era'],snapshot['before'],snapshot['incumbent'],snapshot['reason'],snapshot['matched_count'],snapshot['dwell_elapsed_ticks'],snapshot['switch_count'])==(
                now.isoformat(),h,era,before,inc[h],reason,len(b),elapsed,switches[h]),'frozen selector rule mismatch')
            require(snapshot['earliest_target']==(b[0]['target'].isoformat() if b else None) and snapshot['latest_target']==(b[-1]['target'].isoformat() if b else None),'support timestamps')
            require(snapshot['required_improvement']==margin,'improvement margin')
            require(snapshot['mean_absolute_errors'] is None if means is None else all(math.isclose(a,z,abs_tol=1e-12) for a,z in zip(snapshot['mean_absolute_errors'],means)),'mean losses')
            d=next(d for d in decisions if d['origin']==now.isoformat() and d['horizon']==h)
            chosen=bank[inc[h],h];source=chosen if chosen.forecast.availability=='expert' else bank['persistence',h]
            expected='expert' if source is chosen else 'fallback' if source.forecast.issued else 'abstained'
            require(d['selection']==snapshot and d['sequence']>e['sequence'],'immutable decision/selection linkage')
            require(d['label']==LABEL and d['availability']==expected and d['predicted_value']==source.forecast.predicted_value and d['selected_expert']==source.forecast.selected_expert,'invented adaptive prediction/source')
            require(d['source_reference']==asdict(source.reference) and d['incumbent_reference']==asdict(chosen.reference),'source provenance')
            require(d['source_version']==source.forecast.source_version and d['context_sha256']==source.forecast.context_sha256,'source model/context version')
            require(d['target']==source.forecast.target.isoformat(),'target shifted')
            if expected=='abstained':
                require(d['decision_id'] not in resolved,'abstention scored');abstentions+=1;continue
            if source.forecast.target not in times:
                require(d['decision_id'] not in resolved,'boundary target scored');pending+=1;continue
            o=resolved[d['decision_id']];original=source_outcomes[source.forecast.forecast_id]
            require(o['source_reference']==d['source_reference'] and o['source_outcome_id']==original.event_id and o['source_outcome_sequence']==original.sequence,'source outcome linkage')
            require(o['origin']==d['origin'] and o['target']==d['target'] and o['horizon']==h and o['predicted_value']==d['predicted_value'],'adaptive outcome changed issuance')
            require(o['status']==original.status and o['actual']==original.actual,'adaptive actual/missing status')
            for k in ('signed_error','absolute_error','squared_error'):require(o[k]==getattr(original,k),'adaptive error differs from immutable source')
            if original.status=='scored':
                require(math.isclose(o['absolute_error'],abs(o['actual']-d['predicted_value']),abs_tol=1e-12),'error arithmetic');scored+=1
            else:missing+=1
    require(len(decisions)==scored+missing+pending+abstentions,'decision reconciliation')
    require(len(outcomes)==scored+missing,'extra outcomes')
    # Match each adaptive score to the tick group in which it actually arrived.
    for frame,group in zip(inputs.frames,groups):
        for e in group:
            if e['kind'] in ('adaptive_scored','adaptive_target_unavailable'):
                o=e['record'];d=ids[o['decision_id']]
                require(o['target']==frame.tick.timestamp.isoformat() and d['sequence']<group[0]['sequence']<e['sequence'],'premature adaptive feedback')
    require(sum(e['kind']=='expert_switch' for e in events)==sum(switches.values()),'switch log count')
    # Recompute comparison subsets and errors independently from linked centers
    # and genuine recorded target ticks, rather than trusting output metrics.
    actual={f.tick.timestamp.isoformat():f.tick.value for f in inputs.frames}
    points={p:{} for p in ('persistence','arima','xgboost','adaptive')};expert={p:set() for p in points}
    for saved in source_refs.values():
        f=saved.forecast;target=f.target.isoformat()
        if not f.issued or target not in actual or actual[target] is None:continue
        key=(f.origin.isoformat(),target,f.horizon);points[f.policy_id][key]=actual[target]-f.predicted_value
        if f.policy_id=='persistence' or f.availability=='expert':expert[f.policy_id].add(key)
    for d in decisions:
        if d['availability']=='abstained' or d['target'] not in actual or actual[d['target']] is None:continue
        key=(d['origin'],d['target'],d['horizon']);points['adaptive'][key]=actual[d['target']]-d['predicted_value']
        if d['availability']=='expert':expert['adaptive'].add(key)
    metrics=[]
    for h in (1,12):
        for scope in ('expert_matched','complete_policy_matched'):
            keys=set.intersection(*({k for k in (expert[p] if scope=='expert_matched' else points[p]) if k[2]==h} for p in points))
            for p in points:
                errors=[points[p][k] for k in sorted(keys)]
                metrics.append({'machine':inputs.machine,'horizon':h,'scope':scope,'policy':p,'count':len(errors),
                    'mae':sum(abs(e) for e in errors)/len(errors) if errors else None,
                    'rmse':math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None})
    return {'label':LABEL,'passed':True,'machine':inputs.machine,'decisions':len(decisions),'scored':scored,
        'missing_targets':missing,'pending':pending,'abstentions':abstentions,'switches':switches,
        'telemetry_resets':reset_count,'matched_pairs':pair_counts,'final_support':{h:len(b) for h,b in buffer.items()},
        'selector_reimplemented_independently':True,'source_predictions_recomputed':False,'recomputed_comparisons':metrics}
