"""One-sided Page-Hinkley-style error monitoring with causal robust scaling."""
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from statistics import median
import hashlib,json

from .contracts_v2 import grid_timestamp
from .selector_contracts_v1 import digest
from .drift_contracts_v1 import GenuineReferenceErrorV1,DriftSnapshotV1,DriftAlertV1,DriftUpdateV1,LABEL

ROOT=Path(__file__).resolve().parents[2]


@dataclass(frozen=True,slots=True)
class DriftConfigV1:
    normalization_samples: int = 32
    minimum_recent_errors: int = 64
    recency_grid_ticks: int = 288
    scale_floor_cpu_points: float = 0.1
    mad_multiplier: float = 1.4826
    normalized_clip: float = 4.0
    delta: float = 0.05
    warning_threshold: float = 4.0
    alarm_threshold: float = 8.0
    cooldown_grid_ticks: int = 24

    def __post_init__(self):
        for name,field in self.__dataclass_fields__.items():
            value=getattr(self,name)
            if type(value) is not type(field.default) or value!=field.default:raise ValueError('Unsupported frozen engineering choice: '+name)


def load_drift_config(path=ROOT/'configs/dafr_m6a_synthetic_v1.json'):
    data=Path(path).read_bytes();c=json.loads(data)
    if c.get('schema_version')!='dafr_m6a_synthetic_v1' or c.get('scope')!='SYNTHETIC_ONLY' or c.get('label')!=LABEL or c.get('synthetic_execution_allowed') is not True:
        raise ValueError('M6A is synthetic-only')
    for flag in ('real_data_execution_allowed','confirmation_execution_allowed','model_refitting_allowed','selector_changes_allowed','prediction_intervals_allowed','m6b_execution_allowed','cpu_level_detector_enabled'):
        if c.get(flag) is not False:raise ValueError('Unauthorized capability: '+flag)
    if (c.get('channel'),c.get('reference_expert'),c.get('reference_version'))!=('one_sided_persistence_absolute_error','persistence','rule_v2'):
        raise ValueError('Fixed reference/channel changed')
    if c['max_grid_ticks']!=2304 or c['maximum_process_rss_bytes']!=4*1024**3:raise ValueError('Resource limit changed')
    return DriftConfigV1(**c['detector']),hashlib.sha256(data).hexdigest()


