"""Read-only M6B monitoring beside registered synthetic real backends.

The backend completes issuance before monitoring. No monitor response is passed
back to the backend. Persistence records are projected, never relabelled in place.
"""
from dataclasses import dataclass, replace
import hashlib
import json

from .adaptive_real_streaming_v1 import AdaptiveRealStreamingV1
from .adaptive_real_contracts_v1 import BackendForecastV1
from .contracts_v2 import ForecastRecordV2, TargetOutcomeV2
from .drift_contracts_v1 import GenuineReferenceErrorV1
from .drift_v1 import ROOT, load_drift_config, PageHinkleyErrorV1


def load_m6b_config():
    raw=(ROOT/'configs/dafr_m6b_synthetic_backend_v1.json').read_bytes()
    c=json.loads(raw)
    if c['scope']!='SYNTHETIC_REGISTERED_BACKENDS_ONLY' or c['schema_version']!='dafr_m6b_v1':
        raise ValueError('Synthetic M6B scope required')
    for key in ('confirmation_execution_allowed','real_data_execution_allowed',
                'model_refitting_during_replay_allowed','detector_response_allowed',
                'prediction_intervals_allowed','selector_changes_allowed'):
        if c.get(key) is not False:raise ValueError('Unauthorized M6B capability: '+key)
    for name,expected in c['frozen_source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen source changed: '+name)
    return c,hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True,slots=True)
class BackendReferenceBridgeV1:
    """Original backend records plus strictly checked M6A-compatible view."""
    original_forecast: BackendForecastV1
    original_outcome: TargetOutcomeV2
    sample: GenuineReferenceErrorV1

    @classmethod
    def create(cls,f,o):
        if type(f) is not BackendForecastV1 or type(o) is not TargetOutcomeV2:
            raise ValueError('Exact validated backend records required')
        if (f.policy_id,f.policy_version,f.availability,f.source_expert,f.source_version)!=(
                'persistence','m5b1_real_backend_v1','baseline','persistence','rule_v2'):
            raise ValueError('Expert/adaptive/fallback errors cannot be reference inputs')
        for name in ('forecast_id','run_id','dataset_id','machine_id','policy_id','policy_version',
                     'origin','target','horizon','predicted_value'):
            if getattr(f,name)!=getattr(o,name):raise ValueError('Backend reference link mismatch')
        if f.sequence!=o.issued_sequence or f.era!=o.forecast_era or o.status!='scored':
            raise ValueError('Genuine exact-target backend outcome required')
        view=ForecastRecordV2(forecast_id=f.forecast_id,run_id=f.run_id,dataset_id=f.dataset_id,
            machine_id=f.machine_id,policy_id='persistence',policy_version='rule_v2',
            origin=f.origin,target=f.target,horizon=f.horizon,sequence=f.sequence,
            origin_tick_id='backend-sequence-'+str(f.origin_tick_sequence),origin_tick_sequence=f.origin_tick_sequence,
            era=f.era,context_sha256=f.context_sha256,learned_eligible=f.learned_eligible,
            availability='baseline',selected_expert='persistence',source_version='rule_v2',
            predicted_value=f.predicted_value,reason=f.reason,last_genuine_cutoff=f.last_genuine_cutoff,
            last_genuine_age_ticks=f.last_genuine_age_ticks)
        # The envelope version identifies the integration layer; rule_v2 is the
        # unchanged actual reference algorithm. Original envelopes remain saved.
        sample=GenuineReferenceErrorV1(view,replace(o,policy_version='rule_v2'))
        return cls(f,o,sample)


@dataclass(frozen=True,slots=True)
class BackendMonitorEventV1:
    sequence: int
    kind: str
    record: object
    backend_barrier_sequence: int
    m6b_configuration_sha256: str


@dataclass(frozen=True,slots=True)
class BackendDriftStepV1:
    backend: object
    monitor_events: tuple


class RealBackendDriftStreamV1:
    """Accepts only the existing synthetic registry factory, never models/data."""
    def __init__(self,run_id,registry_reference,monitoring_enabled=True):
        if type(monitoring_enabled) is not bool:raise ValueError('Boolean monitoring flag required')
        self.configuration,self.configuration_sha256=load_m6b_config()
        self.backend=AdaptiveRealStreamingV1(run_id,registry_reference)
        config,sha=load_drift_config()
        self.detectors={h:PageHinkleyErrorV1(h,sha,config) for h in (1,12)}
        self.monitoring_enabled=monitoring_enabled;self._monitor_sequence=0

    def advance(self,timestamp,value,missing_reason=None):
        step=self.backend.advance(timestamp,value,missing_reason)
        if not self.monitoring_enabled:return BackendDriftStepV1(step,())
        barrier=max(e.sequence for e in step.events);events=[]
        def emit(kind,record):
            self._monitor_sequence+=1
            events.append(BackendMonitorEventV1(self._monitor_sequence,kind,record,
                barrier,self.configuration_sha256))
        for h,d in self.detectors.items():
            previous=d.era
            emit('detector_clock',d.clock(timestamp,self.backend._era))
            if previous!=d.era:emit('detector_telemetry_reset',d.snapshot())
        for outcome in step.outcomes:
            if outcome.policy_id!='persistence' or outcome.status!='scored':continue
            f=self.backend.ledger._records[outcome.forecast_id]
            bridge=BackendReferenceBridgeV1.create(f,outcome)
            emit('reference_error_link',bridge)
            update=self.detectors[outcome.horizon].observe(bridge.sample)
            emit('detector_update',update.snapshot)
            for alert in update.alerts:emit(alert.kind,alert)
        return BackendDriftStepV1(step,tuple(events))
