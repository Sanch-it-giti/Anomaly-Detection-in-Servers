"""Read only pinned, previously saved M4A JSON artifacts. No dataset loader."""
from dataclasses import dataclass,fields
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path

from .contracts_v2 import (TickEventV2,ForecastRecordV2,TargetOutcomeV2,StateEventV2,
    SupportSnapshotV2,TelemetryResetV2)
from .selector_v1 import ROOT,load_selector_config

LABEL='RETROSPECTIVE DEVELOPMENT DIAGNOSTIC'
MACHINES=('m_505','m_1426','m_3028')
EPOCH=datetime.fromisoformat('2000-01-01T00:00:00+00:00')


def sha_bytes(data):return hashlib.sha256(data).hexdigest()


def canonical_sha(value):
    return sha_bytes(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode())


def load_config(root=ROOT):
    root=Path(root);data=(root/'configs/dafr_m5b2_retrospective_v1.json').read_bytes();c=json.loads(data)
    if c.get('schema_version')!='dafr_m5b2_retrospective_v1' or c.get('label')!=LABEL or c.get('retrospective_execution_allowed') is not True:
        raise ValueError('Wrong retrospective execution scope')
    for key in ('confirmation_execution_allowed','new_observation_access_allowed','training_allowed','m6_execution_allowed','m7_execution_allowed','m8_execution_allowed'):
        if c.get(key) is not False:raise ValueError('Unauthorized execution: '+key)
    old=(root/'configs/dafr_m5a_synthetic_v1.json').read_bytes();original=json.loads(old)
    if sha_bytes(old)!=c['m5a_config_sha256'] or c['selector']!=original['selector'] or c['missingness']!=original['missingness']:
        raise ValueError('Frozen selector/missingness changed')
    if c['machines']!=list(MACHINES) or c['origin_indices']!=[1152,1612] or c['logical_adaptive_design_available_after_index']!=1611:
        raise ValueError('Unauthorized machines/origins')
    if c['source_directory']!='data/processed/dafr/m4a_development_v1/m4a-development-20261031-001':raise ValueError('Source redirection')
    if c['m4a_inventory_path']!='reports/dafr/m4a_v1/m4a-development-20261031-001/final_artifact_hashes.json':raise ValueError('Inventory redirection')
    if c['maximum_process_rss_bytes']!=4*1024**3:raise ValueError('Memory guard changed')
    selector,_=load_selector_config()
    return c,selector,sha_bytes(data)


def decode(cls,record):
    """Convert only explicitly declared timestamp fields; reject unknown data."""
    data=dict(record)
    dates={'timestamp','origin','target','last_genuine_cutoff','support_latest_target',
        'training_cutoff','scaling_cutoff','version_available_at','earliest_target','latest_target'}
    for name in dates & data.keys():
        if data[name] is not None:data[name]=datetime.fromisoformat(data[name])
    if cls is StateEventV2:data['support']=tuple(decode(SupportSnapshotV2,s) for s in data['support'])
    return cls(**data)


@dataclass(frozen=True,slots=True)
class SourceRefV1:
    path: str
    line: int
    run_id: str
    forecast_id: str
    record_sha256: str

    def __post_init__(self):
        from .selector_contracts_v1 import digest
        from .contracts import identifier,positive_integer
        identifier(self.run_id);identifier(self.forecast_id);positive_integer(self.line);digest(self.record_sha256)
        if not self.path or Path(self.path).is_absolute() or '..' in Path(self.path).parts:raise ValueError('Invalid source reference path')


@dataclass(frozen=True,slots=True)
class SavedForecastV1:
    forecast: ForecastRecordV2
    reference: SourceRefV1
    checkpoint_sha256: str | None
    execution_sha256: str
    policy_selection_cutoff: datetime | None


def decode_forecast(record,path,line):
    extras={'schema_version','execution_sha256','policy_selection_cutoff','requested_checkpoint_sha256'}
    if record.get('schema_version')!='m4a_prediction_v1' or set(record)!={f.name for f in fields(ForecastRecordV2)}|extras:
        raise ValueError('Incomplete M4A provenance envelope')
    f=decode(ForecastRecordV2,{k:v for k,v in record.items() if k not in extras})
    cutoff=datetime.fromisoformat(record['policy_selection_cutoff']) if record['policy_selection_cutoff'] else None
    if cutoff is not None and cutoff>=f.origin:raise ValueError('Source policy selected after origin')
    return SavedForecastV1(f,SourceRefV1(path,line,f.run_id,f.forecast_id,canonical_sha(record)),
        record['requested_checkpoint_sha256'],record['execution_sha256'],cutoff)


@dataclass(frozen=True,slots=True)
class FrameV1:
    tick: TickEventV2
    state: StateEventV2
    forecasts: tuple[SavedForecastV1,...]
    outcomes: tuple[TargetOutcomeV2,...]
    reset: TelemetryResetV2 | None


@dataclass(frozen=True,slots=True)
class ReplayInputV1:
    machine: str
    prefix: tuple[TickEventV2,...]
    initial_era: int
    frames: tuple[FrameV1,...]
    source_hashes: tuple[tuple[str,str],...]