class PageHinkleyErrorV1:
    """No raw CPU update, fitting API, selector callback or refitting response.

    PH running mean/statistic uses genuine monitor inputs since last alarm or
    support-loss restart. The current-era robust normalization stays fixed.
    Alert eligibility additionally needs 64 genuine targets in 288 grid ticks.
    """
    def __init__(self,horizon,execution_sha256,config=DriftConfigV1()):
        if type(horizon) is not int or horizon not in (1,12) or type(config) is not DriftConfigV1:raise ValueError('Validated detector horizon/config required')
        digest(execution_sha256)
        self.horizon=horizon;self.config=config;self.execution_sha256=execution_sha256
        self.now=None;self.era=0;self.lifetime_errors=0;self.ignored_old_errors=0;self._received=False
        self._identity=None
        self._clear()

    def _clear(self):
        self.recent=deque(maxlen=288);self._normalization=[];self.center=self.scale=None
        self.era_errors=0;self.clips=0;self.warm_clips=0;self.cooldown_until=None;self._anchor=0.
        self._rearm()

    def _rearm(self):
        self.mean=self._anchor;self.weight=32;self.cumulative=0.;self.minimum=0.;self.statistic=0.;self.warning=False

    @property
    def in_cooldown(self):return self.cooldown_until is not None and self.now<self.cooldown_until

    def clock(self,timestamp,era):
        grid_timestamp(timestamp)
        if type(era) is not int or era not in (self.era,self.era+1):raise ValueError('Invalid telemetry era')
        if self.now is not None and timestamp-self.now!=timedelta(minutes=5):raise ValueError('Every five-minute clock tick is required once')
        if era!=self.era:self._clear();self.era=era
        self.now=timestamp;self._received=False
        prior=len(self.recent);oldest=timestamp-timedelta(minutes=5*287)
        while self.recent and self.recent[0]<oldest:self.recent.popleft()
        if prior>=64 and len(self.recent)<64:self._rearm()
        return self.snapshot()

    def snapshot(self,status=None,raw=None,z=None,clipped=False):
        if self.now is None:raise ValueError('Reveal clock before requesting a snapshot')
        if status is None:
            status='cooldown' if self.in_cooldown else 'warming_normalization' if self.center is None else 'warming_support' if len(self.recent)<64 else 'warning' if self.warning else 'normal'
        return DriftSnapshotV1(self.now,self.horizon,self.era,'persistence','rule_v2',status,self.era_errors,self.lifetime_errors,
            len(self.recent),len(self._normalization),self.center,self.scale,raw,z,clipped,self.clips,self.warm_clips,
            self.mean,self.cumulative,self.minimum,self.statistic,self.config.warning_threshold,self.config.alarm_threshold,
            self.warning,self.cooldown_until,self.in_cooldown,self.config.minimum_recent_errors,self.ignored_old_errors,self.execution_sha256)

    def observe(self,sample):
        if type(sample) is not GenuineReferenceErrorV1:raise ValueError('Only validated genuine reference errors accepted')
        f,o=sample.forecast,sample.outcome
        if self.now is None or o.target!=self.now or o.horizon!=self.horizon or f.era>self.era:raise ValueError('Only this exact genuinely arrived target may update its horizon')
        if self._received:raise ValueError('Duplicate error at the same horizon/target')
        identity=(f.run_id,f.dataset_id,f.machine_id)
        if self._identity is not None and identity!=self._identity:raise ValueError('Reference stream identity cannot change')
        self._identity=identity
        self._received=True
        if f.era!=self.era:
            self.ignored_old_errors+=1
            return DriftUpdateV1(self.snapshot('old_era_ignored'))
        raw=o.absolute_error;self.era_errors+=1;self.lifetime_errors+=1;self.recent.append(self.now)
        if self.center is None:
            self._normalization.append(raw)
            if len(self._normalization)==32:
                self.center=median(self._normalization)
                self.scale=max(self.config.mad_multiplier*median(abs(x-self.center) for x in self._normalization),self.config.scale_floor_cpu_points)
                zz=[max(-4.,min(4.,(x-self.center)/self.scale)) for x in self._normalization]
                self.warm_clips=sum(abs((x-self.center)/self.scale)>4 for x in self._normalization)
                self._anchor=sum(zz)/32;self._rearm()
            return DriftUpdateV1(self.snapshot('normalization_frozen' if self.center is not None else 'warming_normalization',raw))
        unbounded=(raw-self.center)/self.scale;z=max(-4.,min(4.,unbounded));clipped=abs(unbounded)>4.
        self.clips+=int(clipped)
        if self.in_cooldown:return DriftUpdateV1(self.snapshot('cooldown',raw,z,clipped))
        self.weight+=1;self.mean+=(z-self.mean)/self.weight
        self.cumulative+=z-self.mean-self.config.delta;self.minimum=min(self.minimum,self.cumulative)
        self.statistic=self.cumulative-self.minimum
        if len(self.recent)<64:
            self.warning=False
            return DriftUpdateV1(self.snapshot('warming_support',raw,z,clipped))
        alerts=[]
        if self.statistic>=8.:
            self.cooldown_until=self.now+timedelta(minutes=5*24)
            alerts.append(DriftAlertV1('statistical_alarm',self.now,'persistence','rule_v2',self.horizon,len(self.recent),self.era_errors,
                self.statistic,8.,self.era,False,self.cooldown_until,f.forecast_id,o.event_id,self.execution_sha256))
            snapshot=self.snapshot('alarm',raw,z,clipped)
            self._rearm()
            return DriftUpdateV1(snapshot,tuple(alerts))
        was_warning=self.warning;self.warning=self.statistic>=4.
        if self.warning and not was_warning:
            alerts.append(DriftAlertV1('warning_entered',self.now,'persistence','rule_v2',self.horizon,len(self.recent),self.era_errors,
                self.statistic,4.,self.era,False,self.cooldown_until,f.forecast_id,o.event_id,self.execution_sha256))
        return DriftUpdateV1(self.snapshot(raw=raw,z=z,clipped=clipped),tuple(alerts))
