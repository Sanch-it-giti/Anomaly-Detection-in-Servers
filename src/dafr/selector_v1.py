"""Bounded matched-loss hard selection. No real-data reader, fit or detector."""
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path

from .selector_contracts_v1 import EXPERTS, MatchedLossV1, SelectionSnapshotV1, SyntheticForecastV1
from .contracts_v2 import TickEventV2, CausalContextV2, TargetOutcomeV2

ROOT=Path(__file__).resolve().parents[2]


@dataclass(frozen=True,slots=True)
class SelectorConfigV1:
    experts: tuple = EXPERTS
    default_expert: str = 'arima'
    horizons: tuple = (1,12)
    max_matched_scores: int = 288
    min_matched_scores: int = 100
    recency_grid_ticks: int = 288
    absolute_improvement_margin: float = 0.1
    relative_improvement_margin: float = 0.05
    minimum_dwell_grid_ticks: int = 24
    tie_tolerance: float = 1e-12

    def __post_init__(self):
        for name,field in self.__dataclass_fields__.items():
            value=getattr(self,name)
            if type(value) is not type(field.default) or value!=field.default:raise ValueError('Unsupported frozen M5A choice: '+name)


def load_selector_config(path=ROOT/'configs/dafr_m5a_synthetic_v1.json'):
    import hashlib
    payload=Path(path).read_bytes();c=json.loads(payload)
    if c.get('schema_version')!='dafr_m5a_synthetic_v1' or c.get('scope')!='SYNTHETIC_ONLY' or c.get('status')!='FROZEN_SYNTHETIC_ENGINEERING_CHOICES_NOT_OPTIMIZED':
        raise ValueError('Wrong M5A execution scope')
    if c.get('synthetic_execution_allowed') is not True or any(c.get(k) is not False for k in
        ('real_data_execution_allowed','confirmation_execution_allowed','m3_training_allowed','m5b_execution_allowed','drift_detection_allowed','prediction_intervals_allowed')):
        raise ValueError('M5A cannot authorize real data, fitting, M5B, drift or intervals')
    values=dict(c['selector']);values['experts']=tuple(values['experts']);values['horizons']=tuple(values['horizons'])
    config=SelectorConfigV1(**values)
    if c['missingness']!={'cadence_seconds':300,'genuine_history_gate':24,'persistence_max_age_ticks':3,'era_reset_missing_tick':4,'imputation_enabled':False,'old_era_scores_seed_active_support':False}:
        raise ValueError('V2 missingness cannot change')
    if type(c['missingness']['imputation_enabled']) is not bool or c['max_grid_ticks_per_run']!=2304 or c['maximum_process_rss_bytes']!=4*1024**3:
        raise ValueError('Resource/missingness guard changed')
    return config,hashlib.sha256(payload).hexdigest()


