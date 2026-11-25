"""Typed real-record feedback bridge; frozen M5A choose/reset/age rules reused."""
from .contracts_v2 import TickEventV2,TargetOutcomeV2
from .selector_contracts_v1 import EXPERTS,MatchedLossV1,digest
from .selector_v1 import MatchedSelectorV1
from .adaptive_real_contracts_v1 import BackendForecastV1


class BackendMatchedSelectorV1(MatchedSelectorV1):
    def __init__(self,config,versions,registry_sha256):
        super().__init__(config)
        if type(versions) is not tuple or len(versions)!=2:raise ValueError('Pinned expert versions required')
        digest(registry_sha256)
        self._expected_versions=versions;self._registry_sha256=registry_sha256

    def reveal_feedback(self,tick,era,outcomes,forecasts):
        if type(tick) is not TickEventV2:raise ValueError('Validated arrival required')
        groups={};seen=set()
        for o in outcomes:
            if type(o) is not TargetOutcomeV2 or o.forecast_id not in forecasts:raise ValueError('Known immutable outcome required')
            f=forecasts[o.forecast_id]
            if type(f) is not BackendForecastV1 or f.registry_sha256!=self._registry_sha256:raise ValueError('Wrong record/registry provenance')
            if o.forecast_id in seen:raise ValueError('Duplicate feedback')
            seen.add(o.forecast_id)
            if (o.run_id,o.dataset_id,o.machine_id,o.target,o.tick_id,o.actual)!=(tick.run_id,tick.dataset_id,tick.machine_id,tick.timestamp,tick.event_id,tick.value):
                raise ValueError('Only exact current genuine/missing targets can mature')
            if not f.issued or (f.target,f.origin,f.horizon,f.predicted_value,f.policy_id,f.era,f.sequence,tick.sequence)!=(o.target,o.origin,o.horizon,o.predicted_value,o.policy_id,o.forecast_era,o.issued_sequence,o.arrival_sequence):
                raise ValueError('Outcome differs from immutable issuance')
            if f.requested_metadata is not None:
                m=f.requested_metadata
                if m.version!=self._expected_versions[EXPERTS.index(m.expert_id)]:raise ValueError('Model version changed retrospectively')
            if f.policy_id.startswith('shadow_') and f.availability=='expert' and o.status=='scored':
                key=(f.origin,f.target,f.horizon,f.era,f.context_sha256)
                group=groups.setdefault(key,{})
                if f.source_expert in group:raise ValueError('Duplicate expert loss')
                group[f.source_expert]=(f,o)
        pairs=[]
        for key,group in groups.items():
            if set(group)!=set(EXPERTS):continue
            fs,os=zip(*(group[n] for n in EXPERTS))
            pair=MatchedLossV1(*key,tuple(f.forecast_id for f in fs),tuple(f.source_version for f in fs),tuple(o.absolute_error for o in os))
            if pair.versions!=self._expected_versions:raise ValueError('Unregistered matched versions')
            pairs.append(pair)
        # Advance the original frozen clock/reset/aging state with no mock
        # records. Then add these independently validated current-target pairs.
        # Since every new target equals now, inserting after expiry is exactly
        # equivalent to M5A's insert-then-expire order. No synthetic metadata is
        # forged and the inherited choose() implementation is unchanged.
        super().reveal_feedback(tick,era,(),{})
        for pair in pairs:
            if pair.era==era:self.buffers[pair.horizon].append(pair)
        return tuple(pairs)
