"""M7A immutable external interval records; original forecasts stay unchanged."""
from dataclasses import dataclass
from datetime import datetime
from .contracts import finite_number, identifier
from .contracts_v2 import TargetOutcomeV2, grid_timestamp
from .selector_contracts_v1 import SyntheticForecastV1, digest


@dataclass(frozen=True,slots=True)
class CalibrationScoreV1:
    forecast: SyntheticForecastV1
    outcome: TargetOutcomeV2
    accepted_for_current_era: bool

    def __post_init__(self):
        f,o=self.forecast,self.outcome
        if type(f) is not SyntheticForecastV1 or type(o) is not TargetOutcomeV2 or not f.issued or o.status!='scored':
            raise ValueError('Genuine matured issued synthetic policy records required')
        for n in ('forecast_id','run_id','dataset_id','machine_id','policy_id','policy_version','horizon','origin','target','predicted_value'):
            if getattr(f,n)!=getattr(o,n):raise ValueError('Calibration linkage mismatch')
        if f.sequence!=o.issued_sequence or f.era!=o.forecast_era:raise ValueError('Calibration issuance mismatch')
        if type(self.accepted_for_current_era) is not bool:raise ValueError('Boolean era attribution required')


@dataclass(frozen=True,slots=True)
class CalibrationSupportV1:
    policy_id: str
    policy_version: str
    horizon: int
    era: int
    available_at: datetime
    count: int
    oldest_target: datetime | None
    latest_target: datetime | None
    scores_sha256: str
    minimum_support: int = 100
    capacity: int = 288
    recency_grid_ticks: int = 288

    def __post_init__(self):
        identifier(self.policy_id);identifier(self.policy_version);grid_timestamp(self.available_at);digest(self.scores_sha256)
        if type(self.horizon) is not int or self.horizon not in (1,12) or type(self.era) is not int or self.era<0:
            raise ValueError('Invalid horizon/era')
        if type(self.count) is not int or not 0<=self.count<=288:raise ValueError('Invalid calibration count')
        if (self.minimum_support,self.capacity,self.recency_grid_ticks)!=(100,288,288):raise ValueError('Frozen support required')
        if (self.count==0)!=(self.oldest_target is None) or (self.oldest_target is None)!=(self.latest_target is None):
            raise ValueError('Support bounds mismatch')
        if self.count:
            from datetime import timedelta
            for t in (self.oldest_target,self.latest_target):grid_timestamp(t)
            if not self.available_at-timedelta(minutes=5*287)<=self.oldest_target<=self.latest_target<=self.available_at:
                raise ValueError('Future/stale/inverted support')


@dataclass(frozen=True,slots=True)
class IntervalRecordV1:
    interval_id: str
    forecast: SyntheticForecastV1
    nominal_percent: int
    status: str
    support: CalibrationSupportV1
    quantile_rank: int | None
    radius: float | None
    lower: float | None
    upper: float | None
    execution_sha256: str
    clipping: str = 'none_raw_center_preserved'

    def __post_init__(self):
        identifier(self.interval_id);digest(self.execution_sha256)
        f,s=self.forecast,self.support
        if type(f) is not SyntheticForecastV1 or type(s) is not CalibrationSupportV1:raise ValueError('Validated source/support required')
        if (s.policy_id,s.policy_version,s.horizon,s.era,s.available_at)!=(f.policy_id,f.policy_version,f.horizon,f.era,f.origin):
            raise ValueError('Interval support differs from issuance')
        if type(self.nominal_percent) is not int or self.nominal_percent not in (90,95):raise ValueError('Both frozen nominal levels only')
        if self.clipping!='none_raw_center_preserved':raise ValueError('Clipping is disabled')
        if self.status=='available':
            expected=((s.count+1)*self.nominal_percent+99)//100
            if not f.issued or s.count<100 or self.quantile_rank!=expected or expected>s.count:raise ValueError('Unsupported quantile')
            for v in (self.radius,self.lower,self.upper):finite_number(v)
            if self.radius<0 or (self.lower,self.upper)!=(f.predicted_value-self.radius,f.predicted_value+self.radius):
                raise ValueError('Intervals must preserve the raw center')
        elif self.status in ('center_unavailable','insufficient_support','rank_unavailable'):
            if any(v is not None for v in (self.radius,self.lower,self.upper,self.quantile_rank)):raise ValueError('Unavailable bounds must be null')
            if (self.status=='center_unavailable')!= (not f.issued):raise ValueError('Availability mismatch')
            if self.status=='insufficient_support' and s.count>=100:raise ValueError('Sufficient support')
            if self.status=='rank_unavailable' and ((s.count+1)*self.nominal_percent+99)//100<=s.count:raise ValueError('Rank available')
        else:raise ValueError('Unknown interval status')


@dataclass(frozen=True,slots=True)
class IntervalOutcomeV1:
    interval_id: str
    source_outcome_id: str
    forecast_id: str
    target: datetime
    nominal_percent: int
    status: str
    covered: bool | None
    width: float | None
    interval_score: float | None

    def __post_init__(self):
        for v in (self.interval_id,self.source_outcome_id,self.forecast_id):identifier(v)
        grid_timestamp(self.target)
        if self.nominal_percent not in (90,95):raise ValueError('Nominal level invalid')
        if self.status=='scored':
            if type(self.covered) is not bool:raise ValueError('Genuine coverage required')
            for v in (self.width,self.interval_score):
                finite_number(v)
                if v<0:raise ValueError('Negative width/score')
        elif self.status in ('target_unavailable','interval_unavailable'):
            if any(v is not None for v in (self.covered,self.width,self.interval_score)):raise ValueError('No invented coverage')
        else:raise ValueError('Unknown interval outcome status')
