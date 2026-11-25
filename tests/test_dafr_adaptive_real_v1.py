"""M5B-1 real backends, generated CPU only; historical reads are hashes only."""
import copy
from dataclasses import FrozenInstanceError,replace,asdict
from datetime import timedelta
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAXResultsWrapper
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.adaptive_checkpoint_registry_v1 import (RegistryReferenceV1,load_fixture_bank,load_integration_config,
    synthetic_fit_values,file_hash,verify_historical_checkpoints)
from dafr.adaptive_real_fixtures_v1 import build_fixture_checkpoints,fixture_events,forbid_replay_fitting
from dafr.adaptive_real_streaming_v1 import AdaptiveRealStreamingV1
from dafr.adaptive_real_feedback_v1 import BackendMatchedSelectorV1
from dafr.real_adapters_v1 import RealAdapter,ArtifactReference,sarimax_model
from dafr.real_streaming_v1 import RealStreamingSimulator
from dafr.selector_v1 import MatchedSelectorV1
from dafr.selector_contracts_v1 import MatchedLossV1
from dafr.run_m5b1_v1 import run_backend_fixture,verify_preservation
from dafr.development_qualification_v1 import EPOCH
from dafr.audit_m5b1_v1 import verify_backend_run
from dafr.adaptive_real_fixtures_v1 import write_new
from dafr.streaming_v2 import _write_json

def ts(k):return EPOCH+timedelta(minutes=5*(97+k))


class AdaptiveBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();cls.root=Path(cls.tmp.name).resolve()
        cls.reference=build_fixture_checkpoints(cls.root/'checkpoints')
        with forbid_replay_fitting():
            cls.base=AdaptiveRealStreamingV1('synthetic_test',cls.reference)
            cls.stream=copy.deepcopy(cls.base);cls.steps=[]
            for row in list(fixture_events('continuous'))[:125]:cls.steps.append(cls.stream.advance(*row))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def engine(self):return copy.deepcopy(self.base)

    def test_correct_real_types_and_exact_fingerprints(self):
        adapters,pins,registry,values=load_fixture_bank(self.reference)
        self.assertEqual(values,synthetic_fit_values())
        for name,a in adapters.items():
            self.assertIs(type(a),RealAdapter);self.assertEqual(a.parameter_sha256,pins[name]['loaded_parameter_sha256'])
            self.assertEqual(a.metadata.version,pins[name]['version'])
    def test_arbitrary_objects_rejected(self):
        for bad in (object(),{},self.base._adapters['arima']):
            with self.assertRaises(ValueError):AdaptiveRealStreamingV1('bad',bad)
    def test_registry_hash_and_scope_rejected_before_backend_loading(self):
        with self.assertRaises(ValueError):load_fixture_bank(replace(self.reference,sha256='0'*64))
        with TemporaryDirectory() as temp:
            p=Path(temp).resolve()/'registry.json';r=json.loads(self.reference.path.read_text());r['scope']='REAL_DATA';p.write_text(json.dumps(r))
            with patch('dafr.adaptive_checkpoint_registry_v1.load_registered_adapter') as loader:
                with self.assertRaises(ValueError):load_fixture_bank(RegistryReferenceV1(p,file_hash(p)))
                loader.assert_not_called()
    def test_checkpoint_file_tamper_rejected(self):
        for file in ('arima/params.json','xgboost/model_h12.json','arima/features.json','arima/scaler.json','arima/metadata.json'):
            with TemporaryDirectory() as temp:
                d=Path(temp).resolve()/'bank';shutil.copytree(self.reference.path.parent,d)
                with (d/file).open('a') as out:out.write(' ')
                with self.assertRaises(ValueError):load_fixture_bank(RegistryReferenceV1(d/'registry.json',self.reference.sha256))
    def test_version_pins_rejected_even_with_new_registry_hash(self):
        with TemporaryDirectory() as temp:
            d=Path(temp).resolve()/'bank';shutil.copytree(self.reference.path.parent,d)
            p=d/'registry.json';r=json.loads(p.read_text());r['experts']['arima']['version']='rewritten';p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):load_fixture_bank(RegistryReferenceV1(p,file_hash(p)))
    def test_new_execution_locks_and_frozen_rules(self):
        c,s,h=load_integration_config()
        original=json.loads((ROOT/'configs/dafr_m5a_synthetic_v1.json').read_text())
        self.assertEqual(c['selector'],original['selector']);self.assertFalse(c['confirmation_execution_allowed'])
        self.assertIs(BackendMatchedSelectorV1.choose,MatchedSelectorV1.choose)
        with TemporaryDirectory() as temp:
            p=Path(temp)/'config.json';c['selector']['min_matched_scores']=99;p.write_text(json.dumps(c))
            with self.assertRaises(ValueError):load_integration_config(p)
    def test_bootstrap_no_duplicate_fitted_observations(self):
        s=self.engine();self.assertEqual(len(s._history),23)
        for a in s._adapters.values():self.assertEqual(a.resources()['update_calls'],0)
        self.assertEqual(s._adapters['arima'].result.nobs,96)
        with self.assertRaises(ValueError):s.advance(ts(-1),40.)
        for a in s._adapters.values():self.assertEqual(a.resources()['update_calls'],0)
    def test_exactly_one_update_per_tick_both_experts(self):
        for a in self.stream._adapters.values():
            self.assertEqual(a.resources()['update_calls'],125);self.assertEqual(a.resources()['state_steps'],125)
        for step in self.steps:
            updates=[e.record for e in step.events if e.kind=='adapter_update']
            self.assertEqual(len(updates),2);self.assertEqual(updates[0].context_sha256,updates[1].context_sha256)
    def test_real_shadow_parity_with_standalone_drivers(self):
        s=self.engine();standalone={}
        for family,p in s._pins.items():
            artifact=s._adapters[family].artifact
            ref=ArtifactReference(self.reference.path.parent/p['directory'],p['metadata_sha256'],artifact['source_sha256'],artifact['fit_values_sha256'],'synthetic')
            standalone[family]=RealStreamingSimulator('standalone','synthetic',ref,synthetic_fit_values())
        for k in range(36):
            v=None if k in (4,5) else 42.+k%3
            step=s.advance(ts(k),v,'gap' if v is None else None)
            for family,old in standalone.items():
                other=old.advance(ts(k),v,'gap' if v is None else None)
                for h in (1,12):
                    new=next(f for f in step.decisions if f.policy_id=='shadow_'+family and f.horizon==h)
                    prior=next(f for f in other.decisions if f.policy_id==family and f.horizon==h)
                    if new.availability=='expert':self.assertEqual(new.predicted_value,prior.predicted_value)
                    else:self.assertNotEqual(prior.availability,'expert')
                self.assertEqual(s._adapters[family].state_sha256,old._adapters[family].state_sha256)
    def test_missing_state_transition_matches_batch_filter(self):
        s=self.engine();full=list(synthetic_fit_values())
        for k in range(9):
            v=None if k in (2,3,6) else 43.+k%3;full.append(v)
            s.advance(ts(k),v,'gap' if v is None else None)
            a=s._adapters['arima'];batch=sarimax_model([np.nan if v is None else v for v in full],[1,1,1]).filter([.4,.2,1.])
            np.testing.assert_allclose(a.result.filter_results.filtered_state[:,-1],batch.filter_results.filtered_state[:,-1],atol=1e-9,rtol=1e-9)
            if v is None:
                f=a.result.filter_results;np.testing.assert_allclose(f.filtered_state[:,0],f.predicted_state[:,0],atol=1e-10)
        self.assertEqual(s._adapters['arima'].resources()['genuine_measurement_updates'],6)
    def test_h1_h12_nonmutating_prediction(self):
        s=self.engine();step=s.advance(ts(0),43.);ctx=s._context(step.tick)
        for a in s._adapters.values():
            state,params=a.state_sha256,a.parameter_sha256
            for h in (1,12):
                r=a.forecast(ctx,h);self.assertEqual(r.status,'ok');self.assertEqual(r.target,ts(h))
                self.assertEqual((a.state_sha256,a.parameter_sha256),(state,params))
    def test_origin_relative_features_are_exact(self):
        s=self.engine();step=s.advance(ts(0),43.);ctx=s._context(step.tick)
        a=s._adapters['xgboost'];x=np.asarray([[ctx.history[-1-o].value for o in (0,1,2,5,11,23)]],dtype=np.float32)
        for h in (1,12):self.assertEqual(a.forecast(ctx,h).value,float(a.boosters[h].inplace_predict(x,strict_shape=True)[0,0]))
    def test_delayed_h12_genuine_feedback(self):
        self.assertTrue(all(p.horizon!=12 for step in self.steps[:12] for p in step.matched))
        self.assertTrue(any(p.horizon==12 for p in self.steps[12].matched))
        for f in self.steps[0].decisions:self.assertEqual(f.target,ts(f.horizon))
    def test_correct_99_100_support_gate(self):
        for h,k in ((1,100),(12,111)):
            before=next(x for x in self.steps[k-1].selections if x.horizon==h)
            current=next(x for x in self.steps[k].selections if x.horizon==h)
            self.assertEqual(before.matched_count,99);self.assertFalse(before.switched)
            self.assertEqual(current.matched_count,100)
    def test_only_genuine_matched_shadow_errors_rank_experts(self):
        for b in self.stream.selector.buffers.values():
            for pair in b:
                for fid in pair.forecast_ids:
                    f=self.stream.ledger._records[fid]
                    self.assertTrue(f.policy_id.startswith('shadow_'));self.assertEqual(f.availability,'expert')
    def test_hysteresis_dwell_and_independent_horizons(self):
        s=self.engine();step=s.advance(ts(0),43.);ctx=s._context(step.tick);sel=s.selector
        def prime(h,errors,elapsed):
            sel.buffers[h].clear();sel._chosen.discard(h);sel.last_change[h]=ts(0)-timedelta(minutes=5*elapsed)
            for j in range(100):
                target=ts(0)-timedelta(minutes=5*(99-j))
                sel.buffers[h].append(MatchedLossV1(target-timedelta(minutes=5*h),target,h,0,ctx.context_sha256,
                    (f'a-{j}',f'x-{j}'),tuple(sel._expected_versions),errors))
        prime(1,(2.,0.),23);self.assertEqual(sel.choose(ctx,1,frozenset(('arima','xgboost'))).reason,'dwell_hold')
        prime(1,(2.,0.),24);self.assertEqual(sel.choose(ctx,1,frozenset(('arima','xgboost'))).incumbent,'xgboost')
        prime(12,(.15,.10),100);self.assertEqual(sel.choose(ctx,12,frozenset(('arima','xgboost'))).reason,'hysteresis_hold')
        self.assertEqual(sel.incumbents,{1:'xgboost',12:'arima'})
    def test_suffix_perturbation_invariance(self):
        a=self.engine();b=self.engine();aa=[];bb=[]
        for k in range(22):
            aa.append(a.advance(ts(k),42.+k%3))
            v=(None if k%2 else 99.) if k>=15 else 42.+k%3
            bb.append(b.advance(ts(k),v,'changed' if v is None else None))
        self.assertEqual(aa[:15],bb[:15]);self.assertNotEqual(aa[15:],bb[15:])
    def test_gap_recovery_reset_and_fallback_expiration(self):
        s=self.engine();steps=[]
        for k in range(32):steps.append(s.advance(ts(k),None if k<6 else 43.,'gap' if k<6 else None))
        for step in steps[:3]:self.assertTrue(all(f.availability=='fallback' for f in step.decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(f.availability=='abstained' for f in steps[3].decisions if f.policy_id=='adaptive'))
        self.assertEqual(sum(x.reset is not None for x in steps),1)
        self.assertTrue(all(f.availability=='fallback' for f in steps[28].decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(f.availability=='expert' for f in steps[29].decisions if f.policy_id=='adaptive'))
    def test_missing_exact_targets_never_score_or_shift(self):
        s=self.engine();steps=[]
        for k in range(15):steps.append(s.advance(ts(k),None if k==12 else 43.,'gap' if k==12 else None))
        for h,origin in ((1,11),(12,0)):
            f=next(f for f in steps[origin].decisions if f.policy_id=='shadow_arima' and f.horizon==h)
            os=[o for o in s.ledger.outcomes if o.forecast_id==f.forecast_id]
            self.assertEqual(len(os),1);self.assertEqual(os[0].status,'target_unavailable');self.assertIsNone(os[0].absolute_error)
    def test_nonfinite_incumbent_forecast_has_honest_fallback(self):
        s=self.engine();a=s._adapters['arima']
        with patch.object(SARIMAXResultsWrapper,'forecast',new=lambda result,steps=1:np.full(steps,np.nan)):
            step=s.advance(ts(0),43.)
        for f in step.decisions:
            if f.policy_id=='shadow_arima':self.assertEqual(f.availability,'numerical_failure');self.assertIsNone(f.predicted_value)
            if f.policy_id=='adaptive':self.assertEqual(f.availability,'fallback');self.assertEqual(f.source_expert,'persistence')
        later=s.advance(ts(1),43.);self.assertFalse(later.matched)
    def test_bridge_support_expires_by_original_grid_age(self):
        s=self.engine();step=s.advance(ts(0),43.)
        pair=MatchedLossV1(ts(-299),ts(-287),12,0,'a'*64,('old-a','old-x'),s.selector._expected_versions,(1.,2.))
        s.selector.buffers[12].append(pair)
        s.advance(ts(1),43.)
        self.assertFalse(s.selector.buffers[12])
    def test_old_era_matched_losses_do_not_seed_new_era(self):
        s=self.engine();steps=[]
        for k in range(39):steps.append(s.advance(ts(k),None if 30<=k<34 else 43.,'gap' if 30<=k<34 else None))
        self.assertTrue(any(p.era==0 for step in steps[34:] for p in step.matched))
        self.assertFalse(s.selector.buffers[12]);self.assertEqual(s.selector.era,1)
    def test_nonfinite_xgboost_h12_does_not_spoil_h1(self):
        s=self.engine()
        with patch.object(s._adapters['xgboost'].boosters[12],'inplace_predict',return_value=np.array([[np.nan]])):
            step=s.advance(ts(0),43.)
        fs={f.horizon:f for f in step.decisions if f.policy_id=='shadow_xgboost'}
        self.assertEqual(fs[1].availability,'expert');self.assertEqual(fs[12].availability,'numerical_failure')
    def test_failed_update_latches_stale_state_and_abstention(self):
        s=self.engine()
        with patch.object(s._adapters['arima'].result,'extend',side_effect=RuntimeError('fixture failure')):
            first=s.advance(ts(0),43.)
        f=next(f for f in first.decisions if f.policy_id=='shadow_arima' and f.horizon==1)
        self.assertLess(f.requested_state_cutoff,f.origin);self.assertEqual(f.availability,'numerical_failure')
        for k in range(1,5):last=s.advance(ts(k),None,'gap')
        self.assertTrue(all(f.availability=='abstained' for f in last.decisions if f.policy_id=='adaptive'))
    def test_historical_model_version_changes_abort_before_tick(self):
        s=self.engine();s._adapters['arima'].metadata=replace(s._adapters['arima'].metadata,version='tampered')
        with self.assertRaises(ValueError):s.advance(ts(0),43.)
        self.assertEqual(s._ticks,0)
    def test_parameter_mutation_aborts_before_tick(self):
        s=self.engine();s._adapters['arima'].result.params[0]+=.01
        with self.assertRaises(ValueError):s.advance(ts(0),43.)
        self.assertEqual(s._ticks,0)
    def test_parameters_fixed_despite_shadow_and_policy_choices(self):
        self.assertEqual({k:a.parameter_sha256 for k,a in self.stream._adapters.items()},self.stream._parameters)
        for step in self.steps:
            for f in step.decisions:
                if f.requested_metadata:self.assertEqual(f.requested_parameter_sha256,self.stream._parameters[f.requested_metadata.expert_id])
    def test_immutable_decisions_outcomes_and_shadow_links(self):
        f=next(f for f in self.steps[0].decisions if f.policy_id=='adaptive');o=self.stream.ledger.outcomes[0]
        with self.assertRaises(FrozenInstanceError):f.predicted_value=0
        with self.assertRaises(FrozenInstanceError):o.actual=0
        shadow=self.stream.ledger._records[f.source_shadow_id];self.assertEqual(f.predicted_value,shadow.predicted_value)
    def test_registry_and_state_provenance_on_every_requested_expert(self):
        for f in self.stream.ledger.decisions:
            self.assertEqual(f.registry_sha256,self.reference.sha256)
            if f.requested_metadata:
                self.assertEqual(f.requested_checkpoint_sha256,self.stream._pins[f.requested_metadata.expert_id]['metadata_sha256'])
                self.assertLessEqual(f.requested_metadata.training_cutoff,f.origin);self.assertLessEqual(f.requested_state_cutoff,f.origin)
    def test_replay_fitting_guard(self):
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        with self.assertRaises(AssertionError):
            with forbid_replay_fitting():SARIMAX.fit(None)
    def test_no_real_data_or_historical_model_read_by_driver(self):
        original=Path.open
        def guard(p,*args,**kwargs):
            mode=args[0] if args else kwargs.get('mode','r')
            if 'r' in mode and (p.is_relative_to(ROOT/'data') or p.is_relative_to(ROOT/'models')):raise AssertionError('Real project data/model read')
            return original(p,*args,**kwargs)
        with patch.object(Path,'open',guard):
            s=AdaptiveRealStreamingV1('isolated',self.reference);s.advance(ts(0),43.)
    def test_no_overwrite_and_failure_reservation(self):
        with TemporaryDirectory() as temp:
            p=Path(temp).resolve()/'reserved';p.mkdir();(p/'sentinel').write_text('preserve')
            with self.assertRaises(FileExistsError):run_backend_fixture(p,self.reference,'continuous')
            self.assertEqual((p/'sentinel').read_text(),'preserve')
            failed=p.parent/'failed'
            with patch('dafr.run_m5b1_v1.fixture_events',side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):run_backend_fixture(failed,self.reference,'continuous')
            self.assertEqual(json.loads((failed/'completion.json').read_text())['status'],'failed')
            with self.assertRaises(FileExistsError):run_backend_fixture(failed,self.reference,'continuous')
    def test_protected_hashes_and_historical_checkpoints(self):
        self.assertEqual(verify_preservation(),437)
        result=verify_historical_checkpoints();self.assertEqual(result['checkpoint_bundles'],6);self.assertEqual(result['checkpoint_files_verified'],27)
    def test_saved_ledger_audit_and_prediction_tamper_rejection(self):
        with TemporaryDirectory() as temp:
            d=Path(temp).resolve()
            write_new(d/'manifest.json',{'scope':'SYNTHETIC_REAL_BACKEND_FIXTURE','real_data_execution_allowed':False,
                'registry_path':str(self.reference.path),'registry_sha256':self.reference.sha256,'scenario':'continuous'})
            for name,items in (
                ('events',({'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)} for step in self.steps for e in step.events)),
                ('shadow_predictions',(asdict(f) for step in self.steps for f in step.decisions if f.policy_id.startswith('shadow_'))),
                ('policy_predictions',(asdict(f) for step in self.steps for f in step.decisions if not f.policy_id.startswith('shadow_'))),
                ('outcomes',(asdict(o) for step in self.steps for o in step.outcomes))):
                with (d/(name+'.jsonl')).open('x') as out:
                    for item in items:_write_json(out,item)
            expected=list(fixture_events('continuous'))[:125]
            result=verify_backend_run(d,expected);self.assertTrue(result['passed']);self.assertEqual(result['grid_ticks'],125)
            p=d/'policy_predictions.jsonl';lines=p.read_text().splitlines();row=json.loads(lines[0]);row['predicted_value']+=1
            lines[0]=json.dumps(row);p.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(AssertionError):verify_backend_run(d,expected)


if __name__=='__main__':unittest.main()
