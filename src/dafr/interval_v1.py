"""Causal complete-policy rolling absolute-residual order-statistic engine."""
from collections import deque
from datetime import timedelta
import hashlib,json
from .contracts_v2 import TickEventV2,TargetOutcomeV2
from .selector_contracts_v1 import SyntheticForecastV1
from .interval_contracts_v1 import CalibrationScoreV1,CalibrationSupportV1,IntervalRecordV1,IntervalOutcomeV1
from .drift_v1 import ROOT


def load_interval_config():
    raw=(ROOT/'configs/dafr_m7a_synthetic_v1.json').read_bytes();c=json.loads(raw)
    if c['schema_version']!='dafr_m7a_synthetic_v1' or c['scope']!='SYNTHETIC_DETERMINISTIC_ONLY':raise ValueError('Synthetic scope required')
    for key in ('confirmation_execution_allowed','real_data_execution_allowed','refitting_allowed','reliability_selection_response_allowed','detector_response_allowed'):
        if c.get(key) is not False:raise ValueError('Unauthorized capability: '+key)
    if c['nominal_percent']!=[90,95] or (c['minimum_support'],c['capacity'],c['recency_grid_ticks'])!=(100,288,288):raise ValueError('Frozen research constraints changed')
    if c['clipping']!='none_raw_center_preserved' or c['calibration_key']!='complete_policy_version_horizon_era':raise ValueError('Unsupported calibration rule')
    for name,expected in c['frozen_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen dependency changed: '+name)
    return c,hashlib.sha256(raw).hexdigest()


def order_statistic(errors,nominal_percent):
    if type(nominal_percent) is not int or nominal_percent not in (90,95):raise ValueError('Frozen nominal level required')
    from .contracts import finite_number
    values=list(errors)
    for v in values:
        finite_number(v)
        if v<0:raise ValueError('Residual magnitude cannot be negative')
    n=len(values);rank=((n+1)*nominal_percent+99)//100
    return (rank,sorted(values)[rank-1]) if rank<=n else (rank,None)


