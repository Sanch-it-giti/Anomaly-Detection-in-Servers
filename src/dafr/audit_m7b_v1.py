"""M7B independent saved-record checks around the frozen M7A replay auditor."""
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from .audit_m7a_v1 import audit_interval_run
from .drift_v1 import load_drift_config,PageHinkleyErrorV1
from .drift_contracts_v1 import GenuineReferenceErrorV1
from .contracts_v2 import ForecastRecordV2,TargetOutcomeV2
from .streaming_v2 import _json_default


def decode(cls,data):
    d=dict(data)
    for k in ('origin','target','last_genuine_cutoff','support_latest_target','training_cutoff','scaling_cutoff','version_available_at'):
        if d.get(k) is not None:d[k]=datetime.fromisoformat(d[k])
    return cls(**d)


def audit_backend_intervals(directory):
    p=Path(directory);base=audit_interval_run(p)
    read=lambda n:[json.loads(s) for s in (p/(n+'.jsonl')).read_text().splitlines()]
    if (p/'source_events.jsonl').read_bytes()!=(p/'legacy_source_events.jsonl').read_bytes():raise ValueError('Legacy point parity failed')
    if (p/'drift_events.jsonl').read_bytes()!=(p/'legacy_drift_events.jsonl').read_bytes():raise ValueError('Legacy drift payload parity failed')
    manifest=json.loads((p/'manifest.json').read_text());pins=manifest['registered_experts']
    forecasts=read('forecasts');fs={f['forecast_id']:f for f in forecasts}
    for f in forecasts:
        if f['registry_sha256']!=manifest['registry_sha256']:raise ValueError('Wrong checkpoint registry')
        m=f['requested_metadata']
        if m is not None:
            pin=pins[m['expert_id']]
            if m['version']!=pin['version'] or f['requested_checkpoint_sha256']!=pin['metadata_sha256'] or f['requested_parameter_sha256']!=pin['parameter_sha256']:
                raise ValueError('Real model provenance changed')
            if f['requested_state_cutoff']>f['origin']:raise ValueError('Future state')
            for k in ('training_cutoff','scaling_cutoff','available_at'):
                if m.get(k) is not None and m[k]>f['origin']:raise ValueError('Future model cutoff')
    grouped={}
    for r in read('intervals'):grouped.setdefault(r['forecast']['forecast_id'],{})[r['nominal_percent']]=r
    nesting=0
    for pair in grouped.values():
        a,b=pair[90],pair[95]
        if a['support']!=b['support'] or a['status']!=b['status']:raise ValueError('Nominal support mismatch')
        if a['status']=='available':
            if not b['lower']<=a['lower']<=a['upper']<=b['upper']:raise ValueError('95/90 nesting violated')
            nesting+=1
    timeline=read('timeline');last=0;by_tick={}
    for e in timeline:
        if e['sequence']!=last+1 or e['integration_sha256']!=manifest['integration_sha256']:raise ValueError('Integration sequence/configuration mismatch')
        last=e['sequence'];by_tick.setdefault(e['timestamp'],[]).append(e)
    for events in by_tick.values():
        kinds=[e['kind'] for e in events]
        first_update=kinds.index('adapter_update')
        for i,k in enumerate(kinds):
            if k in ('calibration_clock','calibration_score','interval_outcome') or k.startswith('monitor_'):
                if i>=first_update:raise ValueError('Support/monitor update after backend update')
            if k=='interval_issuance':
                r=events[i]['record'];fid=r['forecast']['forecast_id']
                if not any(e['kind'] in ('issuance','unissued_attempt') and e['record']['forecast_id']==fid for e in events[:i]):
                    raise ValueError('Interval precedes point decision')
    cfg,sha=load_drift_config();ds={h:PageHinkleyErrorV1(h,sha,cfg) for h in (1,12)}
    pending_update=None;pending_alerts=[];normalized=lambda x:json.loads(json.dumps(x,default=_json_default))
    for e in read('drift_events'):
        k,r=e['kind'],e['record']
        if k=='detector_clock':
            snapshot=ds[r['horizon']].clock(datetime.fromisoformat(r['available_at']),r['telemetry_era'])
            if normalized(asdict(snapshot))!=r:raise ValueError('Drift clock replay mismatch')
        elif k=='reference_error_link':
            if r['original_forecast']!=fs[r['original_forecast']['forecast_id']]:raise ValueError('Reference is not original backend forecast')
            sample=GenuineReferenceErrorV1(decode(ForecastRecordV2,r['sample']['forecast']),decode(TargetOutcomeV2,r['sample']['outcome']))
            update=ds[sample.outcome.horizon].observe(sample);pending_update=normalized(asdict(update.snapshot))
            pending_alerts.extend(normalized(asdict(a)) for a in update.alerts)
        elif k=='detector_update':
            if pending_update!=r:raise ValueError('Drift update replay mismatch')
            pending_update=None
        elif k in ('warning_entered','statistical_alarm'):
            if not pending_alerts or pending_alerts.pop(0)!=r:raise ValueError('Drift alert replay mismatch')
        elif k=='detector_telemetry_reset':
            if normalized(asdict(ds[r['horizon']].snapshot()))!=r:raise ValueError('Drift reset mismatch')
        else:raise ValueError('Unknown drift event')
    if pending_update is not None or pending_alerts:raise ValueError('Missing drift receipt')
    return dict(base,real_provenance_verified=True,nested_95_90_pairs=nesting,
        pre_state_support_chronology=True,legacy_m6b_point_and_drift_payload_parity=True,drift_replayed=True)
