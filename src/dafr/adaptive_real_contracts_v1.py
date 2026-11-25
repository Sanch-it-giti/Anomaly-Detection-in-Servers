"""Immutable real-backend adaptive records. Frozen M5A contracts are untouched."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from .real_adapters_v1 import RealVersion
from .selector_contracts_v1 import digest,horizon,SelectionSnapshotV1
from .contracts import identifier,finite_number,past_cutoff,positive_integer
from .contracts_v2 import grid_timestamp,nonnegative_integer

@dataclass(frozen=True, slots=True)
class BackendForecastV1:
    forecast_id: str
    run_id: str
    dataset_id: str
    machine_id: str
    policy_id: str
    origin: datetime
    target: datetime
    horizon: int
    sequence: int
    origin_tick_sequence: int
    era: int
    context_sha256: str
    execution_sha256: str
    learned_eligible: bool
    availability: str
    predicted_value: float | None
    source_expert: str | None
    source_version: str | None
    reason: str
    last_genuine_cutoff: datetime | None
    last_genuine_age_ticks: int | None
    requested_metadata: RealVersion | None = None
    source_shadow_id: str | None = None
    selection: SelectionSnapshotV1 | None = None
    policy_support_count: int = 0
    policy_latest_target: datetime | None = None
    policy_version: str = 'm5b1_real_backend_v1'
    interval_status: str = 'not_implemented'
    detector_status: str = 'not_implemented'
    registry_sha256: str = ''
    requested_checkpoint_sha256: str | None = None
    requested_parameter_sha256: str | None = None
    requested_state_sha256: str | None = None
    requested_state_cutoff: datetime | None = None

    def __post_init__(self):
        for n in (self.forecast_id,self.run_id,self.dataset_id,self.machine_id,self.policy_id,self.policy_version,self.reason):identifier(n)
        if self.dataset_id!='synthetic_m5b1_v1' or self.machine_id!='synthetic':raise ValueError('Synthetic scope required')
        grid_timestamp(self.origin);grid_timestamp(self.target);horizon(self.horizon)
        if self.target-self.origin!=timedelta(minutes=5*self.horizon):raise ValueError('Wrong exact forecast target')
        positive_integer(self.sequence);positive_integer(self.origin_tick_sequence)
        if self.sequence<=self.origin_tick_sequence:raise ValueError('Issue must follow revealed origin')
        nonnegative_integer(self.era);digest(self.context_sha256);digest(self.execution_sha256)
        if type(self.learned_eligible) is not bool:raise ValueError('Boolean gate required')
        digest(self.registry_sha256)
        if self.requested_metadata is not None:
            for h in (self.requested_checkpoint_sha256,self.requested_parameter_sha256,self.requested_state_sha256):digest(h)
            if self.requested_state_cutoff is None:raise ValueError('Requested state cutoff required')
            grid_timestamp(self.requested_state_cutoff);past_cutoff(self.requested_state_cutoff,self.origin)
            if self.requested_metadata.machine_id!=self.machine_id:raise ValueError('Checkpoint machine identity mismatch')
        elif any(x is not None for x in (self.requested_checkpoint_sha256,self.requested_parameter_sha256,self.requested_state_sha256,self.requested_state_cutoff)):
            raise ValueError('Persistence has no requested fitted checkpoint')
        shadow=self.policy_id in ('shadow_arima','shadow_xgboost')
        if not shadow and self.policy_id not in ('adaptive','persistence'):raise ValueError('Unknown synthetic policy')
        allowed=('expert','gated','unavailable','numerical_failure') if shadow else ('expert','fallback','baseline','abstained')
        if self.availability not in allowed:raise ValueError('Invalid layer availability')
        if self.requested_metadata is not None:
            if type(self.requested_metadata) is not RealVersion:raise ValueError('Only registered real-backend metadata allowed')
            self.requested_metadata.validate_origin(self.origin)
        if shadow and (self.requested_metadata is None or self.policy_id!='shadow_'+self.requested_metadata.expert_id):
            raise ValueError('Shadow metadata mismatch')
        if self.policy_id=='adaptive':
            if type(self.selection) is not SelectionSnapshotV1 or (self.selection.timestamp,self.selection.horizon,self.selection.era)!=(self.origin,self.horizon,self.era):
                raise ValueError('Adaptive issuance requires current causal selection provenance')
            if self.requested_metadata is None or self.requested_metadata.expert_id!=self.selection.incumbent:
                raise ValueError('Requested incumbent metadata mismatch')
        elif self.selection is not None:raise ValueError('Only adaptive policy owns selection provenance')
        if self.last_genuine_cutoff is None:
            if self.last_genuine_age_ticks is not None:raise ValueError('Input age mismatch')
        else:
            grid_timestamp(self.last_genuine_cutoff);past_cutoff(self.last_genuine_cutoff,self.origin)
            nonnegative_integer(self.last_genuine_age_ticks)
            if self.origin-self.last_genuine_cutoff!=timedelta(minutes=5*self.last_genuine_age_ticks):raise ValueError('Incorrect elapsed age')
        if self.issued:
            finite_number(self.predicted_value);identifier(self.source_expert);identifier(self.source_version)
            if self.last_genuine_cutoff is None:raise ValueError('Prediction needs genuine history')
        elif any(v is not None for v in (self.predicted_value,self.source_expert,self.source_version,self.source_shadow_id)):
            raise ValueError('Unissued attempts cannot invent predictions')
        if self.availability=='expert':
            if not self.learned_eligible or self.last_genuine_age_ticks!=0 or self.requested_metadata is None or self.requested_state_cutoff!=self.origin:
                raise ValueError('Expert requires shared genuine gate and metadata')
            if (self.source_expert,self.source_version)!=(self.requested_metadata.expert_id,self.requested_metadata.version):
                raise ValueError('Expert source identity mismatch')
            if self.policy_id=='adaptive' and self.source_shadow_id is None:raise ValueError('Adaptive expert center must link shadow record')
        elif self.availability in ('fallback','baseline'):
            if self.source_expert!='persistence' or self.source_version!='rule_v2' or self.last_genuine_age_ticks>3:
                raise ValueError('Fallback must be age-three persistence')
            if (self.availability=='baseline')!=(self.policy_id=='persistence'):raise ValueError('Baseline attribution mismatch')
            if self.source_shadow_id is not None:raise ValueError('Fallback is not an expert shadow forecast')
        if self.source_shadow_id is not None:identifier(self.source_shadow_id)
        nonnegative_integer(self.policy_support_count)
        if self.policy_support_count>288 or (self.policy_support_count==0)!=(self.policy_latest_target is None):raise ValueError('Policy support mismatch')
        past_cutoff(self.policy_latest_target,self.origin)
        if self.policy_latest_target is not None and self.origin-self.policy_latest_target>=timedelta(minutes=5*288):
            raise ValueError('Policy support has expired')
        if self.interval_status!='not_implemented' or self.detector_status!='not_implemented':raise ValueError('No intervals or drift detectors in M5B-1')

    @property
    def issued(self):return self.availability in ('expert','baseline','fallback')

    @property
    def key(self):return (self.run_id,self.dataset_id,self.machine_id,self.policy_id,self.origin,self.horizon)
