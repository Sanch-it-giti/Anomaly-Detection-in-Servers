"""Registered real backends on generated streams, no new research data."""
import copy
from dataclasses import replace,FrozenInstanceError
from datetime import timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.interval_real_streaming_v1 import RealIntervalStreamingV1,load_m7b_config
from dafr.interval_real_contracts_v1 import BackendIntervalRecordV1
from dafr.drift_real_streaming_v1 import RealBackendDriftStreamV1
from dafr.adaptive_real_fixtures_v1 import build_fixture_checkpoints,forbid_replay_fitting,declared_failure
from dafr.interval_v1 import order_statistic
from dafr.real_adapters_v1 import RealAdapter,RealVersion
from dafr.run_m7b_v1 import events,run_case,verify_preservation,demonstrate,common_diagnostics
from dafr.audit_m7b_v1 import audit_backend_intervals
from dafr.audit_m7a_v1 import file_sha
from dafr.contracts_v2 import TickEventV2


class RealIntervalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();cls.root=Path(cls.tmp.name).resolve()
        cls.reference=build_fixture_checkpoints(cls.root/'checkpoints')
        cls.base=RealIntervalStreamingV1('integration',cls.reference)
        cls.rows=list(events('continuous'))[:220];cls.sim=copy.deepcopy(cls.base)
        with forbid_replay_fitting():cls.steps=[cls.sim.advance(*r) for r in cls.rows]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def engine(self):return copy.deepcopy(self.base)
    def available(self):return next(r for s in self.steps for r in s.intervals if r.status=='available')

    def test_real_adapter_and_contract_types(self):
        for a in self.sim._adapters.values():self.assertIs(type(a),RealAdapter)
        for r in self.steps[-1].intervals:
            self.assertIs(type(r),BackendIntervalRecordV1)
            if r.forecast.requested_metadata:self.assertIs(type(r.forecast.requested_metadata),RealVersion)

    def test_arbitrary_models_and_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):RealIntervalStreamingV1('bad',object())
        with self.assertRaises(ValueError):RealIntervalStreamingV1('bad',self.reference,1)

    def test_locks_and_frozen_nominals(self):
        c,_=load_m7b_config();self.assertEqual(c['nominal_percent'],[90,95])
        self.assertFalse(c['confirmation_execution_allowed']);self.assertFalse(c['m8_execution_allowed'])
        self.assertEqual(self.sim.calibrator.configuration['minimum_support'],100)

    def test_exact_quantile_from_matured_own_errors(self):
        r=next(r for r in self.steps[150].intervals if r.forecast.policy_id=='shadow_arima' and r.nominal_percent==95 and r.forecast.horizon==1)
        scores=[s.outcome.absolute_error for step in self.steps[:151] for s in step.scores if s.forecast.policy_id=='shadow_arima' and s.forecast.horizon==1]
        self.assertEqual((r.quantile_rank,r.radius),order_statistic(scores,95))

    def test_95_intervals_nest_90(self):
        for s in self.steps:
            pairs={}
            for r in s.intervals:pairs.setdefault(r.forecast.forecast_id,{})[r.nominal_percent]=r
            for p in pairs.values():
                a,b=p[90],p[95];self.assertEqual(a.support,b.support)
                if a.status=='available':self.assertLessEqual(b.lower,a.lower);self.assertGreaterEqual(b.upper,a.upper)

    def test_minimum_100_and_null_cold_start(self):
        rows=[r for s in self.steps for r in s.intervals if r.forecast.policy_id=='persistence' and r.forecast.horizon==1 and r.nominal_percent==90]
        self.assertEqual(next(r for r in rows if r.support.count==99).status,'insufficient_support')
        self.assertEqual(next(r for r in rows if r.status=='available').support.count,100)
        self.assertIsNone(rows[0].lower)

    def test_h12_delayed_calibration(self):
        self.assertFalse(any(c.forecast.horizon==12 for s in self.steps[:12] for c in s.scores))
        sample=next(c for c in self.steps[12].scores if c.forecast.horizon==12)
        self.assertEqual(sample.outcome.target-sample.forecast.origin,timedelta(minutes=60))

    def test_real_model_provenance_and_version_rejection(self):
        r=self.available();f=r.forecast
        real=next(r.forecast for r in self.steps[-1].intervals if r.forecast.policy_id=='shadow_arima')
        with self.assertRaises(ValueError):self.sim.calibrator._validate_registered(replace(real,requested_checkpoint_sha256='0'*64))
        with self.assertRaises(ValueError):self.sim.calibrator._validate_registered(replace(real,registry_sha256='0'*64))
        self.assertEqual(f.registry_sha256,self.reference.sha256)

    def test_separate_policy_horizon_support(self):
        rows=[r for r in self.steps[150].intervals if r.forecast.horizon==1 and r.nominal_percent==90]
        self.assertEqual(len({r.support.scores_sha256 for r in rows}),4)
        for r in rows:self.assertEqual(r.support.policy_id,r.forecast.policy_id)

    def test_pre_update_chronology_and_post_point_interval(self):
        for s in self.steps:
            kinds=[e.kind for e in s.timeline];first=kinds.index('adapter_update')
            self.assertLess(kinds.index('calibration_clock'),first)
            self.assertTrue(all(i<first for i,k in enumerate(kinds) if k.startswith('monitor_') or k in ('calibration_score','interval_outcome')))
            for i,e in enumerate(s.timeline):
                if e.kind=='interval_issuance':self.assertTrue(any(old.kind in ('issuance','unissued_attempt') and old.record.forecast_id==e.record.forecast.forecast_id for old in s.timeline[:i]))

    def test_each_backend_updates_once_per_tick(self):
        for s in self.steps:
            updates=[e for e in s.backend.events if e.kind=='adapter_update']
            self.assertEqual(len(updates),2)
            self.assertEqual({e.record.metadata.expert_id for e in updates},{'arima','xgboost'})

    def test_interval_on_off_and_old_m6b_full_point_parity(self):
        disabled=self.engine();disabled.intervals_enabled=False
        legacy=RealBackendDriftStreamV1('integration',self.reference)
        with forbid_replay_fitting():
            for row,a in zip(self.rows,self.steps):
                b=disabled.advance(*row);c=legacy.advance(*row)
                self.assertEqual(a.backend,b.backend);self.assertEqual(a.backend,c.backend)
                self.assertEqual(a.monitor_events,b.monitor_events)
                self.assertEqual([(e.kind,e.record) for e in a.monitor_events],[(e.kind,e.record) for e in c.monitor_events])

    def test_future_suffix_value_and_mask_invariance(self):
        a=self.engine();b=self.engine();previous=[]
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:140]):
                first=a.advance(*row);second=b.advance(*(row if i<125 else (row[0],None,'changed_suffix')))
                if i<125:self.assertEqual(first,second);previous.append(first)
        self.assertEqual(previous[0].intervals[0],a.calibrator.intervals[previous[0].intervals[0].forecast.forecast_id,90])

    def test_missing_exact_targets_and_reset_once(self):
        sim=self.engine();steps=[]
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:160]):steps.append(sim.advance(*(row if not 130<=i<136 else (row[0],None,'gap'))))
        resets=[i for i,s in enumerate(steps) if s.backend.reset]
        self.assertEqual(resets,[133])
        for s in steps[130:136]:
            self.assertFalse(s.scores)
            self.assertTrue(all(o.covered is None for o in s.interval_outcomes))
        self.assertTrue(any(not c.accepted_for_current_era for s in steps[136:] for c in s.scores))

    def test_leading_missing_abstention_and_no_borrowed_interval(self):
        sim=self.engine()
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:6]):s=sim.advance(row[0],None,'leading_gap')
        self.assertTrue(all(r.status=='center_unavailable' for r in s.intervals))

    def test_age_expiry_with_no_new_policy_errors(self):
        engine=copy.deepcopy(self.sim.calibrator)
        self.assertTrue(engine._buffers)
        start=self.rows[-1][0]
        for k in range(1,289):
            tick=TickEventV2('integration','synthetic_m5b1_v1','synthetic','expiry-'+str(k),100000+k,start+timedelta(minutes=5*k),40.)
            engine.clock(tick,0)
        self.assertTrue(all(not b for b in engine._buffers.values()))

    def test_forecast_failure_null_shadow_and_own_fallback_scores(self):
        sim=self.engine();steps=[]
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:130]):
                with declared_failure(sim,'gaps_failures',i):steps.append(sim.advance(*row))
        failed=[r for s in steps for r in s.intervals if r.forecast.availability=='numerical_failure']
        self.assertTrue(failed);self.assertTrue(all(r.status=='center_unavailable' for r in failed))
        fallback=[c for s in steps for c in s.scores if c.forecast.availability=='fallback']
        self.assertTrue(fallback);self.assertTrue(all(c.forecast.policy_id=='adaptive' for c in fallback))

    def test_update_failure_no_refit_and_monitor_continues(self):
        sim=self.engine()
        with forbid_replay_fitting():
            for i,row in enumerate(self.rows[:50]):
                with declared_failure(sim,'update_failure',i):s=sim.advance(*row)
        arima=next(r for r in s.intervals if r.forecast.policy_id=='shadow_arima')
        self.assertEqual(arima.status,'center_unavailable')
        self.assertTrue(any(e.kind=='reference_error_link' for e in s.monitor_events))

    def test_coverage_width_and_score_arithmetic(self):
        for s in self.steps:
            os={o.event_id:o for o in s.backend.outcomes}
            for o in s.interval_outcomes:
                if o.status=='scored':
                    r=self.sim.calibrator.intervals[o.forecast_id,o.nominal_percent];y=os[o.source_outcome_id].actual
                    self.assertEqual(o.covered,r.lower<=y<=r.upper);self.assertEqual(o.width,r.upper-r.lower)
                    self.assertEqual(o.interval_score,o.width+(200/(100-o.nominal_percent))*max(r.lower-y,0,y-r.upper))

    def test_pending_no_coverage_and_immutable_records(self):
        for r in self.steps[-1].intervals:
            if r.forecast.issued:self.assertNotIn(r.interval_id,self.sim.calibrator.outcomes)
        with self.assertRaises(FrozenInstanceError):self.available().lower=0

    def test_checkpoint_and_parameters_remain_fixed(self):
        for n,a in self.sim._adapters.items():self.assertEqual(a.parameter_sha256,self.base._parameters[n])
        self.assertEqual(file_sha(self.reference.path),self.reference.sha256)

    def test_common_target_denominators_are_identical(self):
        rows=common_diagnostics('continuous',self.steps)
        for h in (1,12):
            for p in (90,95):self.assertEqual(len({r['common_genuine_available_count'] for r in rows if r['horizon']==h and r['nominal_percent']==p}),1)

    def test_real_adaptive_switch_retains_complete_policy_support(self):
        sim=self.engine();switches=[]
        with forbid_replay_fitting():
            for i,row in enumerate(events('gaps_failures')):
                with declared_failure(sim,'gaps_failures',i):step=sim.advance(*row)
                for selection in step.backend.selections:
                    if selection.switched:
                        switches.append(selection)
                        rows=[r for r in step.intervals if r.forecast.policy_id=='adaptive' and r.forecast.horizon==selection.horizon]
                        self.assertTrue(all(r.support.policy_id=='adaptive' for r in rows))
                        self.assertTrue(all(r.support.count>0 for r in rows))
        self.assertTrue(switches)

    def test_saved_audit_and_nesting_tamper_rejection(self):
        with TemporaryDirectory() as temp:
            p=Path(temp)/'run';run_case(p,self.reference,'update_failure')
            self.assertEqual(audit_backend_intervals(p)['status'],'passed')
            with (p/'intervals.jsonl').open('a') as out:out.write('tamper')
            with self.assertRaises(ValueError):audit_backend_intervals(p)

    def test_no_overwrite_case(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError):run_case(Path(temp),self.reference,'continuous')

    def test_no_overwrite_run_before_execution(self):
        p=ROOT/'data/processed/dafr/m7b_synthetic_backend_v1/test-existing-m7b';p.mkdir(parents=True,exist_ok=False)
        try:
            with patch('dafr.run_m7b_v1.build_fixture_checkpoints') as build:
                with self.assertRaises(FileExistsError):demonstrate(p.name)
                build.assert_not_called()
        finally:p.rmdir()

    def test_no_new_observation_reads(self):
        original=Path.open;blocked=[]
        def guarded(path,*a,**kw):
            if any(s in str(path.resolve()) for s in ('/data/raw/','/data/external/','five_minute_prefix','confirmation_suffix')):
                blocked.append(str(path));raise AssertionError('Restricted observations')
            return original(path,*a,**kw)
        with patch.object(Path,'open',guarded):
            sim=self.engine();sim.advance(*self.rows[0])
        self.assertEqual(blocked,[])

    def test_all_historical_hashes_and_checkpoint_fingerprints(self):
        d=verify_preservation();self.assertEqual(d['historical_hashes_verified'],882)
        self.assertEqual(d['checkpoints']['checkpoint_files_verified'],27)


if __name__=='__main__':unittest.main()
