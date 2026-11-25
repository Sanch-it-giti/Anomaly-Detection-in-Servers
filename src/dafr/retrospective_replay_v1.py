"""Causal M5B-2 replay of immutable saved forecasts; no prediction/model API."""
from collections import defaultdict,deque
from dataclasses import dataclass
from datetime import datetime,timedelta
import json

from .contracts import identifier,finite_number
from .contracts_v2 import CausalContextV2
from .selector_contracts_v1 import AuditEventV1,MatchedLossV1,SelectionSnapshotV1
from .selector_v1 import MatchedSelectorV1,SelectorConfigV1
from .retrospective_sources_v1 import (LABEL,SourceRefV1,ReplayInputV1,FrameV1,canonical_sha)


@dataclass(frozen=True,slots=True)
class AdaptiveDecisionV1:
    run_id: str
    machine: str
    decision_id: str
    sequence: int
    origin: datetime
    target: datetime
    horizon: int
    era: int
    context_sha256: str
    availability: str
    predicted_value: float | None
    selected_expert: str | None
    source_version: str | None
    selection: SelectionSnapshotV1
    incumbent_reference: SourceRefV1
    source_reference: SourceRefV1
    execution_sha256: str
    label: str = LABEL

    def __post_init__(self):
        identifier(self.run_id);identifier(self.machine);identifier(self.decision_id)
        if self.label!=LABEL or self.horizon not in (1,12) or self.target!=self.origin+timedelta(minutes=5*self.horizon):raise ValueError('Invalid diagnostic scope/target')
        if self.availability=='abstained':
            if self.predicted_value is not None or self.selected_expert is not None:raise ValueError('Abstention has no prediction')
        elif self.availability in ('expert','fallback'):finite_number(self.predicted_value)
        else:raise ValueError('Unknown adaptive availability')
        if (self.selection.timestamp,self.selection.horizon,self.selection.era)!=(self.origin,self.horizon,self.era):raise ValueError('Selection mismatch')


@dataclass(frozen=True,slots=True)
class AdaptiveOutcomeV1:
    decision_id: str
    sequence: int
    origin: datetime
    target: datetime
    horizon: int
    status: str
    predicted_value: float
    actual: float | None
    signed_error: float | None
    absolute_error: float | None
    squared_error: float | None
    source_reference: SourceRefV1
    source_outcome_id: str
    source_outcome_sequence: int
    label: str = LABEL


@dataclass(frozen=True,slots=True)
class ReplayStateV1:
    timestamp: datetime
    era: int
    learned_eligible: bool
    reset: bool
    context_sha256: str
    expired_by_age: tuple[int,int]
    capacity_evictions: tuple[int,int]
    previous_incumbents: tuple[str,str]


@dataclass(frozen=True,slots=True)
class ReplayStepV1:
    events: tuple[AuditEventV1,...]
    decisions: tuple[AdaptiveDecisionV1,...]
    outcomes: tuple[AdaptiveOutcomeV1,...]
    selections: tuple[SelectionSnapshotV1,...]
    pairs: tuple[MatchedLossV1,...]
    context: CausalContextV2
    state: ReplayStateV1


