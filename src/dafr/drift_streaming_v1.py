"""M6A parallel monitor on a deterministic persistence reference only."""
from dataclasses import dataclass
from datetime import timedelta

from .contracts_v2 import TickEventV2,ForecastRecordV2,StateEventV2,SupportSnapshotV2,TelemetryResetV2
from .streaming_v2 import StreamingSimulatorV2
from .selector_contracts_v1 import AuditEventV1
from .drift_contracts_v1 import GenuineReferenceErrorV1
from .drift_v1 import PageHinkleyErrorV1,load_drift_config


@dataclass(frozen=True,slots=True)
class ReferenceFailureV1:
    timestamp: object
    horizon: int
    forecast_id: str
    reason: str = 'declared_synthetic_numerical_failure'


@dataclass(frozen=True,slots=True)
class DetectorResetV1:
    timestamp: object
    horizon: int
    previous_era: int
    new_era: int
    cleared_recent_errors: int
    reason: str = 'telemetry_reset_not_workload_drift'


@dataclass(frozen=True,slots=True)
class DriftStepV1:
    tick: TickEventV2
    events: tuple
    decisions: tuple
    outcomes: tuple
    alerts: tuple
    snapshots: tuple
    reset: object


class SyntheticDriftStreamV1(StreamingSimulatorV2):
    def __init__(self,run_id,failure_origins=()):
        config,sha=load_drift_config()
        if type(failure_origins) is not tuple or failure_origins!=tuple(sorted(set(failure_origins))) or any(type(i) is not int or not 0<=i<2304 for i in failure_origins):
            raise ValueError('Immutable prespecified synthetic fault indices required')
        super().__init__(run_id,'synthetic_m6a_v1')
        self.execution_sha256=sha;self.failure_origins=failure_origins
        self.detectors={h:PageHinkleyErrorV1(h,sha,config) for h in (1,12)}

    def advance(self,timestamp,value,missing_reason=None):
        tick=TickEventV2(self.run_id,self.dataset_id,self.machine_id,f'tick-{self._ticks+1}',self._sequence+1,timestamp,value,missing_reason)
        if self._ticks>=2304 or (self._history and timestamp-self._history[-1].timestamp!=timedelta(minutes=5)):
            raise ValueError('Every five-minute tick is required; maximum 2304')
        events=[]
        def emit(kind,record,sequence=None):
            events.append(AuditEventV1(sequence if sequence is not None else self._next_sequence(),kind,record))
        self._next_sequence();self._ticks+=1;self._history.append(tick);emit('tick',tick,tick.sequence)
        if tick.genuine:
            self._last_genuine=tick;self._genuine+=1;self._genuine_streak+=1;self._missing_streak=0
        else:self._genuine_streak=0;self._missing_streak+=1
        outcomes=tuple(self.ledger.resolve(f,tick,self._next_sequence()) for f in self.ledger.pending_at(timestamp))
        for o in outcomes:emit(o.status,o,o.sequence)
        reset=None
        if self._missing_streak==4:
            self._era+=1;reset=TelemetryResetV2(f'reset-{self._era}',self._next_sequence(),timestamp,tick.event_id,self._era-1,self._era)
            emit('telemetry_reset',reset,reset.sequence)
            for b in self._support.values():b.clear()
        for o in outcomes:
            if o.status=='scored':
                key=(o.policy_id,o.policy_version,o.horizon);self._total_scored[key]+=1
                if o.forecast_era==self._era:self._support[key].append(o)
        oldest=timestamp-timedelta(minutes=5*287)
        for b in self._support.values():
            while b and b[0].target<oldest:b.popleft()
        snapshots=[];alerts=[]
        for h,d in self.detectors.items():
            old_era=d.era;old_count=len(d.recent);clock=d.clock(timestamp,self._era);emit('detector_clock',clock)
            if reset:emit('detector_telemetry_reset',DetectorResetV1(timestamp,h,old_era,self._era,old_count))
        for o in outcomes:
            if o.status!='scored':continue
            sample=GenuineReferenceErrorV1(self.ledger._decisions[o.forecast_id],o)
            emit('genuine_reference_error',sample)
            update=self.detectors[o.horizon].observe(sample);snapshots.append(update.snapshot)
            emit('detector_update',update.snapshot)
            for alert in update.alerts:alerts.append(alert);emit(alert.kind,alert)
        context=self._context(tick)
        supports=tuple(SupportSnapshotV2(k[0],k[1],k[2],self._era,len(b),b[-1].target if b else None,b[0].target if b else None,
            len(b)>=100,self._total_scored[k]) for k,b in self._support.items())
        state=StateEventV2(f'state-{self._ticks}',self._next_sequence(),timestamp,tick.event_id,self._ticks,self._genuine,self._era,
            self._genuine_streak,self._missing_streak,context.learned_eligible,context.last_genuine_age_ticks,context.context_sha256,supports)
        emit('state',state,state.sequence);decisions=[]
        for h in (1,12):
            prediction=source=version=None;reason='persistence_reference'
            if self._last_genuine is not None and context.last_genuine_age_ticks<=3:
                prediction=self._last_genuine.value;source='persistence';version='rule_v2';availability='baseline'
            else:availability='abstained';reason='no_genuine_history' if self._last_genuine is None else 'fallback_stale'
            failure=self._ticks-1 in self.failure_origins and prediction is not None
            if failure:
                prediction=source=version=None;availability='abstained';reason='reference_numeric_failure'
            b=self._support[('persistence','rule_v2',h)];seq=self._next_sequence()
            f=ForecastRecordV2(forecast_id=f'forecast-{seq}',run_id=self.run_id,dataset_id=self.dataset_id,machine_id=self.machine_id,
                policy_id='persistence',policy_version='rule_v2',origin=timestamp,target=timestamp+timedelta(minutes=5*h),horizon=h,
                sequence=seq,origin_tick_id=tick.event_id,origin_tick_sequence=tick.sequence,era=self._era,context_sha256=context.context_sha256,
                learned_eligible=context.learned_eligible,availability=availability,selected_expert=source,source_version=version,predicted_value=prediction,
                reason=reason,last_genuine_cutoff=context.last_genuine_cutoff,last_genuine_age_ticks=context.last_genuine_age_ticks,
                support_count=len(b),support_latest_target=b[-1].target if b else None,support_ready=len(b)>=100)
            self.ledger.issue(f,tick,context);decisions.append(f);emit('reference_forecast' if f.issued else 'reference_abstention',f,f.sequence)
            if failure:emit('reference_failure',ReferenceFailureV1(timestamp,h,f.forecast_id))
        return DriftStepV1(tick,tuple(events),tuple(decisions),outcomes,tuple(alerts),tuple(snapshots),reset)
