"""M7B typed real-backend interval contracts; original M7A contracts untouched.

Validation mirrors the frozen M7A formulas, with actual BackendForecastV1 and
RealVersion provenance. No real forecast is relabelled as a mock.
"""
from dataclasses import dataclass
from .adaptive_real_contracts_v1 import BackendForecastV1
from .contracts_v2 import TargetOutcomeV2
from .contracts import identifier,finite_number
from .selector_contracts_v1 import digest
from .interval_contracts_v1 import CalibrationSupportV1

@dataclass(frozen=True,slots=True)
class BackendCalibrationScoreV1:
    forecast: BackendForecastV1
    outcome: TargetOutcomeV2
    accepted_for_current_era: bool

    def __post_init__(self):
        f,o=self.forecast,self.outcome
        if type(f) is not BackendForecastV1 or type(o) is not TargetOutcomeV2 or not f.issued or o.status!='scored':
            raise ValueError('Genuine matured issued registered backend policy records required')
        for n in ('forecast_id','run_id','dataset_id','machine_id','policy_id','policy_version','horizon','origin','target','predicted_value'):
            if getattr(f,n)!=getattr(o,n):raise ValueError('Calibration linkage mismatch')
        if f.sequence!=o.issued_sequence or f.era!=o.forecast_era:raise ValueError('Calibration issuance mismatch')
        if type(self.accepted_for_current_era) is not bool:raise ValueError('Boolean era attribution required')


@dataclass(frozen=True,slots=True)
class BackendIntervalRecordV1:
    interval_id: str
    forecast: BackendForecastV1
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
        if type(f) is not BackendForecastV1 or type(s) is not CalibrationSupportV1:raise ValueError('Validated source/support required')
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


