"""M5B-1 real-backend synthetic runs, immutable outputs and preservation."""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from contextlib import ExitStack
import argparse
import json
import resource
import sys
import time

from .contracts import identifier
from .adaptive_checkpoint_registry_v1 import ROOT,file_hash,load_integration_config,verify_historical_checkpoints
from .adaptive_real_fixtures_v1 import build_fixture_checkpoints,fixture_events,declared_failure,forbid_replay_fitting,write_new
from .adaptive_real_streaming_v1 import AdaptiveRealStreamingV1
from .streaming_v2 import _write_json

SOURCES=('configs/dafr_m5b1_integration_v1.json','configs/dafr_m5b1_checkpoint_registry_v1.json',
    'src/dafr/adaptive_checkpoint_registry_v1.py','src/dafr/adaptive_real_contracts_v1.py',
    'src/dafr/adaptive_real_feedback_v1.py','src/dafr/adaptive_real_streaming_v1.py',
    'src/dafr/adaptive_real_fixtures_v1.py','src/dafr/run_m5b1_v1.py','src/dafr/audit_m5b1_v1.py','tests/test_dafr_adaptive_real_v1.py')


def verify_preservation():
    receipt=json.loads((ROOT/'reports/dafr/m5b1_preservation_v1.json').read_text())
    for path,sha in receipt['protected_sha256'].items():
        if file_hash(ROOT/path)!=sha:raise ValueError('Historical file changed: '+path)
    return receipt['file_count']