class MatchedSelectorV1:
    def __init__(self,config=SelectorConfigV1()):
        if type(config) is not SelectorConfigV1:raise ValueError('Frozen selector configuration required')
        self.config=config
        self.buffers={h:deque(maxlen=config.max_matched_scores) for h in config.horizons}
        self.incumbents={h:config.default_expert for h in config.horizons}
        self.last_change={h:None for h in config.horizons}
        self.switches={h:0 for h in config.horizons}
        self.now=None;self.era=0
        self._versions=None
        self._chosen=set();self._missing_streak=0

    def reveal_feedback(self,tick,era,outcomes,forecasts):
        """Call once at arrival, after outcome creation, before expert issuance.

        All input records are checked first. Only two genuine shadow errors
        with identical origin/target/era/context and fixed versions form a pair.
        Old-era scores remain in audit accounting but cannot enter support.
        """
        if type(tick) is not TickEventV2 or type(era) is not int or era not in (self.era,self.era+1):raise ValueError('Invalid feedback clock/era')
        if self.now is not None and tick.timestamp-self.now!=timedelta(minutes=5):raise ValueError('Feedback requires every tick once')
        missing_streak=0 if tick.genuine else self._missing_streak+1
        if era!=self.era+(missing_streak==4):raise ValueError('Reset exactly once on the fourth missing tick')
        groups={};seen=set()
        for outcome in outcomes:
            if type(outcome) is not TargetOutcomeV2:raise ValueError('Validated immutable outcome required')
            f=forecasts[outcome.forecast_id]
            if type(f) is not SyntheticForecastV1:raise ValueError('Validated immutable issuance required')
            if outcome.forecast_id in seen:raise ValueError('Duplicate feedback')
            seen.add(outcome.forecast_id)
            if (outcome.run_id,outcome.dataset_id,outcome.machine_id,outcome.target,outcome.tick_id,outcome.actual)!=(tick.run_id,tick.dataset_id,tick.machine_id,tick.timestamp,tick.event_id,tick.value):
                raise ValueError('Only exact current genuinely arrived targets can mature')
            if not f.issued or (f.target,f.origin,f.horizon,f.predicted_value,f.policy_id,f.era,f.sequence,tick.sequence)!=(outcome.target,outcome.origin,outcome.horizon,outcome.predicted_value,outcome.policy_id,outcome.forecast_era,outcome.issued_sequence,outcome.arrival_sequence):
                raise ValueError('Outcome differs from immutable issuance')
            if f.policy_id.startswith('shadow_') and f.availability=='expert' and outcome.status=='scored':
                key=(f.origin,f.target,f.horizon,f.era,f.context_sha256)
                group=groups.setdefault(key,{})
                if f.source_expert in group:raise ValueError('Duplicate expert loss')
                group[f.source_expert]=(f,outcome)
        pairs=[]
        for key,group in groups.items():
            if set(group)!=set(EXPERTS):continue
            fs,os=zip(*(group[n] for n in EXPERTS))
            pairs.append(MatchedLossV1(key[0],key[1],key[2],key[3],key[4],
                tuple(f.forecast_id for f in fs),tuple(f.source_version for f in fs),tuple(o.absolute_error for o in os)))
        versions=self._versions or (pairs[0].versions if pairs else None)
        if any(pair.versions!=versions for pair in pairs):raise ValueError('Expert versions cannot change within an M5A run')
        reset=era!=self.era
        if reset:
            for h in self.config.horizons:
                self.buffers[h].clear();self.incumbents[h]=self.config.default_expert;self.last_change[h]=tick.timestamp
        self.now=tick.timestamp;self.era=era
        self._versions=versions
        self._chosen.clear();self._missing_streak=missing_streak
        for h in self.config.horizons:
            if self.last_change[h] is None:self.last_change[h]=tick.timestamp
        for pair in pairs:
            if pair.era==era:self.buffers[pair.horizon].append(pair)
        cutoff=tick.timestamp-timedelta(minutes=5*(self.config.recency_grid_ticks-1))
        for buffer in self.buffers.values():
            while buffer and buffer[0].target<cutoff:buffer.popleft()
        return tuple(pairs)

    def choose(self,context,horizon,available):
        if type(context) is not CausalContextV2 or context.origin!=self.now or context.era!=self.era or type(horizon) is not int or horizon not in self.buffers:
            raise ValueError('Selection must follow this tick feedback and current context')
        if type(available) is not frozenset or not available.issubset(EXPERTS):raise ValueError('Explicit validated availability required')
        if horizon in self._chosen:raise ValueError('A horizon decision cannot be revised within its origin')
        buffer=self.buffers[horizon];before=self.incumbents[horizon]
        means=tuple(sum(p.absolute_errors[i] for p in buffer)/len(buffer) for i in range(2)) if buffer else None
        elapsed=int((self.now-self.last_change[horizon]).total_seconds()/300)
        margin=None
        if not context.learned_eligible:reason='history_gate'
        elif before not in available:reason='incumbent_unavailable'
        elif set(available)!=set(EXPERTS):reason='challenger_unavailable'
        elif len(buffer)<self.config.min_matched_scores:reason='insufficient_matched_support'
        else:
            challenger=next(e for e in EXPERTS if e!=before)
            old,new=means[EXPERTS.index(before)],means[EXPERTS.index(challenger)]
            margin=max(self.config.absolute_improvement_margin,self.config.relative_improvement_margin*old)
            gain=old-new
            if abs(gain)<=self.config.tie_tolerance:reason='tie_hold_incumbent'
            elif gain<=0 or gain+self.config.tie_tolerance<margin:reason='hysteresis_hold'
            elif elapsed<self.config.minimum_dwell_grid_ticks:reason='dwell_hold'
            else:
                self.incumbents[horizon]=challenger;self.switches[horizon]+=1
                self.last_change[horizon]=self.now;reason='matched_loss_switch'
        self._chosen.add(horizon)
        return SelectionSnapshotV1(self.now,horizon,self.era,before,self.incumbents[horizon],reason,len(buffer),
            buffer[0].target if buffer else None,buffer[-1].target if buffer else None,means,margin,elapsed,self.switches[horizon])
