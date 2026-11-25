"""Synthetic-only M5A integration; fixed mock experts, no external data path."""
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import hashlib
import json
import resource
import sys
import time

from .adapters_v1 import MockAdapterSpec, ModelVersionV1
from .contracts import identifier
from .contracts_v2 import TickEventV2, TargetOutcomeV2, TelemetryResetV2, StateEventV2, SupportSnapshotV2
from .streaming_adapters_v1 import AdapterStreamingSimulatorV1, AdapterCallEventV1
from .streaming_v2 import _write_json
from .selector_contracts_v1 import SyntheticForecastV1, AuditEventV1, EXPERTS
from .selector_v1 import MatchedSelectorV1, SelectorConfigV1, load_selector_config, ROOT


@dataclass(frozen=True,slots=True)
class TelemetrySelectionResetV1:
    timestamp: datetime
    horizon: int
    era: int
    previous_incumbent: str
    incumbent: str = 'arima'
    reason: str = 'telemetry_default_reset_not_expert_switch'


@dataclass(frozen=True,slots=True)
class SyntheticStepV1:
    tick: TickEventV2
    events: tuple[AuditEventV1,...]
    decisions: tuple[SyntheticForecastV1,...]
    outcomes: tuple[TargetOutcomeV2,...]
    selections: tuple
    matched: tuple
    reset: TelemetryResetV2 | None


class SyntheticLedgerV1:
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
        if type(forecast) is not SyntheticForecastV1 or forecast.forecast_id in self._records or forecast.key in self._keys:
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


def mock_specs(scenario='stable'):
    arima=MockAdapterSpec(ModelVersionV1('arima','m5a_mock_arima_v1','arima'),offset_per_step=0.0,
        fault='forecast_nonfinite' if scenario=='gaps_failures' else 'none',
        fault_ticks=(150,151) if scenario=='gaps_failures' else (),fault_horizon=1)
    xgboost=MockAdapterSpec(ModelVersionV1('xgboost','m5a_mock_xgboost_v1','xgboost'),offset_per_step=0.25,
        fault='forecast_unavailable' if scenario=='gaps_failures' else 'none',
        fault_ticks=(160,) if scenario=='gaps_failures' else (),fault_horizon=12)
    return arima,xgboost


class SelectorStreamingV1(AdapterStreamingSimulatorV1):
    """Uses preserved V2 context/gap primitives and M3A registered mocks only.

    New contracts/ledger are necessary: fixed-policy V2 contracts deliberately
    forbid adaptive source identity. No old validation or module is changed.
    """
    def __init__(self,run_id,specs=None):
        config,sha=load_selector_config()
        specs=mock_specs() if specs is None else specs
        if type(specs) is not tuple or len(specs)!=2 or any(type(s) is not MockAdapterSpec for s in specs) or tuple(s.metadata.expert_id for s in specs)!=EXPERTS or tuple(s.metadata.family for s in specs)!=EXPERTS:
            raise ValueError('M5A accepts exactly two registered ARIMA/XGBoost lifecycle mocks')
        super().__init__(run_id,'synthetic_m5a_v1',specs=specs)
        self.execution_sha256=sha;self.selector=MatchedSelectorV1(config);self.ledger=SyntheticLedgerV1()
        self._support={(p,'m5a_synthetic_v1',h):deque(maxlen=288) for p in ('shadow_arima','shadow_xgboost','adaptive','persistence') for h in (1,12)}

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
            seq=self._next_sequence();emit('adapter_update',AdapterCallEventV1(f'update-{seq}',seq,'update',self._versions[name],timestamp,context.context_sha256,result.status,result.reason,result))
        supports=tuple(SupportSnapshotV2(k[0],k[1],k[2],self._era,len(b),b[-1].target if b else None,
            b[0].target if b else None,len(b)>=100,self._total_scored[k]) for k,b in self._support.items())
        state=StateEventV2(f'state-{self._ticks}',self._next_sequence(),timestamp,tick.event_id,self._ticks,self._genuine,
            self._era,self._genuine_streak,self._missing_streak,context.learned_eligible,context.last_genuine_age_ticks,context.context_sha256,supports)
        emit('state',state)
        decisions=[];shadow={}

        def issue(policy,h,status,predicted,source,reason,metadata=None,selection=None,source_id=None):
            buffer=self._support[(policy,'m5a_synthetic_v1',h)]
            f=SyntheticForecastV1(f'forecast-{self._sequence+1}',self.run_id,self.dataset_id,self.machine_id,policy,
                timestamp,timestamp+timedelta(minutes=5*h),h,self._next_sequence(),tick.sequence,self._era,
                context.context_sha256,self.execution_sha256,context.learned_eligible,status,predicted,
                source[0] if source else None,source[1] if source else None,reason,context.last_genuine_cutoff,
                context.last_genuine_age_ticks,metadata,source_id,selection,len(buffer),buffer[-1].target if buffer else None)
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
                seq=self._next_sequence();emit('shadow_attempt',AdapterCallEventV1(f'attempt-{seq}',seq,'forecast',self._versions[name],timestamp,context.context_sha256,status,reason,result,h))
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
        return SyntheticStepV1(tick,tuple(events),tuple(decisions),outcomes,tuple(selections),matched,reset)