def rss():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def run_backend_fixture(directory,reference,scenario):
    if scenario not in ('continuous','gaps_failures','update_failure'):raise ValueError('Synthetic fixtures only')
    directory=Path(directory)
    if directory.resolve()!=directory:raise ValueError('Output redirection forbidden')
    directory.mkdir(parents=True,exist_ok=False)
    completion={'status':'failed'};start=time.perf_counter()
    try:
        with forbid_replay_fitting() as no_fit:
            sim=AdaptiveRealStreamingV1(directory.name,reference)
            write_new(directory/'manifest.json',{'scope':'SYNTHETIC_REAL_BACKEND_FIXTURE','scenario':scenario,
                'registry_path':str(reference.path),'registry_sha256':reference.sha256,'execution_sha256':sim.execution_sha256,
                'checkpoint_metadata':{k:asdict(v) for k,v in sim._versions.items()},'parameter_sha256':sim._parameters,
                'model_parameters_fixed':True,'confirmation_execution_allowed':False,'real_data_execution_allowed':False,
                'bootstrap_history_slots':23,'bootstrap_model_updates':0,'selector_seeded_with_fit_errors':False})
            counts=Counter();maximum_support={1:0,12:0};switches=[]
            with ExitStack() as stack:
                files={name:stack.enter_context((directory/(name+'.jsonl')).open('x')) for name in
                    ('events','shadow_predictions','policy_predictions','outcomes','matched_losses','selector_states','switches','resets')}
                for index,row in enumerate(fixture_events(scenario)):
                    if rss()>4*1024**3:raise MemoryError('4 GiB process RSS budget exceeded')
                    with declared_failure(sim,scenario,index):step=sim.advance(*row)
                    for e in step.events:
                        _write_json(files['events'],{'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)})
                        stream={'selector_state':'selector_states','expert_switch':'switches','telemetry_reset':'resets','matched_shadow_loss':'matched_losses'}.get(e.kind)
                        if stream:_write_json(files[stream],{'sequence':e.sequence,'record':asdict(e.record)})
                        if e.kind=='expert_switch':switches.append(asdict(e.record))
                        if e.kind=='telemetry_reset':counts['telemetry_resets']+=1
                        if e.kind=='adapter_update':
                            counts['update_'+e.record.status]+=1
                            counts['stale_state_receipts']+=e.record.result.model_state_cutoff<step.tick.timestamp
                        if e.kind=='shadow_attempt':counts['forecast_attempt_'+e.record.status]+=1
                    for f in step.decisions:
                        _write_json(files['shadow_predictions' if f.policy_id.startswith('shadow_') else 'policy_predictions'],asdict(f))
                    for o in step.outcomes:_write_json(files['outcomes'],asdict(o))
                    for s in step.selections:maximum_support[s.horizon]=max(maximum_support[s.horizon],s.matched_count)
            rows=[];pending=set(sim.ledger.pending_ids)
            for policy in ('shadow_arima','shadow_xgboost','adaptive','persistence'):
                for h in (1,12):
                    ds=[f for f in sim.ledger.decisions if (f.policy_id,f.horizon)==(policy,h)]
                    os=[o for o in sim.ledger.outcomes if (o.policy_id,o.horizon)==(policy,h)]
                    rows.append({'policy':policy,'horizon':h,'decisions':len(ds),
                        **{status:sum(f.availability==status for f in ds) for status in ('expert','fallback','baseline','abstained','gated','unavailable','numerical_failure')},
                        'genuine_scored':sum(o.status=='scored' for o in os),'target_unavailable':sum(o.status=='target_unavailable' for o in os),
                        'pending':sum(f.forecast_id in pending for f in ds)})
            summary={'scenario':scenario,'grid_ticks':sim._ticks,'genuine_ticks':sim._genuine,'missing_ticks':sim._ticks-sim._genuine,
                'switch_counts':sim.selector.switches,'switch_records':switches,'maximum_matched_support':maximum_support,
                'final_matched_support':{h:len(b) for h,b in sim.selector.buffers.items()},'accounting':rows,'event_counts':dict(counts),
                'backend_resources':{k:a.resources() for k,a in sim._adapters.items()},'no_refitting':dict(no_fit),
                'elapsed_seconds':time.perf_counter()-start,'peak_process_rss_bytes':rss(),
                'parameters_unchanged':all(a.parameter_sha256==sim._parameters[k] for k,a in sim._adapters.items()),
                'interpretation':'Real backend mechanics on synthetic data, not a real-data adaptive benchmark or improvement claim'}
            write_new(directory/'summary.json',summary)
        completion={'status':'completed','grid_ticks':sim._ticks,'streaming_fit_attempts':no_fit['fit_attempts']}
    except BaseException as error:
        completion.update(error_type=type(error).__name__,error=str(error));raise
    finally:write_new(directory/'completion.json',completion)
    return summary


def demonstrate(run_id):
    identifier(run_id);load_integration_config();verify_preservation();checkpoints=verify_historical_checkpoints()
    gate=json.loads((ROOT/'reports/dafr/m5b1_backend_gate_v1.json').read_text())
    if gate.get('passed') is not True or any(gate['source_sha256'].get(p)!=file_hash(ROOT/p) for p in SOURCES):raise ValueError('Successful current test/source gate required')
    output=ROOT/'data/processed/dafr/m5b1_synthetic_backend_v1'/run_id
    report=ROOT/'reports/dafr/m5b1_v1'/run_id
    for path in (output,report):
        if path.resolve()!=path:raise ValueError('Output symlink redirection')
        if path.exists():raise FileExistsError('Versioned run already exists')
    output.mkdir(parents=True,exist_ok=False);report.mkdir(parents=True,exist_ok=False)
    reference=build_fixture_checkpoints(output/'fixture_checkpoints')
    result={scenario:run_backend_fixture(output/scenario,reference,scenario) for scenario in ('continuous','gaps_failures','update_failure')}
    from .audit_m5b1_v1 import verify_backend_run
    audits={scenario:verify_backend_run(output/scenario) for scenario in result}
    write_new(report/'ledger_verification.json',audits)
    write_new(report/'synthetic_summary.json',result)
    write_new(report/'preservation_verification.json',{'protected_hashes_verified':verify_preservation(),'historical_checkpoints':checkpoints,
        'historical_data_parsed':False,'confirmation_execution_allowed':False})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    print(demonstrate(parser.parse_args().run_id))
