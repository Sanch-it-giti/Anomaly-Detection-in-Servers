"""Authorized small synthetic checkpoint recipe and replay fixtures only."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta
import json
import math
from pathlib import Path
from unittest.mock import patch

import numpy as np
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.statespace.sarimax import SARIMAXResultsWrapper

from .adaptive_checkpoint_registry_v1 import load_integration_config,synthetic_fit_values,file_hash,RegistryReferenceV1
from .real_adapters_v1 import canonical_hash,load_registered_adapter
from .run_m3b2_v1 import save_artifact
from .development_qualification_v1 import EPOCH
from .selector_v1 import ROOT
from .streaming_v2 import _write_json


def write_new(path,value):
    with Path(path).open('x') as out:_write_json(out,value)


def build_fixture_checkpoints(directory):
    """Never accepts observations or a source path. Not a replay operation.

    Known valid ARIMA(1,1,1) coefficients exercise actual state-space filtering;
    two native XGBoost boosters are fitted on genuine synthetic lag examples.
    """
    load_integration_config();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    values=synthetic_fit_values();source=canonical_hash({'generator':'m5b1_generated_fit_v1','values':values})
    plan=json.loads((ROOT/'configs/dafr_m3b_development_manifest_v1.json').read_text())
    write_new(directory/'fit_source.json',{'scope':'synthetic_only','generator_id':'m5b1_generated_fit_v1','values':values,'source_sha256':source})
    entries={}
    for family,index in (('arima',2),('xgboost',0)):
        reference,m=save_artifact(directory/family,'synthetic',source,values,family,index,plan,
            synthetic=True,known_params=[.4,.2,1.] if family=='arima' else None)
        if m['status']!='accepted':raise ValueError('Synthetic checkpoint rejected: '+str(m))
        adapter=load_registered_adapter(reference,values)
        entries[family]={'directory':family,'version':m['version'],'metadata_sha256':reference.metadata_sha256,
            'artifact_sha256':{p.name:file_hash(p) for p in reference.directory.iterdir() if p.is_file()},
            'loaded_parameter_sha256':adapter.parameter_sha256}
    registry={'scope':'SYNTHETIC_BACKEND_EXECUTION_ONLY','generator_id':'m5b1_generated_fit_v1','source_sha256':source,
        'fit_values_sha256':canonical_hash(list(values)),'experts':entries,
        'build':'ARIMA known-parameter filtering; two throwaway synthetic XGBoost fits; no Alibaba observations'}
    path=directory/'registry.json';write_new(path,registry)
    return RegistryReferenceV1(path,file_hash(path))


@contextmanager
def forbid_replay_fitting():
    audit={'fit_attempts':0}
    def forbidden(*args,**kwargs):
        audit['fit_attempts']+=1;raise AssertionError('Refitting inside streaming is prohibited')
    with patch.object(SARIMAX,'fit',forbidden),patch.object(xgb.XGBRegressor,'fit',forbidden),patch.object(xgb.Booster,'update',forbidden),patch.object(xgb,'train',forbidden):
        yield audit
    if audit['fit_attempts']:raise AssertionError('Replay attempted fitting')


def fixture_events(scenario):
    counts={'continuous':420,'gaps_failures':450,'update_failure':180}
    if scenario not in counts:raise ValueError('Built-in synthetic scenarios only')
    gaps={*range(4),70,*range(150,153),*range(230,236),*range(330,334),*range(440,450)} if scenario=='gaps_failures' else set(range(174,180)) if scenario=='update_failure' else set()
    for k in range(counts[scenario]):
        value=43+2.5*math.sin(k*.18)+math.sin(k*1.1)
        yield EPOCH+timedelta(minutes=5*(97+k)),None if k in gaps else value,'synthetic_gap' if k in gaps else None


@contextmanager
def declared_failure(simulator,scenario,tick_index):
    """Synthetic-only fault injection; never part of the integration driver's API."""
    if scenario=='gaps_failures' and tick_index==115:
        # update() replaces the one-step results wrapper, whose generated method
        # captures the original backend function. Patch the registered wrapper
        # class so the fault reaches the newly filtered result at issuance.
        original=SARIMAXResultsWrapper.forecast
        def fault(result,steps=1,**kwargs):return np.full(1,np.nan) if steps==1 else original(result,steps=steps,**kwargs)
        with patch.object(SARIMAXResultsWrapper,'forecast',new=fault):yield
    elif scenario=='gaps_failures' and tick_index==125:
        with patch.object(simulator._adapters['xgboost'].boosters[12],'inplace_predict',return_value=np.array([[np.nan]])):yield
    elif scenario=='update_failure' and tick_index==40:
        with patch.object(simulator._adapters['arima'].result,'extend',side_effect=RuntimeError('Declared synthetic update failure')):yield
    else:yield
