"""Predeclared deterministic CPU fixtures; labels never enter the detector."""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone

START=datetime(2026,1,1,tzinfo=timezone.utc)


@dataclass(frozen=True,slots=True)
class DriftFixtureV1:
    name: str
    length: int = 280
    change_start: int | None = None
    change_kind: str = 'none'
    missing_indices: tuple = ()
    failure_origins: tuple = ()


FIXTURES=(
    DriftFixtureV1('stable_errors'),
    DriftFixtureV1('sustained_error_increase',change_start=160,change_kind='slope_increase'),
    DriftFixtureV1('isolated_outlier'),
    DriftFixtureV1('gradual_change',change_start=160,change_kind='gradual_slope_increase'),
    DriftFixtureV1('abrupt_level_change',change_start=160,change_kind='level_step_error_transient'),
    DriftFixtureV1('missing_observations',missing_indices=(100,150,151,152,200,235,236,237)),
    DriftFixtureV1('four_tick_resets',missing_indices=tuple(range(4))+tuple(range(145,151))+tuple(range(220,224))+tuple(range(276,280))),
    DriftFixtureV1('delayed_h12',length=40),
    DriftFixtureV1('insufficient_support',length=50,change_start=35,change_kind='early_slope_increase'),
    DriftFixtureV1('forecast_failure',failure_origins=(100,101,102)),
    DriftFixtureV1('cooldown_stress',change_start=120,change_kind='slope_increase'),
)


def fixture_events(spec):
    if type(spec) is not DriftFixtureV1 or spec not in FIXTURES:raise ValueError('Only predefined synthetic fixtures')
    value=20.
    for i in range(spec.length):
        increment=.1
        if spec.name=='sustained_error_increase' and i>=160:increment=.5
        if spec.name=='gradual_change' and i>=160:increment=.1+.25*(i-159)/120
        if spec.name=='cooldown_stress' and i>=120:increment=.3
        if spec.name=='insufficient_support' and i>=35:increment=1.
        if i:value+=increment
        observed=value+(10. if spec.name=='abrupt_level_change' and i>=160 else 12. if spec.name=='isolated_outlier' and i==160 else 0.)
        missing=i in spec.missing_indices
        yield START+timedelta(minutes=5*i),None if missing else observed,'synthetic_gap' if missing else None