def load_m4a_input(machine,root=ROOT):
    if machine not in MACHINES:raise ValueError('Only the three authorized development machines')
    root=Path(root).resolve();c,_,_=load_config(root)
    inventory_path=root/c['m4a_inventory_path'];payload=inventory_path.read_bytes()
    if sha_bytes(payload)!=c['m4a_inventory_sha256']:raise ValueError('M4A inventory changed')
    inventory=json.loads(payload)['sha256'];used={}
    def checked(relative):
        path=root/relative
        if path.resolve()!=path or relative not in inventory:raise ValueError('Unpinned/redirection source')
        data=path.read_bytes()
        if sha_bytes(data)!=inventory[relative]:raise ValueError('Saved artifact fingerprint mismatch: '+relative)
        used[relative]=inventory[relative];return data
    old=json.loads(checked('configs/dafr_m4a_execution_v1.json'))
    if used['configs/dafr_m4a_execution_v1.json']!=c['m4a_config_sha256']:raise ValueError('M4A execution changed')
    previous=json.loads(checked('reports/dafr/m4a_preservation_v1.json'))['protected_sha256']
    inventory.update(previous)
    # The prior inventory already protects native checkpoint files; this step
    # parses only the required metadata, never instantiates a model.
    pins={}
    for policy in ('arima','xgboost'):
        spec=old['models'][machine][policy];name=spec['directory']+'/metadata.json'
        raw=checked(name);meta=json.loads(raw)
        if used[name]!=spec['metadata_sha256'] or meta['family']!=policy or meta['machine_id']!=machine or meta['status']!='accepted':
            raise ValueError('Checkpoint identity differs')
        pins[policy]=(spec,meta)
    base=c['source_directory']+'/'+machine
    reconstruction=[json.loads(line) for line in checked(base+'/reconstruction.jsonl').splitlines()]
    prefix=tuple(decode(TickEventV2,e['record']) for e in reconstruction if e['kind']=='reconstruction_tick')[-23:]
    if len(prefix)!=23:raise ValueError('Required saved context history absent')
    bootstrap=json.loads(checked(base+'/bootstrap.json'))
    events=[json.loads(line) for line in checked(base+'/events.jsonl').splitlines()]
    if any(a['record']['sequence']>=b['record']['sequence'] for a,b in zip(events,events[1:])):raise ValueError('Original event order invalid')
    ticks={};states={};resets={};event_forecasts={};event_outcomes={}
    for e in events:
        kind,r=e['kind'],e['record']
        if kind=='tick':ticks[r['timestamp']]=decode(TickEventV2,r)
        elif kind=='state':states[r['timestamp']]=decode(StateEventV2,r)
        elif kind=='telemetry_reset':resets[r['timestamp']]=decode(TelemetryResetV2,r)
        elif kind in ('forecast','abstention'):event_forecasts[r['forecast_id']]=r
        elif kind in ('scored','target_unavailable'):event_outcomes[r['forecast_id']]=r
    forecasts={};outcomes={};ids=set()
    for policy in ('persistence','arima','xgboost'):
        path=base+'/'+policy+'/predictions.jsonl'
        records=[json.loads(line) for line in checked(path).splitlines()]
        if len(records)!=920:raise ValueError('Missing source forecast decisions')
        for i,r in enumerate(records,1):
            saved=decode_forecast(r,path,i);f=saved.forecast
            if f.machine_id!=machine or f.policy_id!=policy or f.forecast_id in ids:raise ValueError('Source identity/duplicate')
            ids.add(f.forecast_id)
            key=(f.origin,f.horizon,policy)
            if key in forecasts:raise ValueError('Duplicate origin/horizon')
            plain={k:v for k,v in r.items() if k in {x.name for x in fields(ForecastRecordV2)}}
            if event_forecasts.get(f.forecast_id)!=plain:raise ValueError('Forecast/event ledger differs')
            if saved.execution_sha256!=c['m4a_config_sha256']:raise ValueError('Wrong source execution hash')
            if policy!='persistence':
                spec,meta=pins[policy]
                if saved.checkpoint_sha256!=spec['metadata_sha256'] or f.policy_version!='m4a_'+meta['version']:
                    raise ValueError('Wrong original model version/checkpoint')
                if f.availability=='expert' and (f.source_version,f.training_cutoff,f.scaling_cutoff,f.version_available_at)!=(
                    meta['version'],datetime.fromisoformat(meta['training_cutoff']),None,datetime.fromisoformat(meta['checkpoint_cutoff'])):
                    raise ValueError('Source expert metadata changed')
            forecasts[key]=saved
        path=base+'/'+policy+'/outcomes.jsonl'
        for raw in checked(path).splitlines():
            r=json.loads(raw);o=decode(TargetOutcomeV2,r)
            if o.forecast_id in outcomes or o.forecast_id not in ids or event_outcomes.get(o.forecast_id)!=r:raise ValueError('Missing/duplicate/mismatched source outcome')
            outcomes[o.forecast_id]=o
    if ids!=set(event_forecasts) or set(outcomes)!=set(event_outcomes):raise ValueError('Source ledgers incomplete')
    by_target={}
    for o in outcomes.values():by_target.setdefault(o.target,[]).append(o)
    frames=[]
    for index in range(1152,1612):
        t=EPOCH+timedelta(minutes=5*(index+1));key=t.isoformat()
        if key not in ticks or key not in states:raise ValueError('Missing original grid tick/state')
        fs=tuple(forecasts[t,h,p] for h in (1,12) for p in ('persistence','arima','xgboost'))
        if len({x.forecast.context_sha256 for x in fs})!=1:raise ValueError('Expert contexts differ')
        frames.append(FrameV1(ticks[key],states[key],fs,tuple(sorted(by_target.get(t,()),key=lambda x:x.sequence)),resets.get(key)))
    if len(ticks)!=460 or prefix[-1].timestamp!=frames[0].tick.timestamp-timedelta(minutes=5):raise ValueError('Origin scope/context boundary mismatch')
    if any(o.target not in {f.tick.timestamp for f in frames} for o in outcomes.values()):raise ValueError('Forbidden target outcomes')
    return ReplayInputV1(machine,prefix,bootstrap['initial_era'],tuple(frames),tuple(sorted(used.items())))
