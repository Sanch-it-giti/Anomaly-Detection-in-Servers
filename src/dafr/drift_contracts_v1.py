"""M6A immutable monitoring records, independent of adaptive selection."""
from dataclasses import dataclass
from datetime import datetime
from .contracts_v2 import ForecastRecordV2,TargetOutcomeV2,grid_timestamp
from .contracts import finite_number

LABEL='SYNTHETIC ENGINEERING VERIFICATION ONLY'


@dataclass(frozen=True,slots=True)
class GenuineReferenceErrorV1:
    forecast: ForecastRecordV2
    outcome: TargetOutcomeV2

    def __post_init__(self):
        f,o=self.forecast,self.outcome
        if type(f) is not ForecastRecordV2 or type(o) is not TargetOutcomeV2:raise ValueError('Validated immutable source records required')
        if (f.policy_id,f.policy_version,f.availability,f.selected_expert,f.source_version)!=('persistence','rule_v2','baseline','persistence','rule_v2'):
            raise ValueError('Only the fixed persistence reference may feed this detector')
        if o.status!='scored':raise ValueError('Missing targets never produce a detector sample')
        for name in ('forecast_id','run_id','dataset_id','machine_id','policy_id','policy_version','origin','target','horizon','predicted_value'):
            if getattr(f,name)!=getattr(o,name):raise ValueError('Error differs from original issued reference')
        if f.sequence!=o.issued_sequence or f.era!=o.forecast_era:raise ValueError('Issuance/era mismatch')
        finite_number(o.absolute_error)


@dataclass(frozen=True,slots=True)
class DriftSnapshotV1:
    available_at: datetime
    horizon: int
    telemetry_era: int
    source_expert: str
    source_version: str
    status: str
    era_genuine_errors: int
    lifetime_genuine_errors: int
    recent_genuine_errors: int
    normalization_count: int
    normalization_center: float | None
    normalization_scale: float | None
    raw_absolute_error: float | None
    normalized_input: float | None
    clipped: bool
    clipped_monitor_updates: int
    normalization_clipped_samples: int
    running_mean: float
    cumulative_sum: float
    cumulative_minimum: float
    statistic: float
    warning_threshold: float
    alarm_threshold: float
    warning_active: bool
    cooldown_until: datetime | None
    in_cooldown: bool
    minimum_recent_errors: int
    ignored_old_era_errors: int
    execution_sha256: str
    detector_version: str = 'ph_persistence_error_v1'
    label: str = LABEL


@dataclass(frozen=True,slots=True)
class DriftAlertV1:
    kind: str
    available_at: datetime
    source_expert: str
    source_version: str
    horizon: int
    genuine_support: int
    era_genuine_errors: int
    statistic: float
    threshold: float
    telemetry_era: int
    cooldown_active_before: bool
    cooldown_until: datetime | None
    source_forecast_id: str
    source_outcome_id: str
    execution_sha256: str
    interpretation: str = 'Reference forecasting-error change; not proven concept drift'
    label: str = LABEL


@dataclass(frozen=True,slots=True)
class DriftUpdateV1:
    snapshot: DriftSnapshotV1
    alerts: tuple[DriftAlertV1,...] = ()