class RollingIntervalsV1:
    def __init__(self):
        self.configuration,self.execution_sha256=load_interval_config()
        self.now=None;self.era=0;self._identity=None;self._buffers={};self._seen=set()
        self.intervals={};self.outcomes={};self._issued_forecasts=set();self._phase='unstarted'
        self._missing_streak=0;self._model_versions={};self._keys=set();self._tick=None

    def clock(self,tick,era):
        if type(tick) is not TickEventV2 or type(era) is not int or era not in (self.era,self.era+1):raise ValueError('Validated tick/era required')
        if self.now is not None and tick.timestamp-self.now!=timedelta(minutes=5):raise ValueError('Every exact grid tick required')
        missing_streak=0 if tick.genuine else self._missing_streak+1
        if era!=self.era+int(missing_streak==4):raise ValueError('Era changes only on fourth missing tick')
        identity=(tick.run_id,tick.dataset_id,tick.machine_id)
        if self._identity is not None and identity!=self._identity:raise ValueError('Stream identity changed')
        self._identity=identity;reset=era!=self.era
        if reset:self._buffers.clear()
        self.now=tick.timestamp;self.era=era;self._phase='maturing';self._missing_streak=missing_streak;self._tick=tick
        oldest=self.now-timedelta(minutes=5*287);expired=0
        for b in self._buffers.values():
            while b and b[0].outcome.target<oldest:b.popleft();expired+=1
        return {'available_at':self.now,'era':era,'reset':reset,'expired_scores':expired}

    def mature(self,f,o):
        if self._phase!='maturing' or type(f) is not SyntheticForecastV1 or type(o) is not TargetOutcomeV2:
            raise ValueError('Mature outcomes before interval issuance')
        if o.target!=self.now or f.era>self.era or (f.run_id,f.dataset_id,f.machine_id)!=self._identity:
            raise ValueError('Only current exact genuine/missing target records')
        if (o.tick_id,o.arrival_sequence,o.actual)!=(self._tick.event_id,self._tick.sequence,self._tick.value):
            raise ValueError('Outcome must match the actual revealed tick')
        if (o.status=='scored')!=self._tick.genuine:raise ValueError('Observation availability mismatch')
        if f.forecast_id not in self._issued_forecasts or f.forecast_id in self._seen:raise ValueError('Unknown or duplicate outcome')
        for n in ('forecast_id','run_id','dataset_id','machine_id','policy_id','policy_version','origin','target','horizon','predicted_value'):
            if getattr(f,n)!=getattr(o,n):raise ValueError('Original outcome mismatch')
        if f.sequence!=o.issued_sequence or f.era!=o.forecast_era:raise ValueError('Original sequence/era mismatch')
        if any(self.intervals[f.forecast_id,p].forecast!=f for p in (90,95)):raise ValueError('Forecast revision forbidden')
        self._seen.add(f.forecast_id);receipts=[]
        for p in (90,95):
            interval=self.intervals[f.forecast_id,p]
            covered=width=score=None
            if o.status=='target_unavailable':status='target_unavailable'
            elif interval.status!='available':status='interval_unavailable'
            else:
                status='scored';lo,hi=interval.lower,interval.upper;y=o.actual
                covered=lo<=y<=hi;width=hi-lo
                score=width+(200/(100-p))*max(lo-y,0,y-hi)
            receipt=IntervalOutcomeV1(interval.interval_id,o.event_id,f.forecast_id,o.target,p,status,covered,width,score)
            self.outcomes[receipt.interval_id]=receipt;receipts.append(receipt)
        sample=None
        if o.status=='scored':
            sample=CalibrationScoreV1(f,o,f.era==self.era)
            if sample.accepted_for_current_era:
                key=(f.policy_id,f.policy_version,f.horizon)
                self._buffers.setdefault(key,deque(maxlen=288)).append(sample)
        return sample,tuple(receipts)

    def issue(self,f):
        if type(f) is not SyntheticForecastV1 or f.origin!=self.now or f.era!=self.era or (f.run_id,f.dataset_id,f.machine_id)!=self._identity:
            raise ValueError('Current validated synthetic issuance required')
        key=(f.policy_id,f.policy_version,f.horizon,f.origin)
        if f.forecast_id in self._issued_forecasts or key in self._keys:raise ValueError('Duplicate issuance')
        if f.origin_tick_sequence!=self._tick.sequence:raise ValueError('Wrong revealed origin sequence')
        if f.requested_metadata is not None:
            m=f.requested_metadata
            if m.expert_id in self._model_versions and self._model_versions[m.expert_id]!=m:raise ValueError('Model version changes need a separately approved calibration contract')
            self._model_versions[m.expert_id]=m
        self._phase='issuing';self._issued_forecasts.add(f.forecast_id);self._keys.add(key)
        b=self._buffers.get((f.policy_id,f.policy_version,f.horizon),())
        payload=[(s.forecast.forecast_id,s.outcome.event_id,s.outcome.target.isoformat(),s.outcome.absolute_error) for s in b]
        support=CalibrationSupportV1(f.policy_id,f.policy_version,f.horizon,self.era,self.now,len(b),
            b[0].outcome.target if b else None,b[-1].outcome.target if b else None,
            hashlib.sha256(json.dumps(payload,separators=(',',':'),allow_nan=False).encode()).hexdigest())
        records=[]
        for p in (90,95):
            rank=radius=lo=hi=None
            if not f.issued:status='center_unavailable'
            elif len(b)<100:status='insufficient_support'
            else:
                rank,radius=order_statistic((s.outcome.absolute_error for s in b),p)
                if radius is None:status='rank_unavailable';rank=None
                else:status='available';lo=f.predicted_value-radius;hi=f.predicted_value+radius
            r=IntervalRecordV1(f.forecast_id+'-pi'+str(p),f,p,status,support,rank,radius,lo,hi,self.execution_sha256)
            self.intervals[f.forecast_id,p]=r;records.append(r)
        return tuple(records)
