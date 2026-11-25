"""M7B separate pre-state-update monitoring and interval orchestration.

The point backend advance body is preserved literally apart from trace/hooks.
No source sequence, point center, matching, selection or fitting rule is changed.
"""
from dataclasses import dataclass
from datetime import timedelta
import hashlib,json
from .adaptive_real_streaming_v1 import AdaptiveRealStreamingV1,BackendStepV1
from .adaptive_real_contracts_v1 import BackendForecastV1
from .contracts_v2 import TickEventV2,TelemetryResetV2,StateEventV2,SupportSnapshotV2
from .selector_contracts_v1 import AuditEventV1,EXPERTS
from .selector_streaming_v1 import TelemetrySelectionResetV1
from .real_streaming_v1 import RealCallEvent
from .drift_real_streaming_v1 import BackendReferenceBridgeV1
from .drift_v1 import ROOT,load_drift_config,PageHinkleyErrorV1
from .interval_real_v1 import BackendIntervalsV1


def load_m7b_config():
    raw=(ROOT/'configs/dafr_m7b_synthetic_backend_v1.json').read_bytes();c=json.loads(raw)
    if c['schema_version']!='dafr_m7b_v1' or c['scope']!='SYNTHETIC_REGISTERED_BACKENDS_ONLY':raise ValueError('Synthetic-only M7B scope required')
    for flag in ('confirmation_execution_allowed','real_data_execution_allowed','replay_refitting_allowed','selector_changes_allowed','drift_changes_allowed','interval_retuning_allowed','m8_execution_allowed'):
        if c.get(flag) is not False:raise ValueError('Unauthorized capability: '+flag)
    if c['max_grid_ticks']!=2304 or c['maximum_process_rss_bytes']!=4*1024**3:raise ValueError('Resource limit changed')
    for n,h in c['frozen_sha256'].items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source changed: '+n)
    return c,hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True,slots=True)
class MonitorReceiptV1:
    kind: str
    record: object


@dataclass(frozen=True,slots=True)
class IntegrationEventV1:
    sequence: int
    timestamp: object
    kind: str
    record: object
    integration_sha256: str


@dataclass(frozen=True,slots=True)
class RealIntervalStepV1:
    backend: BackendStepV1
    monitor_events: tuple
    scores: tuple
    intervals: tuple
    interval_outcomes: tuple
    timeline: tuple


