"""M7A external intervals beside unchanged mock selector and drift source."""
from dataclasses import dataclass
from .selector_streaming_v1 import SelectorStreamingV1
from .drift_streaming_v1 import SyntheticDriftStreamV1
from .interval_v1 import RollingIntervalsV1


@dataclass(frozen=True,slots=True)
class IntervalStepV1:
    source: object
    drift: object
    calibration_clock: object
    scores: tuple
    intervals: tuple
    interval_outcomes: tuple


class SyntheticIntervalStreamV1:
    def __init__(self,run_id,specs=None,enabled=True):
        if type(enabled) is not bool:raise ValueError('Boolean interval switch required')
        self.source=SelectorStreamingV1(run_id,specs)
        self.drift=SyntheticDriftStreamV1(run_id)
        self.engine=RollingIntervalsV1();self.enabled=enabled

    def advance(self,timestamp,value,missing_reason=None):
        source=self.source.advance(timestamp,value,missing_reason)
        drift=self.drift.advance(timestamp,value,missing_reason)
        if not self.enabled:return IntervalStepV1(source,drift,None,(),(),())
        clock=self.engine.clock(source.tick,self.source._era)
        scores=[];outcomes=[];intervals=[]
        for o in source.outcomes:
            f=self.source.ledger._records[o.forecast_id]
            score,receipts=self.engine.mature(f,o)
            if score:scores.append(score)
            outcomes.extend(receipts)
        for f in source.decisions:intervals.extend(self.engine.issue(f))
        return IntervalStepV1(source,drift,clock,tuple(scores),tuple(intervals),tuple(outcomes))
