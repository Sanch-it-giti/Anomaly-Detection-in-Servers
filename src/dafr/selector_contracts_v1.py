"""New M5A contracts: adaptive provenance without weakening fixed V2 records."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .adapters_v1 import ModelVersionV1
from .contracts import finite_number, identifier, past_cutoff, positive_integer
from .contracts_v2 import grid_timestamp, nonnegative_integer

EXPERTS = ('arima', 'xgboost')


def digest(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Expected a SHA-256 hexadecimal digest')


def horizon(value):
    if type(value) is not int or value not in (1,12):
        raise ValueError('Only exact h=1/h=12 are supported')


@dataclass(frozen=True, slots=True)
class MatchedLossV1:
    origin: datetime
    target: datetime
    horizon: int
    era: int
    context_sha256: str
    forecast_ids: tuple[str,str]
    versions: tuple[str,str]
    absolute_errors: tuple[float,float]

    def __post_init__(self):
        grid_timestamp(self.origin);grid_timestamp(self.target);horizon(self.horizon)
        nonnegative_integer(self.era);digest(self.context_sha256)
        if self.target-self.origin!=timedelta(minutes=5*self.horizon):
            raise ValueError('Matched evidence must have identical exact targets')
        for values in (self.forecast_ids,self.versions,self.absolute_errors):
            if not isinstance(values,tuple) or len(values)!=2:raise ValueError('Two immutable expert entries required')
        if self.forecast_ids[0]==self.forecast_ids[1]:raise ValueError('Distinct shadow forecasts required')
        for name in self.forecast_ids+self.versions:identifier(name)
        for error in self.absolute_errors:
            finite_number(error)
            if error<0:raise ValueError('Absolute loss cannot be negative')


@dataclass(frozen=True, slots=True)
class SelectionSnapshotV1:
    timestamp: datetime
    horizon: int
    era: int
    before: str
    incumbent: str
    reason: str
    matched_count: int
    earliest_target: datetime | None
    latest_target: datetime | None
    mean_absolute_errors: tuple[float,float] | None
    required_improvement: float | None
    dwell_elapsed_ticks: int
    switch_count: int

    def __post_init__(self):
        grid_timestamp(self.timestamp);horizon(self.horizon)
        for n in (self.era,self.matched_count,self.dwell_elapsed_ticks,self.switch_count):nonnegative_integer(n)
        if self.before not in EXPERTS or self.incumbent not in EXPERTS:raise ValueError('Unknown selector expert')
        identifier(self.reason)
        if self.matched_count>288 or (self.matched_count==0)!=(self.latest_target is None):
            raise ValueError('Invalid matched support snapshot')
        if (self.earliest_target is None)!=(self.latest_target is None):raise ValueError('Support bounds disagree')
        for t in (self.earliest_target,self.latest_target):past_cutoff(t,self.timestamp)
        if self.earliest_target is not None and (self.earliest_target>self.latest_target or
                self.timestamp-self.earliest_target>=timedelta(minutes=5*288)):
            raise ValueError('Stale or inverted support')
        if (self.mean_absolute_errors is None)!=(self.matched_count==0):raise ValueError('Missing loss means')
        if self.mean_absolute_errors is not None:
            if type(self.mean_absolute_errors) is not tuple or len(self.mean_absolute_errors)!=2:raise ValueError('Two loss means required')
            for value in self.mean_absolute_errors:
                finite_number(value)
                if value<0:raise ValueError('Loss cannot be negative')
        if self.required_improvement is not None:
            finite_number(self.required_improvement)
            if self.required_improvement<0:raise ValueError('Negative improvement margin')

    @property
    def switched(self):return self.before!=self.incumbent


@dataclass(frozen=True, slots=True)
class SyntheticForecastV1:
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
    requested_metadata: ModelVersionV1 | None = None
    source_shadow_id: str | None = None
    selection: SelectionSnapshotV1 | None = None
    policy_support_count: int = 0
    policy_latest_target: datetime | None = None
    policy_version: str = 'm5a_synthetic_v1'
    interval_status: str = 'not_implemented'
    detector_status: str = 'not_implemented'

    def __post_init__(self):
        for n in (self.forecast_id,self.run_id,self.dataset_id,self.machine_id,self.policy_id,self.policy_version,self.reason):identifier(n)
        if self.dataset_id!='synthetic_m5a_v1' or self.machine_id!='synthetic_machine':raise ValueError('Synthetic scope required')
        grid_timestamp(self.origin);grid_timestamp(self.target);horizon(self.horizon)
        if self.target-self.origin!=timedelta(minutes=5*self.horizon):raise ValueError('Wrong exact forecast target')
        positive_integer(self.sequence);positive_integer(self.origin_tick_sequence)
        if self.sequence<=self.origin_tick_sequence:raise ValueError('Issue must follow revealed origin')
        nonnegative_integer(self.era);digest(self.context_sha256);digest(self.execution_sha256)
        if type(self.learned_eligible) is not bool:raise ValueError('Boolean gate required')
        shadow=self.policy_id in ('shadow_arima','shadow_xgboost')
        if not shadow and self.policy_id not in ('adaptive','persistence'):raise ValueError('Unknown synthetic policy')
        allowed=('expert','gated','unavailable','numerical_failure') if shadow else ('expert','fallback','baseline','abstained')
        if self.availability not in allowed:raise ValueError('Invalid layer availability')
        if self.requested_metadata is not None:
            if type(self.requested_metadata) is not ModelVersionV1:raise ValueError('Only validated mock metadata allowed')
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
            if not self.learned_eligible or self.last_genuine_age_ticks!=0 or self.requested_metadata is None:
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
        if self.interval_status!='not_implemented' or self.detector_status!='not_implemented':raise ValueError('No intervals or drift detectors in M5A')

    @property
    def issued(self):return self.availability in ('expert','baseline','fallback')

    @property
    def key(self):return (self.run_id,self.dataset_id,self.machine_id,self.policy_id,self.origin,self.horizon)


@dataclass(frozen=True, slots=True)
class AuditEventV1:
    sequence: int
    kind: str
    record: object

    def __post_init__(self):
        positive_integer(self.sequence);identifier(self.kind)
