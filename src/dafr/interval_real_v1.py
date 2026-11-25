"""M7B real-type binding of frozen M7A calibration semantics.

Clock/reset/expiry and the discrete quantile are reused unchanged. The literal
maturity/issuance implementation retains M7A arithmetic but validates real types.
"""
from collections import deque
import hashlib,json
from .interval_v1 import RollingIntervalsV1,order_statistic
from .interval_real_contracts_v1 import BackendCalibrationScoreV1,BackendIntervalRecordV1
from .interval_contracts_v1 import CalibrationSupportV1,IntervalOutcomeV1
from .adaptive_real_contracts_v1 import BackendForecastV1
from .contracts_v2 import TargetOutcomeV2
from .real_adapters_v1 import RealVersion
from .selector_contracts_v1 import digest

class BackendIntervalsV1(RollingIntervalsV1):
    def __init__(self,registry_sha256,versions,pins,parameters):
        super().__init__();digest(registry_sha256)
        if set(versions)!={'arima','xgboost'} or any(type(v) is not RealVersion for v in versions.values()):
            raise ValueError('Registered real metadata required')
        self.registry_sha256=registry_sha256;self.versions=dict(versions)
        self.checkpoints={n:pins[n]['metadata_sha256'] for n in versions};self.parameters=dict(parameters)
        for h in tuple(self.checkpoints.values())+tuple(self.parameters.values()):digest(h)

    def _validate_registered(self,f):
        if f.registry_sha256!=self.registry_sha256:raise ValueError('Wrong registered checkpoint bank')
        m=f.requested_metadata
        if m is not None and (self.versions.get(m.expert_id)!=m or self.checkpoints[m.expert_id]!=f.requested_checkpoint_sha256 or self.parameters[m.expert_id]!=f.requested_parameter_sha256):
            raise ValueError('Real model version/checkpoint/parameter provenance changed')

    def mature(self,f,o):
        if self._phase!='maturing' or type(f) is not BackendForecastV1 or type(o) is not TargetOutcomeV2:
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
            sample=BackendCalibrationScoreV1(f,o,f.era==self.era)
            if sample.accepted_for_current_era:
                key=(f.policy_id,f.policy_version,f.horizon)
                self._buffers.setdefault(key,deque(maxlen=288)).append(sample)
        return sample,tuple(receipts)

    def issue(self,f):
        if type(f) is not BackendForecastV1 or f.origin!=self.now or f.era!=self.era or (f.run_id,f.dataset_id,f.machine_id)!=self._identity:
            raise ValueError('Current validated synthetic issuance required')
        self._validate_registered(f)
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
            r=BackendIntervalRecordV1(f.forecast_id+'-pi'+str(p),f,p,status,support,rank,radius,lo,hi,self.execution_sha256)
            self.intervals[f.forecast_id,p]=r;records.append(r)
        return tuple(records)