class RetrospectiveReplayV1:
    def __init__(self,run_id,inputs,execution_sha256):
        identifier(run_id)
        if type(inputs) is not ReplayInputV1 or not inputs.frames or len(inputs.prefix)!=23:raise ValueError('Verified immutable replay input required')
        self.run_id=run_id;self.machine=inputs.machine;self.execution_sha256=execution_sha256
        self._history=deque(inputs.prefix,maxlen=24);self._last_time=inputs.prefix[-1].timestamp
        self._last_genuine=next((x.timestamp for x in reversed(inputs.prefix) if x.genuine),None)
        first=inputs.frames[0];self._era=inputs.initial_era
        self._gs=first.state.genuine_streak-1 if first.tick.genuine else 0
        self._ms=first.state.missing_streak-1 if not first.tick.genuine else 0
        if min(self._gs,self._ms)<0:raise ValueError('Invalid initial source quality state')
        self.selector=MatchedSelectorV1(SelectorConfigV1())
        self.selector.era=self._era;self.selector._missing_streak=self._ms
        self._versions={x.forecast.policy_id:(x.forecast.policy_version,x.checkpoint_sha256) for x in first.forecasts}
        self._pending_source=defaultdict(list);self._pending=defaultdict(list);self._issued={}
        self.decisions=[];self.outcomes=[];self._sequence=0;self._ticks=0

    def _seq(self):self._sequence+=1;return self._sequence

    def advance(self,frame):
        if type(frame) is not FrameV1 or frame.tick.timestamp-self._last_time!=timedelta(minutes=5):raise ValueError('Replay requires each original grid tick once')
        tick=frame.tick
        if tick.machine_id!=self.machine:raise ValueError('Machine identity differs')
        bank={(s.forecast.policy_id,s.forecast.horizon):s for s in frame.forecasts}
        if len(bank)!=6 or set(bank)!={(p,h) for p in ('arima','xgboost','persistence') for h in (1,12)}:raise ValueError('Required original shadow/reference absent')
        for s in frame.forecasts:
            f=s.forecast
            if f.forecast_id in self._issued or s.reference.forecast_id!=f.forecast_id or s.reference.run_id!=f.run_id:raise ValueError('Duplicate/revised source identity')
            if (f.origin,f.run_id,f.dataset_id,f.machine_id,f.origin_tick_id,f.origin_tick_sequence)!=(tick.timestamp,tick.run_id,tick.dataset_id,tick.machine_id,tick.event_id,tick.sequence):raise ValueError('Forecast origin identity differs')
            if (f.policy_version,s.checkpoint_sha256)!=self._versions[f.policy_id]:raise ValueError('Frozen checkpoint/version changed')
        if len({s.forecast.forecast_id for s in frame.forecasts})!=6:raise ValueError('Duplicate source IDs')
        gs=self._gs+1 if tick.genuine else 0;ms=0 if tick.genuine else self._ms+1
        era=self._era+int(ms==4)
        history=(tuple(self._history)+(tick,))[-24:]
        cutoff=tick.timestamp if tick.genuine else self._last_genuine
        age=int((tick.timestamp-cutoff).total_seconds()/300) if cutoff else None
        payload=[era,gs,ms,cutoff.isoformat() if cutoff else None,[[t.timestamp.isoformat(),t.value,t.missing_reason] for t in history]]
        digest=canonical_sha(payload)
        context=CausalContextV2(tick.timestamp,history,era,gs,ms,cutoff,age,digest)
        if (frame.state.era,frame.state.genuine_streak,frame.state.missing_streak,frame.state.learned_eligible,frame.state.context_sha256)!=(era,gs,ms,context.learned_eligible,digest):raise ValueError('Recorded source context cannot be faithfully reconstructed')
        if (frame.reset is not None)!=(ms==4):raise ValueError('Telemetry reset mismatch')
        for s in frame.forecasts:
            f=s.forecast
            if (f.context_sha256,f.era,f.learned_eligible,f.last_genuine_cutoff,f.last_genuine_age_ticks)!=(digest,era,context.learned_eligible,cutoff,age):raise ValueError('Shadow contexts differ from genuine source history')
        pending={s.forecast.forecast_id:s for s in self._pending_source.get(tick.timestamp,())}
        matured={o.forecast_id:o for o in frame.outcomes}
        if len(matured)!=len(frame.outcomes) or set(matured)!=set(pending):raise ValueError('Missing, duplicate, premature or shifted source feedback')
        for fid,o in matured.items():
            f=pending[fid].forecast
            if (o.origin,o.target,o.horizon,o.policy_id,o.policy_version,o.predicted_value,o.forecast_era,o.issued_sequence)!=(f.origin,f.target,f.horizon,f.policy_id,f.policy_version,f.predicted_value,f.era,f.sequence):raise ValueError('Outcome not linked to original immutable prediction')
            if (o.run_id,o.dataset_id,o.machine_id,o.tick_id,o.arrival_sequence,o.actual)!=(tick.run_id,tick.dataset_id,tick.machine_id,tick.event_id,tick.sequence,tick.value):raise ValueError('Outcome must mature at its genuine exact target')
            if o.sequence>=min(s.forecast.sequence for s in frame.forecasts):raise ValueError('Source scoring must precede new issuance')
            if o.status!=('scored' if tick.genuine else 'target_unavailable'):raise ValueError('Missing target cannot have an error')
        # All source validation above precedes causal state mutation.
        events=[]
        def emit(kind,record):events.append(AuditEventV1(self._seq(),kind,record))
        emit('source_tick',tick)
        for o in frame.outcomes:emit('source_'+o.status,o)
        new_outcomes=[]
        for decision in self._pending.pop(tick.timestamp,()):
            o=matured.get(decision.source_reference.forecast_id)
            if o is None:raise ValueError('Adaptive source outcome absent')
            result=AdaptiveOutcomeV1(decision.decision_id,self._sequence+1,decision.origin,decision.target,decision.horizon,
                o.status,decision.predicted_value,o.actual,o.signed_error,o.absolute_error,o.squared_error,
                decision.source_reference,o.event_id,o.sequence)
            emit('adaptive_'+o.status,result);new_outcomes.append(result);self.outcomes.append(result)
        pairs=[];groups={}
        for fid,o in matured.items():
            f=pending[fid].forecast
            if f.policy_id in ('arima','xgboost') and f.availability=='expert' and o.status=='scored':
                groups.setdefault((f.origin,f.target,f.horizon,f.era,f.context_sha256),{})[f.policy_id]=(f,o)
        for key,group in groups.items():
            if set(group)=={'arima','xgboost'}:
                fs,os=zip(*(group[p] for p in ('arima','xgboost')))
                pairs.append(MatchedLossV1(*key,tuple(f.forecast_id for f in fs),tuple(f.source_version for f in fs),tuple(o.absolute_error for o in os)))
        before={h:tuple(b) for h,b in self.selector.buffers.items()};previous=tuple(self.selector.incumbents[h] for h in (1,12))
        self.selector.reveal_feedback(tick,era,(),{})
        if ms==4:emit('telemetry_reset',frame.reset)
        oldest=tick.timestamp-timedelta(minutes=5*287)
        expired=tuple(sum(p.target<oldest for p in before[h]) if ms!=4 else 0 for h in (1,12))
        capacity=[]
        for h in (1,12):
            current=[p for p in pairs if p.horizon==h and p.era==era]
            capacity.append(max(0,len(self.selector.buffers[h])+len(current)-288))
            self.selector.buffers[h].extend(current)
        for pair in pairs:emit('matched_shadow_loss',pair)
        state=ReplayStateV1(tick.timestamp,era,context.learned_eligible,ms==4,digest,expired,tuple(capacity),previous)
        emit('causal_state',state)
        decisions=[];selections=[]
        for h in (1,12):
            available=frozenset(p for p in ('arima','xgboost') if bank[p,h].forecast.availability=='expert')
            selection=self.selector.choose(context,h,available);selections.append(selection);emit('selector_state',selection)
            if selection.switched:emit('expert_switch',selection)
            requested=bank[selection.incumbent,h]
            if requested.forecast.availability=='expert':source=requested;availability='expert'
            else:
                source=bank['persistence',h]
                availability='fallback' if source.forecast.issued else 'abstained'
                if source.forecast.issued and (source.forecast.availability!='baseline' or source.forecast.last_genuine_age_ticks>3):raise ValueError('No valid documented fallback')
            f=source.forecast
            decision=AdaptiveDecisionV1(self.run_id,self.machine,f'adaptive-{self.machine}-{self._ticks+1}-{h}',self._sequence+1,
                tick.timestamp,f.target,h,era,digest,availability,f.predicted_value,f.selected_expert,f.source_version,
                selection,requested.reference,source.reference,self.execution_sha256)
            emit('adaptive_decision',decision);decisions.append(decision);self.decisions.append(decision)
            if availability!='abstained':self._pending[f.target].append(decision)
        for s in frame.forecasts:
            f=s.forecast
            if f.forecast_id in self._issued:raise ValueError('Source forecast revision/duplicate')
            self._issued[f.forecast_id]=s
            if f.issued:self._pending_source[f.target].append(s)
        self._pending_source.pop(tick.timestamp,None)
        self._history=deque(history,maxlen=24);self._last_time=tick.timestamp;self._last_genuine=cutoff
        self._era=era;self._gs=gs;self._ms=ms;self._ticks+=1
        return ReplayStepV1(tuple(events),tuple(decisions),tuple(new_outcomes),tuple(selections),tuple(pairs),context,state)

    @property
    def pending_ids(self):return tuple(d.decision_id for values in self._pending.values() for d in values)
