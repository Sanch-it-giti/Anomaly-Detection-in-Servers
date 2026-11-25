"""Independent dictionary/deque replay; does not call the interval engine."""
from collections import defaultdict,deque
from datetime import datetime,timedelta
import hashlib,json
from pathlib import Path


def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_interval_run(directory):
    p=Path(directory)
    pins=json.loads((p/'hashes.json').read_text())
    for name,expected in pins.items():
        if file_sha(p/name)!=expected:raise ValueError('Saved ledger changed: '+name)
    read=lambda n:[json.loads(s) for s in (p/(n+'.jsonl')).read_text().splitlines()]
    for a,b in (('source_events','disabled_source_events'),('drift_events','disabled_drift_events')):
        if (p/(a+'.jsonl')).read_bytes()!=(p/(b+'.jsonl')).read_bytes():raise ValueError('Enabled/disabled source changed')
    forecasts=read('forecasts');outcomes=read('outcomes');intervals=read('intervals');receipts=read('interval_outcomes')
    source_events=read('source_events')
    if [e['record'] for e in source_events if e['kind'] in ('issuance','unissued_attempt')]!=forecasts:
        raise ValueError('Forecast ledger differs from immutable source events')
    if [e['record'] for e in source_events if e['kind'] in ('scored','target_unavailable')]!=outcomes:
        raise ValueError('Outcome ledger differs from immutable source events')
    if [e['record'] for e in source_events if e['kind']=='tick']!=[r['tick'] for r in read('ticks')]:
        raise ValueError('Tick ledger differs from immutable source events')
    fs={f['forecast_id']:f for f in forecasts};os={o['forecast_id']:o for o in outcomes}
    ins={(r['forecast']['forecast_id'],r['nominal_percent']):r for r in intervals}
    rs={r['interval_id']:r for r in receipts}
    if len(fs)!=len(forecasts) or len(os)!=len(outcomes) or len(ins)!=len(intervals) or len(rs)!=len(receipts):raise ValueError('Duplicate immutable records')
    if len(ins)!=2*len(fs) or len(rs)!=2*len(os):raise ValueError('Incomplete interval/outcome ledger')
    issued=defaultdict(list);arrived=defaultdict(list)
    for f in forecasts:issued[f['origin']].append(f)
    for o in outcomes:arrived[o['target']].append(o)
    buffers=defaultdict(lambda:deque(maxlen=288));active={};era=0;missing=0;last=None;scored=0;seen_scores=[];seen_receipts=set();seen_intervals=set()
    def require(test,message):
        if not test:raise ValueError(message)
    for row in read('ticks'):
        t=row['tick'];now=datetime.fromisoformat(t['timestamp'])
        require(last is None or now-last==timedelta(minutes=5),'Compressed grid')
        last=now;missing=missing+1 if t['value'] is None else 0
        reset=missing==4
        if reset:era+=1;buffers.clear()
        require(row['era']==era,'Wrong telemetry era')
        oldest=now-timedelta(minutes=5*287)
        for b in buffers.values():
            while b and datetime.fromisoformat(b[0][2])<oldest:b.popleft()
        for o in arrived[t['timestamp']]:
            f=fs[o['forecast_id']]
            require(o['forecast_id'] in active,'Outcome before issuance')
            for k in ('run_id','dataset_id','machine_id','policy_id','policy_version','origin','target','horizon','predicted_value'):
                require(o[k]==f[k],'Exact source linkage mismatch')
            require(f['sequence']==o['issued_sequence'] and f['era']==o['forecast_era'],'Wrong issuance/era')
            require(o['issued_sequence']<o['arrival_sequence']<o['sequence'] and o['actual']==t['value'],'Wrong arrival')
            require(o['status']==('scored' if t['value'] is not None else 'target_unavailable'),'Wrong scoring status')
            if o['status']=='scored':require(o['absolute_error']==abs(o['actual']-f['predicted_value']),'Wrong residual')
            else:require(all(o[k] is None for k in ('signed_error','absolute_error','squared_error')),'Missing error invented')
            for nominal in (90,95):
                interval=active[o['forecast_id']][nominal];receipt=rs[interval['interval_id']];seen_receipts.add(interval['interval_id'])
                expected={'interval_id':interval['interval_id'],'source_outcome_id':o['event_id'],'forecast_id':f['forecast_id'],
                    'target':o['target'],'nominal_percent':nominal,'status':'target_unavailable' if t['value'] is None else 'interval_unavailable',
                    'covered':None,'width':None,'interval_score':None}
                if o['status']=='scored' and interval['status']=='available':
                    lo,hi=interval['lower'],interval['upper'];y=o['actual'];width=hi-lo
                    expected.update(status='scored',covered=lo<=y<=hi,width=width,
                        interval_score=width+(200/(100-nominal))*max(lo-y,0,y-hi));scored+=1
                require(receipt==expected,'Coverage/width/score reconstructed mismatch')
            if o['status']=='scored':
                accepted=f['era']==era
                seen_scores.append({'forecast':f,'outcome':o,'accepted_for_current_era':accepted})
                if accepted:buffers[f['policy_id'],f['policy_version'],f['horizon']].append((f['forecast_id'],o['event_id'],o['target'],o['absolute_error']))
        for f in issued[t['timestamp']]:
            require(f['origin_tick_sequence']==t['sequence'] and f['era']==era,'Wrong current origin')
            require(datetime.fromisoformat(f['target'])-now==timedelta(minutes=5*f['horizon']),'Wrong horizon')
            b=buffers[f['policy_id'],f['policy_version'],f['horizon']]
            payload=[list(x) for x in b]
            support={'policy_id':f['policy_id'],'policy_version':f['policy_version'],'horizon':f['horizon'],'era':era,
                'available_at':t['timestamp'],'count':len(b),'oldest_target':b[0][2] if b else None,'latest_target':b[-1][2] if b else None,
                'scores_sha256':hashlib.sha256(json.dumps(payload,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
                'minimum_support':100,'capacity':288,'recency_grid_ticks':288}
            active[f['forecast_id']]={}
            for nominal in (90,95):
                r=ins[f['forecast_id'],nominal];seen_intervals.add((f['forecast_id'],nominal))
                require(r['forecast']==f and r['support']==support and r['interval_id']==f['forecast_id']+'-pi'+str(nominal),'Noncausal/pooled support')
                available=f['availability'] in ('expert','fallback','baseline')
                status='center_unavailable' if not available else 'insufficient_support' if len(b)<100 else 'available'
                require(r['status']==status and r['clipping']=='none_raw_center_preserved','Availability/clipping mismatch')
                rank=radius=lo=hi=None
                if status=='available':
                    # Independent integer-ceiling implementation, no engine import.
                    quotient,remainder=divmod((len(b)+1)*nominal,100);rank=quotient+int(remainder!=0)
                    radius=sorted(x[3] for x in b)[rank-1];lo=f['predicted_value']-radius;hi=f['predicted_value']+radius
                require((r['quantile_rank'],r['radius'],r['lower'],r['upper'])==(rank,radius,lo,hi),'Order statistic/endpoints mismatch')
                active[f['forecast_id']][nominal]=r
    require(seen_scores==read('scores'),'Calibration sample ledger mismatch')
    require(seen_receipts==set(rs) and seen_intervals==set(ins),'Extra future events')
    return {'status':'passed','forecasts':len(fs),'intervals':len(ins),'source_outcomes':len(os),
        'interval_outcomes':len(rs),'genuine_available_interval_scores':scored,'hashes_verified':len(pins),
        'independent_quantile_support_and_outcome_replay':True,'point_selector_drift_parity':True}