class RealIntervalStreamingV1(AdaptiveRealStreamingV1):
    def __init__(self,run_id,registry_reference,intervals_enabled=True):
        if type(intervals_enabled) is not bool:raise ValueError('Boolean interval flag required')
        self.integration_config,self.integration_sha256=load_m7b_config()
        super().__init__(run_id,registry_reference)
        self.intervals_enabled=intervals_enabled
        self.calibrator=BackendIntervalsV1(registry_reference.sha256,self._versions,self._pins,self._parameters)
        config,sha=load_drift_config();self.detectors={h:PageHinkleyErrorV1(h,sha,config) for h in (1,12)}
        self._trace_sequence=0

    def _trace(self,kind,record,timestamp):
        self._trace_sequence+=1
        self._timeline.append(IntegrationEventV1(self._trace_sequence,timestamp,kind,record,self.integration_sha256))

    def _monitor_emit(self,kind,record,timestamp):
        self._monitor.append(MonitorReceiptV1(kind,record));self._trace('monitor_'+kind,record,timestamp)

    def _before_state(self,tick,outcomes,reset):
        if self.intervals_enabled:
            self._trace('calibration_clock',self.calibrator.clock(tick,self._era),tick.timestamp)
        for h,d in self.detectors.items():
            previous=d.era;self._monitor_emit('detector_clock',d.clock(tick.timestamp,self._era),tick.timestamp)
            if d.era!=previous:self._monitor_emit('detector_telemetry_reset',d.snapshot(),tick.timestamp)
        for o in outcomes:
            f=self.ledger._records[o.forecast_id]
            if o.policy_id=='persistence' and o.status=='scored':
                bridge=BackendReferenceBridgeV1.create(f,o);self._monitor_emit('reference_error_link',bridge,tick.timestamp)
                update=self.detectors[o.horizon].observe(bridge.sample)
                self._monitor_emit('detector_update',update.snapshot,tick.timestamp)
                for a in update.alerts:self._monitor_emit(a.kind,a,tick.timestamp)
            if self.intervals_enabled:
                score,receipts=self.calibrator.mature(f,o)
                if score:self._scores.append(score);self._trace('calibration_score',score,tick.timestamp)
                for r in receipts:self._interval_outcomes.append(r);self._trace('interval_outcome',r,tick.timestamp)

    def _on_issuance(self,f):
        if self.intervals_enabled:
            for r in self.calibrator.issue(f):self._intervals.append(r);self._trace('interval_issuance',r,f.origin)

    def advance(self,timestamp,value,missing_reason=None):
        tick=TickEventV2(self.run_id,self.dataset_id,self.machine_id,f'tick-{self._ticks+1}',self._sequence+1,timestamp,value,missing_reason)
        if self._ticks>=2304 or (self._history and timestamp-self._history[-1].timestamp!=timedelta(minutes=5)):
            raise ValueError('Explicit five-minute ticks and maximum 2304 positions required')
        for name in EXPERTS:
            self._validate_adapter(name);self._versions[name].validate_origin(timestamp,first_tick=self._ticks==0)
        events=[]
        self._timeline=[];self._monitor=[];self._intervals=[];self._interval_outcomes=[];self._scores=[]
        def emit(kind,record):
            sequence=getattr(record,'sequence',None)
            if sequence is None:sequence=self._next_sequence()
            events.append(AuditEventV1(sequence,kind,record))
            self._trace(kind,record,timestamp)
        self._next_sequence();self._ticks+=1;self._history.append(tick);emit('tick',tick)
        if tick.genuine:
            self._last_genuine=tick;self._genuine+=1;self._genuine_streak+=1;self._missing_streak=0
        else:self._genuine_streak=0;self._missing_streak+=1
        outcomes=tuple(self.ledger.resolve(f,tick,self._next_sequence()) for f in self.ledger.pending_at(timestamp))
        for o in outcomes:emit(o.status,o)
        reset=None
        previous=dict(self.selector.incumbents)
        if self._missing_streak==4:
            self._era+=1
            reset=TelemetryResetV2(f'reset-{self._era}',self._next_sequence(),timestamp,tick.event_id,self._era-1,self._era)
            emit('telemetry_reset',reset)
            for buffer in self._support.values():buffer.clear()
        matched=self.selector.reveal_feedback(tick,self._era,outcomes,self.ledger._records)
        if reset:
            for h in (1,12):emit('era_default_reset',TelemetrySelectionResetV1(timestamp,h,self._era,previous[h]))
        for pair in matched:emit('matched_shadow_loss',pair)
        for outcome in outcomes:
            if outcome.status=='scored':
                key=(outcome.policy_id,outcome.policy_version,outcome.horizon);self._total_scored[key]+=1
                if outcome.forecast_era==self._era:self._support[key].append(outcome)
        oldest=timestamp-timedelta(minutes=5*287)
        for buffer in self._support.values():
            while buffer and buffer[0].target<oldest:buffer.popleft()
        self._before_state(tick,outcomes,reset)
        context=self._context(tick);updates={}
        for name,adapter in self._adapters.items():
            result=adapter.update(tick,context);self._validate_result(name,result,context,'update');updates[name]=result
            seq=self._next_sequence();emit('adapter_update',RealCallEvent(f'update-{seq}',seq,'update',self._versions[name],timestamp,context.context_sha256,result.status,result.reason,result))
        supports=tuple(SupportSnapshotV2(k[0],k[1],k[2],self._era,len(b),b[-1].target if b else None,
            b[0].target if b else None,len(b)>=100,self._total_scored[k]) for k,b in self._support.items())
        state=StateEventV2(f'state-{self._ticks}',self._next_sequence(),timestamp,tick.event_id,self._ticks,self._genuine,
            self._era,self._genuine_streak,self._missing_streak,context.learned_eligible,context.last_genuine_age_ticks,context.context_sha256,supports)
        emit('state',state)
        decisions=[];shadow={}

        def issue(policy,h,status,predicted,source,reason,metadata=None,selection=None,source_id=None):
            buffer=self._support[(policy,'m5b1_real_backend_v1',h)]
            f=BackendForecastV1(f'forecast-{self._sequence+1}',self.run_id,self.dataset_id,self.machine_id,policy,
                timestamp,timestamp+timedelta(minutes=5*h),h,self._next_sequence(),tick.sequence,self._era,
                context.context_sha256,self.execution_sha256,context.learned_eligible,status,predicted,
                source[0] if source else None,source[1] if source else None,reason,context.last_genuine_cutoff,
                context.last_genuine_age_ticks,metadata,source_id,selection,len(buffer),buffer[-1].target if buffer else None,
                registry_sha256=self.registry_reference.sha256,
                requested_checkpoint_sha256=self._pins[metadata.expert_id]['metadata_sha256'] if metadata else None,
                requested_parameter_sha256=self._parameters[metadata.expert_id] if metadata else None,
                requested_state_sha256=self._adapters[metadata.expert_id].state_sha256 if metadata else None,
                requested_state_cutoff=self._adapters[metadata.expert_id]._state_cutoff if metadata else None)
            self.ledger.issue(f,tick,context);decisions.append(f);emit('issuance' if f.issued else 'unissued_attempt',f)
            self._on_issuance(f)
            return f

        # Every eligible expert is shadowed even when not currently selected.
        for name in EXPERTS:
            adapter=self._adapters[name]
            for h in (1,12):
                result=None
                if updates[name].status!='ok':status,reason=updates[name].status,'adapter_update_failed'
                elif not context.learned_eligible:status,reason='gated','history_gate'
                else:
                    before=adapter.state_sha256;result=adapter.forecast(context,h)
                    self._validate_result(name,result,context,'forecast',h)
                    if adapter.state_sha256!=before:raise ValueError('Forecast mutated causal state')
                    status,reason=result.status,result.reason
                seq=self._next_sequence();emit('shadow_attempt',RealCallEvent(f'attempt-{seq}',seq,'forecast',self._versions[name],timestamp,context.context_sha256,status,reason,result,h))
                shadow[name,h]=issue('shadow_'+name,h,'expert' if status=='ok' else status,
                    result.value if status=='ok' else None,(name,self._versions[name].version) if status=='ok' else None,
                    reason,self._versions[name])
        selections=[]
        for h in (1,12):
            available=frozenset(name for name in EXPERTS if shadow[name,h].availability=='expert')
            selection=self.selector.choose(context,h,available);selections.append(selection);emit('selector_state',selection)
            if selection.switched:emit('expert_switch',selection)
            for policy in ('persistence','adaptive'):
                chosen=shadow[selection.incumbent,h] if policy=='adaptive' else None
                metadata=self._versions[selection.incumbent] if chosen is not None else None
                if chosen is not None and chosen.availability=='expert':
                    issue(policy,h,'expert',chosen.predicted_value,(chosen.source_expert,chosen.source_version),
                        'selected_shadow',metadata,selection,chosen.forecast_id)
                elif self._last_genuine is not None and context.last_genuine_age_ticks<=3:
                    issue(policy,h,'baseline' if policy=='persistence' else 'fallback',self._last_genuine.value,
                        ('persistence','rule_v2'),'persistence_reference' if chosen is None else chosen.reason,metadata,
                        selection if chosen is not None else None)
                else:
                    issue(policy,h,'abstained',None,None,'no_genuine_history' if self._last_genuine is None else 'fallback_stale',
                        metadata,selection if chosen is not None else None)
        backend=BackendStepV1(tick,tuple(events),tuple(decisions),outcomes,tuple(selections),matched,reset)
        return RealIntervalStepV1(backend,tuple(self._monitor),tuple(self._scores),tuple(self._intervals),tuple(self._interval_outcomes),tuple(self._timeline))
