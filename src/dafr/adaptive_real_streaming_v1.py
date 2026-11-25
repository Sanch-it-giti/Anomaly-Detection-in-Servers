"""M5B-1 fixed real-backend adaptive integration; synthetic admission only."""
from collections import defaultdict,deque
from dataclasses import dataclass
from datetime import timedelta

from .contracts_v2 import TickEventV2,TargetOutcomeV2,TelemetryResetV2,StateEventV2,SupportSnapshotV2
from .selector_contracts_v1 import AuditEventV1,EXPERTS
from .selector_streaming_v1 import TelemetrySelectionResetV1
from .streaming_v2 import StreamingSimulatorV2
from .real_streaming_v1 import RealStreamingSimulator,RealCallEvent
from .adaptive_real_contracts_v1 import BackendForecastV1
from .adaptive_real_feedback_v1 import BackendMatchedSelectorV1
from .adaptive_checkpoint_registry_v1 import load_integration_config,load_fixture_bank,RegistryReferenceV1
from .development_qualification_v1 import EPOCH


@dataclass(frozen=True,slots=True)
class BackendStepV1:
    tick: TickEventV2
    events: tuple
    decisions: tuple
    outcomes: tuple
    selections: tuple
    matched: tuple
    reset: TelemetryResetV2 | None


class BackendLedgerV1:
    def __init__(self):
        self._records={};self._keys=set();self._pending=defaultdict(list);self._outcomes={};self._sequence=0

    @property
    def decisions(self):return tuple(self._records.values())
    @property
    def outcomes(self):return tuple(self._outcomes.values())
    @property
    def pending_ids(self):return tuple(f.forecast_id for f in self.decisions if f.issued and f.forecast_id not in self._outcomes)

    def pending_at(self,timestamp):return tuple(self._records[key] for key in self._pending.get(timestamp,()))

    def issue(self,forecast,tick,context):
        if type(forecast) is not BackendForecastV1 or forecast.forecast_id in self._records or forecast.key in self._keys:
            raise ValueError('Invalid or duplicate synthetic issuance')
        if forecast.sequence<=self._sequence or (forecast.run_id,forecast.dataset_id,forecast.machine_id,forecast.origin,forecast.origin_tick_sequence)!=(tick.run_id,tick.dataset_id,tick.machine_id,tick.timestamp,tick.sequence):
            raise ValueError('Issuance clock/identity mismatch')
        if (context.origin,context.context_sha256,context.era,context.learned_eligible,context.last_genuine_cutoff,context.last_genuine_age_ticks)!=(forecast.origin,forecast.context_sha256,forecast.era,forecast.learned_eligible,forecast.last_genuine_cutoff,forecast.last_genuine_age_ticks):
            raise ValueError('Issuance causal context mismatch')
        if forecast.source_shadow_id is not None:
            source=self._records.get(forecast.source_shadow_id)
            if source is None or source.policy_id!='shadow_'+forecast.source_expert or source.availability!='expert' or (
                source.origin,source.target,source.horizon,source.context_sha256,source.predicted_value,source.source_version)!=(
                forecast.origin,forecast.target,forecast.horizon,forecast.context_sha256,forecast.predicted_value,forecast.source_version):
                raise ValueError('Adaptive center must copy its exact immutable shadow')
        self._records[forecast.forecast_id]=forecast;self._keys.add(forecast.key);self._sequence=forecast.sequence
        if forecast.issued:self._pending[forecast.target].append(forecast.forecast_id)

    def resolve(self,f,tick,sequence):
        if self._records.get(f.forecast_id)!=f or not f.issued or f.forecast_id in self._outcomes or f.target!=tick.timestamp:
            raise ValueError('Unknown, revised, unissued, shifted or already resolved target')
        if (f.run_id,f.dataset_id,f.machine_id)!=(tick.run_id,tick.dataset_id,tick.machine_id) or sequence<=self._sequence:
            raise ValueError('Outcome identity/clock mismatch')
        error=tick.value-f.predicted_value if tick.genuine else None
        outcome=TargetOutcomeV2(f'outcome-{sequence}',sequence,f.forecast_id,tick.event_id,f.run_id,f.dataset_id,f.machine_id,
            f.policy_id,f.policy_version,f.horizon,f.origin,f.target,f.sequence,tick.sequence,f.era,
            'scored' if tick.genuine else 'target_unavailable',f.predicted_value,tick.value,
            error,abs(error) if error is not None else None,error*error if error is not None else None)
        self._outcomes[f.forecast_id]=outcome;self._pending[f.target].remove(f.forecast_id)
        if not self._pending[f.target]:del self._pending[f.target]
        self._sequence=sequence
        return outcome



class AdaptiveRealStreamingV1(StreamingSimulatorV2):
    _validate_adapter=RealStreamingSimulator._validate_adapter
    _validate_result=RealStreamingSimulator._validate_result

    def __init__(self,run_id,registry_reference):
        config,selector_config,sha=load_integration_config()
        adapters,pins,registry,fit_values=load_fixture_bank(registry_reference)
        super().__init__(run_id,'synthetic_m5b1_v1','synthetic')
        self.execution_sha256=sha;self.registry_reference=registry_reference
        self._adapters=adapters;self._pins=pins
        self._versions={n:a.metadata for n,a in adapters.items()}
        self._parameters={n:a.parameter_sha256 for n,a in adapters.items()}
        self.selector=BackendMatchedSelectorV1(selector_config,tuple(self._versions[n].version for n in EXPERTS),registry_reference.sha256)
        self.ledger=BackendLedgerV1()
        self._support={(p,'m5b1_real_backend_v1',h):deque(maxlen=288) for p in ('shadow_arima','shadow_xgboost','adaptive','persistence') for h in (1,12)}
        for i,value in enumerate(fit_values):
            tick=TickEventV2(run_id,self.dataset_id,self.machine_id,f'fit-{i}',i+1,EPOCH+timedelta(minutes=5*(i+1)),value)
            self._last_genuine=tick;self._genuine_streak+=1
            if i>=len(fit_values)-23:self._history.append(tick)
        self._sequence=len(fit_values)
        for adapter in adapters.values():adapter.bootstrap(tuple(self._history))
        if any(a.metadata.available_at!=self._history[-1].timestamp for a in adapters.values()):raise ValueError('Bootstrap/checkpoint cutoff mismatch')
        # No model update is called on fitted observations; parameters/state
        # reconstruction happens once inside the original registered factory.

    def advance(self,timestamp,value,missing_reason=None):
        tick=TickEventV2(self.run_id,self.dataset_id,self.machine_id,f'tick-{self._ticks+1}',self._sequence+1,timestamp,value,missing_reason)
        if self._ticks>=2304 or (self._history and timestamp-self._history[-1].timestamp!=timedelta(minutes=5)):
            raise ValueError('Explicit five-minute ticks and maximum 2304 positions required')
        for name in EXPERTS:
            self._validate_adapter(name);self._versions[name].validate_origin(timestamp,first_tick=self._ticks==0)
        events=[]
        def emit(kind,record):
            sequence=getattr(record,'sequence',None)
            if sequence is None:sequence=self._next_sequence()
            events.append(AuditEventV1(sequence,kind,record))
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
        return BackendStepV1(tick,tuple(events),tuple(decisions),outcomes,tuple(selections),matched,reset)
