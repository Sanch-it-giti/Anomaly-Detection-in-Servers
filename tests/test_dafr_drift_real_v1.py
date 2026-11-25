"""M6B real adapters on generated observations; historical access is hashing."""
import copy
from dataclasses import FrozenInstanceError,replace
from datetime import timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.adaptive_real_fixtures_v1 import build_fixture_checkpoints,forbid_replay_fitting,declared_failure
from dafr.drift_real_streaming_v1 import RealBackendDriftStreamV1,BackendReferenceBridgeV1,load_m6b_config
from dafr.run_m6b_v1 import synthetic_events,run_case,audit_case,verify_preservation,demonstrate
from dafr.drift_v1 import PageHinkleyErrorV1,load_drift_config
from dafr.real_adapters_v1 import RealAdapter
from dafr.run_m6a_v1 import sha


class RealDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();cls.root=Path(cls.tmp.name).resolve()
        cls.reference=build_fixture_checkpoints(cls.root/'checkpoints')
        cls.base=RealBackendDriftStreamV1('integration_test',cls.reference)
        cls.rows=list(synthetic_events('sustained'));cls.sim=copy.deepcopy(cls.base)
        with forbid_replay_fitting():cls.steps=[cls.sim.advance(*r) for r in cls.rows]

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def engine(self):return copy.deepcopy(self.base)
    def monitor(self,kind):return [e for s in self.steps for e in s.monitor_events if e.kind==kind]

    def test_registered_real_types(self):
        self.assertEqual(set(self.base.backend._adapters),{'arima','xgboost'})
        for a in self.base.backend._adapters.values():self.assertIs(type(a),RealAdapter)

    def test_arbitrary_adapters_rejected(self):
        with self.assertRaises(ValueError):RealBackendDriftStreamV1('bad',object())

    def test_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):RealBackendDriftStreamV1('bad',self.reference,1)

    def test_frozen_config_and_locks(self):
        c,h=load_m6b_config();self.assertFalse(c['confirmation_execution_allowed'])
        self.assertFalse(c['detector_response_allowed'])
        self.assertEqual(c['frozen_source_sha256']['configs/dafr_m6a_synthetic_v1.json'],sha(ROOT/'configs/dafr_m6a_synthetic_v1.json'))
        for d in self.sim.detectors.values():self.assertIs(type(d),PageHinkleyErrorV1)

    def test_fixed_persistence_reference_link(self):
        for e in self.monitor('reference_error_link'):
            b=e.record;self.assertEqual(b.original_forecast.policy_id,'persistence')
            self.assertEqual(b.original_forecast.forecast_id,b.sample.forecast.forecast_id)
            self.assertEqual(b.original_outcome.event_id,b.sample.outcome.event_id)
            self.assertEqual(b.original_forecast.context_sha256,b.sample.forecast.context_sha256)
            self.assertEqual(b.sample.forecast.policy_version,'rule_v2')

    def test_expert_and_adaptive_fallback_rejected(self):
        s=self.steps[1].backend
        for o in s.outcomes:
            f=self.sim.backend.ledger._records[o.forecast_id]
            if f.policy_id!='persistence':
                with self.assertRaises(ValueError):BackendReferenceBridgeV1.create(f,o)

    def test_wrong_original_provenance_rejected(self):
        b=self.monitor('reference_error_link')[0].record
        with self.assertRaises(ValueError):BackendReferenceBridgeV1.create(b.original_forecast,replace(b.original_outcome,forecast_id='other'))

    def test_exact_horizons_and_delayed_feedback(self):
        links=self.monitor('reference_error_link')
        first={h:next(e for e in links if e.record.sample.outcome.horizon==h) for h in (1,12)}
        for h,e in first.items():self.assertEqual(e.record.sample.outcome.target-self.rows[0][0],timedelta(minutes=5*h))
        for s in self.steps:
            for e in s.monitor_events:
                if e.kind=='reference_error_link':self.assertEqual(e.record.original_outcome.target,s.backend.tick.timestamp)

    def test_backend_then_monitor_barrier(self):
        for s in self.steps:
            barrier=max(e.sequence for e in s.backend.events)
            self.assertTrue(all(e.backend_barrier_sequence==barrier for e in s.monitor_events))
            self.assertTrue(any(e.kind=='issuance' for e in s.backend.events))

    def test_monitoring_does_not_change_any_backend_step(self):
        disabled=self.engine();disabled.monitoring_enabled=False
        with forbid_replay_fitting():
            for row,s in zip(self.rows,self.steps):
                other=disabled.advance(*row);self.assertEqual(other.backend,s.backend)
                self.assertEqual(other.monitor_events,())

    def test_parameters_and_checkpoint_hashes_unchanged(self):
        for name,a in self.sim.backend._adapters.items():self.assertEqual(a.parameter_sha256,self.base.backend._parameters[name])
        self.assertEqual(self.reference.sha256,sha(self.reference.path))

    def test_frozen_warmup_support_and_separate_horizons(self):
        self.assertIsNot(self.sim.detectors[1],self.sim.detectors[12])
        for e in self.monitor('detector_update'):
            s=e.record
            if s.normalization_count<32:self.assertIsNone(s.normalization_center)
        for kind in ('warning_entered','statistical_alarm'):
            for e in self.monitor(kind):self.assertGreaterEqual(e.record.genuine_support,64)

    def test_repeated_alarms_and_exact_cooldown(self):
        for h in (1,12):
            alarms=[e.record for e in self.monitor('statistical_alarm') if e.record.horizon==h]
            self.assertGreater(len(alarms),1)
            for a,b in zip(alarms,alarms[1:]):self.assertGreaterEqual(b.available_at,a.cooldown_until)
            for a in alarms:self.assertEqual(a.cooldown_until-a.available_at,timedelta(minutes=120))

    def test_detector_statistics_equal_direct_m6a_replay(self):
        c,h=load_drift_config();ds={n:PageHinkleyErrorV1(n,h,c) for n in (1,12)}
        for s in self.steps:
            for d in ds.values():d.clock(s.backend.tick.timestamp,0)
            for e in s.monitor_events:
                if e.kind=='reference_error_link':
                    b=e.record;update=ds[b.original_outcome.horizon].observe(b.sample)
                elif e.kind=='detector_update':self.assertEqual(update.snapshot,e.record)

    def test_future_suffix_value_and_mask_invariance(self):
        a=self.engine();b=self.engine()
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:90]):
                ra=a.advance(*row)
                rb=b.advance(*(row if i<80 else (row[0],None,'changed_suffix')))
                if i<80:self.assertEqual(ra,rb)

    def test_missing_exact_targets_and_long_gap_reset(self):
        sim=self.engine();steps=[]
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:90]):
                steps.append(sim.advance(*(row if not 50<=i<56 else (row[0],None,'gap'))))
        resets=[i for i,s in enumerate(steps) if any(e.kind=='detector_telemetry_reset' for e in s.monitor_events)]
        self.assertEqual(resets,[53])
        for s in steps[50:56]:
            self.assertFalse(any(e.kind=='reference_error_link' for e in s.monitor_events))
            self.assertTrue(all(o.status=='target_unavailable' for o in s.backend.outcomes))
        self.assertGreater(sim.detectors[12].ignored_old_errors,0)

    def test_forecast_numerical_failure_remains_separate(self):
        sim=self.engine()
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:116]):
                with declared_failure(sim.backend,'gaps_failures',i):s=sim.advance(*row)
        failed=[f for f in s.backend.decisions if f.policy_id=='shadow_arima' and f.horizon==1][0]
        self.assertEqual(failed.availability,'numerical_failure')
        self.assertTrue(any(e.kind=='reference_error_link' for e in s.monitor_events))

    def test_update_failure_latch_and_monitor_independence(self):
        sim=self.engine()
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:45]):
                with declared_failure(sim.backend,'update_failure',i):s=sim.advance(*row)
        f=next(f for f in s.backend.decisions if f.policy_id=='shadow_arima')
        self.assertNotEqual(f.availability,'expert')
        self.assertEqual(sim.detectors[1].lifetime_errors,44)

    def test_immutable_records_and_no_revision(self):
        first=self.steps[0].backend.decisions[0]
        self.assertEqual(self.sim.backend.ledger._records[first.forecast_id],first)
        with self.assertRaises(FrozenInstanceError):first.predicted_value=999
        alert=self.monitor('statistical_alarm')[0].record
        with self.assertRaises(FrozenInstanceError):alert.threshold=1

    def test_no_alert_callback_or_model_fitting_interface(self):
        self.assertFalse(hasattr(self.sim,'on_alarm'));self.assertFalse(hasattr(self.sim,'fit'))
        for d in self.sim.detectors.values():self.assertFalse(hasattr(d,'selector'))

    def test_invalid_cadence_rejected(self):
        sim=self.engine();sim.advance(*self.rows[0])
        with self.assertRaises(ValueError):sim.advance(*self.rows[2])

    def test_no_observation_file_reads_during_integration(self):
        original=Path.open;blocked=[]
        def checked(path,*args,**kwargs):
            name=str(path.resolve())
            if any(part in name for part in ('/data/raw/','/data/external/','/alibaba_prefix',
                                              '/confirmation','/m4a_forward')):
                blocked.append(name);raise AssertionError('Observation read forbidden')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',checked),forbid_replay_fitting():
            sim=RealBackendDriftStreamV1('isolated',self.reference)
            for row in self.rows[:2]:sim.advance(*row)
        self.assertEqual(blocked,[])

    def test_existing_case_directory_is_never_overwritten(self):
        with TemporaryDirectory() as temp:
            p=Path(temp)/'existing';p.mkdir();(p/'sentinel').write_text('preserve')
            with self.assertRaises(FileExistsError):run_case(p,self.reference,'sustained')
            self.assertEqual((p/'sentinel').read_text(),'preserve')

    def test_saved_independent_audit_and_tamper_rejection(self):
        with TemporaryDirectory() as temp:
            p=Path(temp)/'run';run_case(p,self.reference,'sustained')
            self.assertEqual(audit_case(p)['status'],'passed')
            with (p/'outcomes.jsonl').open('a') as out:out.write('tamper')
            with self.assertRaises(ValueError):audit_case(p)

    def test_no_overwrite_before_checkpoint_build(self):
        p=ROOT/'data/processed/dafr/m6b_synthetic_backend_v1/test-existing-m6b'
        p.mkdir(parents=True,exist_ok=False)
        try:
            with patch('dafr.run_m6b_v1.build_fixture_checkpoints') as builder:
                with self.assertRaises(FileExistsError):demonstrate(p.name)
                builder.assert_not_called()
        finally:p.rmdir()

    def test_all_690_historical_hashes_and_checkpoint_registry(self):
        self.assertEqual(verify_preservation(),690)


if __name__=='__main__':unittest.main()
