"""M5B-1 controlled real-backend registry; execution is synthetic fixtures only."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from .real_adapters_v1 import ArtifactReference,RealAdapter,load_registered_adapter,canonical_hash,FEATURE_SPEC,IDENTITY
from .selector_v1 import ROOT,load_selector_config


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def load_integration_config(path=ROOT/'configs/dafr_m5b1_integration_v1.json'):
    payload=Path(path).read_bytes();c=json.loads(payload)
    if c.get('schema_version')!='dafr_m5b1_integration_v1' or c.get('scope')!='SYNTHETIC_REAL_BACKEND_FIXTURES_ONLY':raise ValueError('Wrong integration scope')
    if c.get('synthetic_backend_execution_allowed') is not True or c.get('synthetic_fixture_build_allowed') is not True:
        raise ValueError('Synthetic fixture authorization required')
    for name in ('real_data_execution_allowed','alibaba_training_allowed','confirmation_execution_allowed','m5b2_execution_allowed','drift_detection_allowed','prediction_intervals_allowed'):
        if c.get(name) is not False:raise ValueError('Unauthorized M5B-1 capability: '+name)
    old=json.loads((ROOT/'configs/dafr_m5a_synthetic_v1.json').read_text());selector,_=load_selector_config()
    if c['m5a_config_sha256']!=file_hash(ROOT/'configs/dafr_m5a_synthetic_v1.json') or c['selector']!=old['selector'] or c['missingness']!=old['missingness']:
        raise ValueError('Frozen M5A scientific rules changed')
    expected={'generator_id':'m5b1_generated_fit_v1','fit_grid_size':96,'arima_order':[1,1,1],
        'arima_known_parameters':[0.4,0.2,1.0],'arima_optimizer_allowed':False,
        'xgboost_configuration':{'max_depth':2,'n_estimators':100,'learning_rate':0.05},'seed':42,
        'description':'Known-parameter ARIMA filtering and two throwaway XGBoost fits on deterministic synthetic history only'}
    if c['synthetic_fixture']!=expected or c['max_grid_ticks_per_run']!=2304 or c['maximum_process_rss_bytes']!=4*1024**3:
        raise ValueError('Synthetic fixture/resource recipe changed')
    return c,selector,hashlib.sha256(payload).hexdigest()


def synthetic_fit_values():
    return tuple(40+2*math.sin(i*.3)+.5*math.sin(i*1.9)+.02*i for i in range(96))


@dataclass(frozen=True,slots=True)
class RegistryReferenceV1:
    path: Path
    sha256: str

    def __post_init__(self):
        from .selector_contracts_v1 import digest
        if not isinstance(self.path,Path):raise ValueError('Canonical registry path required')
        digest(self.sha256)


def load_fixture_bank(reference):
    """Admit immutable artifact references, never preconstructed model objects."""
    if type(reference) is not RegistryReferenceV1:raise ValueError('Validated registry reference required')
    path=reference.path
    if not path.is_absolute() or path.resolve()!=path or file_hash(path)!=reference.sha256:raise ValueError('Registry path or fingerprint mismatch')
    registry=json.loads(path.read_text())
    values=synthetic_fit_values();source_hash=canonical_hash({'generator':'m5b1_generated_fit_v1','values':values})
    if registry.get('scope')!='SYNTHETIC_BACKEND_EXECUTION_ONLY' or registry.get('generator_id')!='m5b1_generated_fit_v1' or registry.get('fit_values_sha256')!=canonical_hash(list(values)) or registry.get('source_sha256')!=source_hash:
        raise ValueError('Only built-in synthetic fit data can enter M5B-1')
    if set(registry['experts'])!={'arima','xgboost'}:raise ValueError('Exactly two registered backends required')
    adapters={};pins={}
    for family in ('arima','xgboost'):
        spec=registry['experts'][family]
        directory=path.parent/spec['directory']
        if Path(spec['directory']).name!=spec['directory'] or directory.resolve()!=directory:raise ValueError('Artifact path redirection')
        for name,sha in spec['artifact_sha256'].items():
            if Path(name).name!=name or (directory/name).resolve()!=directory/name or file_hash(directory/name)!=sha:raise ValueError('Checkpoint byte fingerprint mismatch')
        metadata=json.loads((directory/'metadata.json').read_text())
        if metadata['scope']!='synthetic_backend_test' or metadata['family']!=family or metadata['machine_id']!='synthetic' or metadata['status']!='accepted':
            raise ValueError('Only accepted synthetic backend checkpoints can execute')
        required={'metadata.json','features.json','scaler.json'}|({'params.json'} if family=='arima' else {'model_h1.json','model_h12.json'})
        if set(spec['artifact_sha256'])!=required or spec['metadata_sha256']!=spec['artifact_sha256']['metadata.json']:
            raise ValueError('Incomplete checkpoint pin set')
        if metadata['fit_grid_size']!=96 or metadata['source_sha256']!=source_hash:raise ValueError('Wrong synthetic source')
        if family=='arima' and metadata['order']!=[1,1,1]:raise ValueError('ARIMA fixture order changed')
        if family=='xgboost' and any(metadata['configuration'][k]!=v for k,v in {'max_depth':2,'n_estimators':100,'learning_rate':.05}.items()):raise ValueError('XGBoost fixture configuration changed')
        artifact=ArtifactReference(directory,spec['metadata_sha256'],source_hash,registry['fit_values_sha256'],'synthetic')
        adapter=load_registered_adapter(artifact,values)
        if type(adapter) is not RealAdapter:raise ValueError('Unregistered backend type')
        if adapter.artifact['hashes']!={k:v for k,v in spec['artifact_sha256'].items() if k!='metadata.json'}:
            raise ValueError('Registry and native metadata hashes differ')
        if adapter.artifact['version']!=spec['version'] or adapter.parameter_sha256!=spec['loaded_parameter_sha256']:
            raise ValueError('Loaded version/parameter fingerprint mismatch')
        adapters[family]=adapter;pins[family]=spec
    return adapters,pins,registry,values


def verify_historical_checkpoints():
    """Byte checks only: no source observations or historical outcome parsing."""
    inventory=json.loads((ROOT/'configs/dafr_m5b1_checkpoint_registry_v1.json').read_text())
    if inventory['historical_execution_allowed'] is not False:raise ValueError('Historical execution remains disabled')
    count=0
    for families in inventory['historical_checkpoints'].values():
        for spec in families.values():
            for name,sha in spec['artifact_sha256'].items():
                if file_hash(ROOT/spec['directory']/name)!=sha:raise ValueError('Historical checkpoint changed')
                count+=1
    return {'checkpoint_bundles':6,'checkpoint_files_verified':count,'observation_data_loaded':False,'historical_execution_allowed':False}
