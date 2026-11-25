"""Prespecified deterministic M7A fixtures; no dataset reader or fitting."""
from dataclasses import dataclass
from datetime import timedelta
import math
from .drift_fixtures_v1 import START
from .selector_streaming_v1 import mock_specs
from .adapters_v1 import MockAdapterSpec


@dataclass(frozen=True,slots=True)
class IntervalFixtureV1:
    name: str
    length: int = 360


FIXTURES=tuple(IntervalFixtureV1(n,490 if n=='calibration_expiry' else 60 if n=='insufficient_support' else 360) for n in
    ('stable','growing_variation','shrinking_variation','abrupt_change','isolated_extreme',
     'short_gaps','long_gap_recovery','insufficient_support','numerical_failures','calibration_expiry'))


def fixture_specs(spec):
    if spec not in FIXTURES:raise ValueError('Predefined fixture only')
    if spec.name=='numerical_failures':return mock_specs('gaps_failures')
    if spec.name=='calibration_expiry':
        return tuple(MockAdapterSpec(s.metadata,s.offset_per_step,'forecast_nonfinite',tuple(range(150,450))) for s in mock_specs())
    return mock_specs()


def fixture_events(spec):
    if type(spec) is not IntervalFixtureV1 or spec not in FIXTURES:raise ValueError('Predefined fixture only')
    for i in range(spec.length):
        amplitude=1.
        if spec.name=='growing_variation':amplitude=1.+3.*i/(spec.length-1)
        elif spec.name=='shrinking_variation':amplitude=4.-3.*i/(spec.length-1)
        elif spec.name=='abrupt_change' and i>=180:amplitude=4.
        value=50+amplitude*math.sin(i*.7)
        if spec.name=='isolated_extreme' and i==180:value=90.
        gap=(spec.name=='short_gaps' and i in (150,200,201,202)) or (spec.name=='long_gap_recovery' and (i<4 or 170<=i<178 or i>=354))
        yield START+timedelta(minutes=5*i),None if gap else value,'synthetic_gap' if gap else None