def synthetic_events(scenario):
    lengths={'stable':400,'regime_switch':900,'horizon_divergence':400,'gaps_failures':600}
    if scenario not in lengths:raise ValueError('Unknown built-in synthetic fixture')
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    gaps={0,1,100,*range(200,203),*range(300,306),*range(450,454),*range(590,600)} if scenario=='gaps_failures' else set()
    for i in range(lengths[scenario]):
        value=40.0
        if scenario=='regime_switch' and 250<=i<500:value=40.0+(8 if i%2 else -8)
        if scenario=='horizon_divergence':value=20+0.15*i
        yield start+timedelta(minutes=5*i),None if i in gaps else value,'synthetic_gap' if i in gaps else None


def rss_bytes():
    n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform=='darwin' else n*1024)


def run_synthetic(run_id,scenario,root=ROOT):
    identifier(run_id)
    if scenario not in ('stable','regime_switch','horizon_divergence','gaps_failures'):raise ValueError('Built-in synthetic input only')
    base=Path(root).resolve()/'data/processed/dafr/m5a_synthetic_v1'
    if base.resolve()!=base:raise ValueError('Symlinked output path forbidden')
    base.mkdir(parents=True,exist_ok=True);directory=base/run_id;directory.mkdir(exist_ok=False)
    sim=SelectorStreamingV1(run_id,mock_specs(scenario));start=time.perf_counter();switches=[];resets=[];support=[]
    def write(path,record):
        with path.open('x') as out:_write_json(out,record)
    write(directory/'manifest.json',{'scope':'SYNTHETIC_ONLY','scenario':scenario,'execution_sha256':sim.execution_sha256,
        'confirmation_execution_allowed':False,'training_performed':False,'real_data_read':False,'m5b_execution_allowed':False,
        'mock_specs':[asdict(s) for s in mock_specs(scenario)]})
    completion={'status':'failed'}
    try:
        from contextlib import ExitStack
        with ExitStack() as stack:
            outputs={name:stack.enter_context((directory/(name+'.jsonl')).open('x')) for name in
                ('events','shadow_predictions','policy_predictions','outcomes','matched_losses','selector_states','switches','resets')}
            for row in synthetic_events(scenario):
                if rss_bytes()>4*1024**3:raise MemoryError('4 GiB process RSS guard exceeded')
                step=sim.advance(*row)
                for e in step.events:
                    _write_json(outputs['events'],{'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)})
                    name={'selector_state':'selector_states','expert_switch':'switches','telemetry_reset':'resets','matched_shadow_loss':'matched_losses'}.get(e.kind)
                    if name:_write_json(outputs[name],{'sequence':e.sequence,'record':asdict(e.record)})
                    if e.kind=='expert_switch':switches.append(asdict(e.record))
                    if e.kind=='telemetry_reset':resets.append(asdict(e.record))
                for f in step.decisions:_write_json(outputs['shadow_predictions' if f.policy_id.startswith('shadow_') else 'policy_predictions'],asdict(f))
                for o in step.outcomes:_write_json(outputs['outcomes'],asdict(o))
                for s in step.selections:support.append(s.matched_count)
        rows=[];pending=set(sim.ledger.pending_ids)
        for policy in ('shadow_arima','shadow_xgboost','adaptive','persistence'):
            for h in (1,12):
                ds=[f for f in sim.ledger.decisions if f.policy_id==policy and f.horizon==h]
                os=[o for o in sim.ledger.outcomes if o.policy_id==policy and o.horizon==h]
                counts={status:sum(f.availability==status for f in ds) for status in ('expert','fallback','baseline','abstained','gated','unavailable','numerical_failure')}
                rows.append({'policy':policy,'horizon':h,'decisions':len(ds),**counts,
                    'scored':sum(o.status=='scored' for o in os),'target_unavailable':sum(o.status=='target_unavailable' for o in os),
                    'pending':sum(f.issued and f.forecast_id in pending for f in ds)})
        summary={'scenario':scenario,'grid_ticks':sim._ticks,'genuine_ticks':sim._genuine,'missing_ticks':sim._ticks-sim._genuine,
            'switch_counts':sim.selector.switches,'telemetry_resets':len(resets),'switch_records':switches,
            'selector_final_support':{h:len(b) for h,b in sim.selector.buffers.items()},'maximum_matched_support':max(support),
            'policy_and_shadow_accounting':rows,'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss_bytes(),
            'interpretation':'Synthetic mechanics only; no forecasting advantage or drift detection is established'}
        write(directory/'summary.json',summary);completion={'status':'completed','grid_ticks':sim._ticks}
    except BaseException as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:write(directory/'completion.json',completion)
    return directory


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--scenario',required=True,choices=('stable','regime_switch','horizon_divergence','gaps_failures'))
    args=parser.parse_args();print(run_synthetic(args.run_id,args.scenario))
