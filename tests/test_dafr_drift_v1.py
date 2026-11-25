"""M6A deterministic synthetic-only recurrence, causal integration and audits."""
from dataclasses import replace,FrozenInstanceError
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,json,sys,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.contracts_v2 import ForecastRecordV2,TargetOutcomeV2
from dafr.drift_contracts_v1 import GenuineReferenceErrorV1
from dafr.drift_v1 import PageHinkleyErrorV1,DriftConfigV1,load_drift_config
from dafr.drift_streaming_v1 import SyntheticDriftStreamV1
from dafr.drift_fixtures_v1 import FIXTURES,START,fixture_events
from dafr.run_m6a_v1 import run_case,verify_case,verify_history,sha
from dafr.streaming_v2 import StreamingSimulatorV2


def ts(i):return START+timedelta(minutes=5*i)


def error_sample(i,error=1.,h=1,era=0):
    issued=10000+(i-h)*100+10;arrival=10000+i*100+1
    f=ForecastRecordV2(f'source-{h}-{i}','unit','synthetic_errors','synthetic_machine','persistence','rule_v2',
        ts(i-h),ts(i),h,issued,f'tick-{i-h+1000}',issued-1,era,'a'*64,True,'baseline','persistence','rule_v2',40.,
        'persistence_reference',ts(i-h),0)
    o=TargetOutcomeV2(f'outcome-{h}-{i}',arrival+1,f.forecast_id,f'tick-{i+1000}',f.run_id,f.dataset_id,f.machine_id,
        f.policy_id,f.policy_version,h,f.origin,f.target,f.sequence,arrival,era,'scored',40.,40.+error,error,error,error*error)
    return GenuineReferenceErrorV1(f,o)


def unit_detector(n=80,h=1):
    d=PageHinkleyErrorV1(h,'e'*64)
    for i in range(n):d.clock(ts(i),0);d.observe(error_sample(i,h=h))
    return d


def replay(spec):
    s=SyntheticDriftStreamV1('synthetic_test',spec.failure_origins)
    steps=tuple(s.advance(*row) for row in fixture_events(spec))
    return s,steps


class DriftCoreTests(unittest.TestCase):
    def test_frozen_config_and_research_locks(self):
        c,h=load_drift_config();self.assertEqual(c.minimum_recent_errors,64)
        with self.assertRaises(ValueError):DriftConfigV1(alarm_threshold=7.)
        with self.assertRaises(ValueError):DriftConfigV1(normalization_samples=True)
        with TemporaryDirectory() as t:
            p=Path(t)/'config.json';v=json.loads((ROOT/'configs/dafr_m6a_synthetic_v1.json').read_text());v['real_data_execution_allowed']=True;p.write_text(json.dumps(v))
            with self.assertRaises(ValueError):load_drift_config(p)
    def test_invalid_horizon_or_digest_rejected(self):
        for h in (True,0,2,12.):
            with self.assertRaises(ValueError):PageHinkleyErrorV1(h,'e'*64)
        with self.assertRaises(ValueError):PageHinkleyErrorV1(1,'wrong')
    def test_normalization_requires_32_genuine_errors(self):
        d=unit_detector(31);self.assertIsNone(d.center)
        d.clock(ts(31),0);r=d.observe(error_sample(31))
        self.assertEqual(r.snapshot.normalization_count,32);self.assertEqual(r.snapshot.status,'normalization_frozen')
        self.assertEqual((d.center,d.scale),(1.,.1));self.assertFalse(r.alerts)
    def test_robust_median_and_mad_floor(self):
        d=PageHinkleyErrorV1(1,'e'*64)
        for i in range(32):d.clock(ts(i),0);d.observe(error_sample(i,10. if i==7 else 1.))
        self.assertEqual(d.center,1.);self.assertEqual(d.scale,.1);self.assertEqual(d.warm_clips,1)
    def test_hand_computed_ph_recurrence(self):
        d=unit_detector(32);d.clock(ts(32),0);u=d.observe(error_sample(32,1.1)).snapshot
        self.assertAlmostEqual(u.normalized_input,1.);self.assertAlmostEqual(u.running_mean,1./33)
        self.assertAlmostEqual(u.statistic,1.-1./33-.05);self.assertEqual(u.status,'warming_support')
    def test_no_alert_before_64_recent_genuine_errors(self):
        d=PageHinkleyErrorV1(1,'e'*64)
        for i in range(63):
            d.clock(ts(i),0);u=d.observe(error_sample(i,1. if i<32 else 1.4));self.assertFalse(u.alerts)
        d.clock(ts(63),0);u=d.observe(error_sample(63,1.4))
        self.assertEqual(u.snapshot.recent_genuine_errors,64);self.assertTrue(any(a.kind=='statistical_alarm' for a in u.alerts))
    def test_future_error_rejected_before_mutation(self):
        d=unit_detector();d.clock(ts(80),0);before=d.snapshot()
        with self.assertRaises(ValueError):d.observe(error_sample(81))
        self.assertEqual(before,d.snapshot())
    def test_wrong_horizon_and_arbitrary_error_rejected(self):
        d=unit_detector();d.clock(ts(80),0)
        with self.assertRaises(ValueError):d.observe(error_sample(80,h=12))
        with self.assertRaises(ValueError):d.observe(0.)
    def test_duplicate_sample_and_clock_rejected(self):
        d=unit_detector();d.clock(ts(80),0);d.observe(error_sample(80))
        with self.assertRaises(ValueError):d.observe(error_sample(80))
        with self.assertRaises(ValueError):d.clock(ts(80),0)
        with self.assertRaises(ValueError):d.clock(ts(82),0)
    def test_stream_identity_cannot_change(self):
        d=unit_detector();d.clock(ts(80),0);sample=error_sample(80)
        other=GenuineReferenceErrorV1(replace(sample.forecast,run_id='another_run'),replace(sample.outcome,run_id='another_run'))
        with self.assertRaises(ValueError):d.observe(other)
    def test_missing_target_is_not_a_zero_error(self):
        sample=error_sample(80)
        missing=replace(sample.outcome,status='target_unavailable',actual=None,signed_error=None,absolute_error=None,squared_error=None)
        with self.assertRaises(ValueError):GenuineReferenceErrorV1(sample.forecast,missing)
    def test_wrong_source_prediction_or_version_rejected(self):
        s=error_sample(80)
        with self.assertRaises(ValueError):GenuineReferenceErrorV1(replace(s.forecast,predicted_value=41.),s.outcome)
        with self.assertRaises(ValueError):GenuineReferenceErrorV1(replace(s.forecast,policy_version='changed'),s.outcome)
    def test_normalization_frozen_after_prefix(self):
        d=unit_detector();m,s=d.center,d.scale
        for i in range(80,100):d.clock(ts(i),0);d.observe(error_sample(i,10.))
        self.assertEqual((d.center,d.scale),(m,s));self.assertEqual(len(d._normalization),32)
    def test_clipping_logged_including_cooldown(self):
        d=unit_detector();d.clock(ts(80),0);u=d.observe(error_sample(80,10.))
        self.assertTrue(u.snapshot.clipped);self.assertEqual(u.snapshot.normalized_input,4.)
        self.assertEqual(u.snapshot.clipped_monitor_updates,1)
    def test_cooldown_suppresses_warnings_and_alarms(self):
        d=unit_detector();first=None
        for i in range(80,150):
            d.clock(ts(i),0);u=d.observe(error_sample(i,2.))
            if first is None and any(a.kind=='statistical_alarm' for a in u.alerts):first=i
            elif first is not None and i<first+24:
                self.assertFalse(u.alerts);self.assertEqual(u.snapshot.status,'cooldown');self.assertEqual(u.snapshot.statistic,0.)
        self.assertIsNotNone(first)
    def test_cooldown_uses_elapsed_ticks_not_error_count(self):
        d=unit_detector();i=80
        while True:
            d.clock(ts(i),0);u=d.observe(error_sample(i,2.))
            if any(a.kind=='statistical_alarm' for a in u.alerts):break
            i+=1
        for j in range(i+1,i+25):d.clock(ts(j),0)
        self.assertFalse(d.in_cooldown);self.assertGreaterEqual(len(d.recent),64)
    def test_support_expiry_without_inserting_errors(self):
        d=unit_detector()
        for i in range(80,370):d.clock(ts(i),0)
        self.assertEqual(len(d.recent),0);self.assertEqual(d.era_errors,80);self.assertEqual(d.statistic,0.)
        self.assertEqual(d.center,1.)
    def test_era_reset_clears_all_active_state(self):
        d=unit_detector();d.clock(ts(80),1)
        self.assertEqual(len(d.recent),0);self.assertEqual(d.era_errors,0);self.assertIsNone(d.center)
        self.assertIsNone(d.cooldown_until);self.assertEqual(d.lifetime_errors,80)
    def test_old_era_error_is_audited_but_ignored(self):
        d=unit_detector();d.clock(ts(80),1);u=d.observe(error_sample(80,era=0))
        self.assertEqual(u.snapshot.status,'old_era_ignored');self.assertEqual(d.era_errors,0)
        self.assertEqual(len(d._normalization),0);self.assertEqual(d.ignored_old_errors,1)
    def test_bounded_state_and_independent_horizon_normalization(self):
        a=unit_detector(400);b=PageHinkleyErrorV1(12,'e'*64)
        for i in range(70):b.clock(ts(i),0);b.observe(error_sample(i,3.,12))
        self.assertEqual(len(a.recent),288);self.assertEqual(len(a._normalization),32)
        self.assertEqual(a.center,1.);self.assertEqual(b.center,3.)
    def test_snapshots_and_alerts_are_immutable(self):
        d=unit_detector();snap=d.snapshot()
        with self.assertRaises(FrozenInstanceError):snap.statistic=0
        alert=None
        for i in range(80,90):
            d.clock(ts(i),0);u=d.observe(error_sample(i,2.))
            if u.alerts:alert=u.alerts[0];break
        self.assertIsNotNone(alert)
        with self.assertRaises(FrozenInstanceError):alert.threshold=0


class DriftIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.runs={s.name:replay(s) for s in FIXTURES}
    def test_stable_fixture_false_alarms_recorded(self):
        s,steps=self.runs['stable_errors'];self.assertFalse(any(x.alerts for x in steps))
    def test_sustained_error_increase_detected_after_intervention(self):
        s,steps=self.runs['sustained_error_increase']
        for h in (1,12):
            alarms=[a for step in steps for a in step.alerts if a.horizon==h and a.kind=='statistical_alarm']
            self.assertTrue(alarms);self.assertTrue(all(a.available_at>=ts(160) for a in alarms))
    def test_isolated_outlier_not_automatically_called_drift(self):
        s,steps=self.runs['isolated_outlier']
        self.assertFalse(any(a.kind=='statistical_alarm' for step in steps for a in step.alerts))
        self.assertTrue(any(s.clipped for step in steps for s in step.snapshots))
    def test_gradual_change_and_level_step_remain_distinct_fixtures(self):
        self.assertEqual(next(s for s in FIXTURES if s.name=='gradual_change').change_kind,'gradual_slope_increase')
        self.assertEqual(next(s for s in FIXTURES if s.name=='abrupt_level_change').change_kind,'level_step_error_transient')
        _,steps=self.runs['abrupt_level_change']
        self.assertFalse(any(a.horizon==1 and a.kind=='statistical_alarm' for step in steps for a in step.alerts))
    def test_delayed_h12_input(self):
        s,steps=self.runs['delayed_h12']
        self.assertTrue(all(o.horizon==1 for step in steps[:12] for o in step.outcomes))
        self.assertEqual(s.detectors[1].lifetime_errors,39);self.assertEqual(s.detectors[12].lifetime_errors,28)
    def test_no_insufficient_support_alerts(self):
        _,steps=self.runs['insufficient_support'];self.assertFalse(any(x.alerts for x in steps))
    def test_every_alert_has_genuine_matured_source(self):
        for s,steps in self.runs.values():
            for step in steps:
                outcomes={o.event_id:o for o in step.outcomes}
                for alert in step.alerts:
                    self.assertIn(alert.source_outcome_id,outcomes);self.assertEqual(outcomes[alert.source_outcome_id].status,'scored')
                    self.assertEqual(alert.available_at,step.tick.timestamp);self.assertGreaterEqual(alert.genuine_support,64)
                    self.assertGreaterEqual(alert.statistic,alert.threshold)
                    self.assertEqual(alert.telemetry_era,s.ledger._decisions[outcomes[alert.source_outcome_id].forecast_id].era)
    def test_missing_targets_never_produce_detector_updates(self):
        _,steps=self.runs['missing_observations']
        for step in steps:
            if not step.tick.genuine:
                self.assertFalse(step.snapshots);self.assertFalse(step.alerts)
                self.assertTrue(all(o.absolute_error is None for o in step.outcomes))
    def test_fourth_missing_reset_exactly_once_per_long_gap(self):
        s,steps=self.runs['four_tick_resets']
        self.assertEqual([i for i,x in enumerate(steps) if x.reset],[3,148,223,279])
        self.assertTrue(all(d.center is None and len(d.recent)==0 for d in s.detectors.values()))
    def test_old_era_scores_do_not_seed_new_detector(self):
        s,steps=self.runs['four_tick_resets']
        self.assertTrue(any(x.status=='old_era_ignored' for step in steps for x in step.snapshots))
        self.assertGreater(sum(d.ignored_old_errors for d in s.detectors.values()),0)
    def test_reference_failure_has_no_fabricated_loss(self):
        s,steps=self.runs['forecast_failure'];failed={f.forecast_id for step in steps for f in step.decisions if f.reason=='reference_numeric_failure'}
        self.assertEqual(len(failed),6)
        self.assertFalse(any(o.forecast_id in failed for o in s.ledger.outcomes))
        self.assertTrue(all(f.predicted_value is None for step in steps for f in step.decisions if f.forecast_id in failed))
    def test_cooldown_spacing_in_elapsed_grid_ticks(self):
        _,steps=self.runs['cooldown_stress']
        for h in (1,12):
            alarms=[a for step in steps for a in step.alerts if a.kind=='statistical_alarm' and a.horizon==h]
            self.assertGreater(len(alarms),1)
            self.assertTrue(all(b.available_at-a.available_at>=timedelta(minutes=120) for a,b in zip(alarms,alarms[1:])))
    def test_monitor_never_changes_reference_predictions_or_selector(self):
        spec=next(s for s in FIXTURES if s.name=='sustained_error_increase');new,steps=self.runs[spec.name]
        old=StreamingSimulatorV2('old','synthetic_old')
        for row,step in zip(fixture_events(spec),steps):
            prior=old.advance(*row)
            self.assertEqual([(f.horizon,f.predicted_value,f.availability) for f in prior.decisions],[(f.horizon,f.predicted_value,f.availability) for f in step.decisions])
        self.assertFalse(hasattr(new,'selector'))
    def test_future_suffix_value_and_missingness_invariance(self):
        a=SyntheticDriftStreamV1('same');b=SyntheticDriftStreamV1('same');aa=[];bb=[]
        for i in range(130):
            aa.append(a.advance(ts(i),20+.1*i));v=20+.1*i if i<100 else None
            bb.append(b.advance(ts(i),v,'changed_future' if v is None else None))
        self.assertEqual(aa[:100],bb[:100]);self.assertNotEqual(aa[100:],bb[100:])
    def test_reveal_score_monitor_issue_event_order(self):
        for s,steps in self.runs.values():
            previous=0
            for step in steps:
                seq=[e.sequence for e in step.events];self.assertEqual(seq,sorted(set(seq)));self.assertGreater(seq[0],previous);previous=seq[-1]
                issued=min(f.sequence for f in step.decisions)
                self.assertTrue(all(e.sequence<issued for e in step.events if e.kind in ('detector_update','statistical_alarm','warning_entered')))
    def test_boundary_forecasts_remain_pending(self):
        s,steps=self.runs['stable_errors'];self.assertEqual(len(s.ledger.pending_ids),13)
        self.assertTrue(all(o.target<=steps[-1].tick.timestamp for o in s.ledger.outcomes))
    def test_no_arbitrary_fixture_or_model_objects(self):
        with self.assertRaises(ValueError):list(fixture_events(object()))
        with self.assertRaises(ValueError):SyntheticDriftStreamV1('bad',failure_origins=[1])
    def test_new_pipeline_does_not_read_real_data_or_models(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            mode=args[0] if args else kwargs.get('mode','r')
            if 'r' in mode and (path.is_relative_to(ROOT/'data') or path.is_relative_to(ROOT/'models')):raise AssertionError('Real data read')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):replay(next(s for s in FIXTURES if s.name=='stable_errors'))
    def test_no_overwrite_failed_and_successful_runs(self):
        spec=next(s for s in FIXTURES if s.name=='delayed_h12')
        with TemporaryDirectory() as temp:
            directory=Path(temp).resolve()/'case';run_case(directory,spec)
            hashes={p.name:sha(p) for p in directory.iterdir()}
            with self.assertRaises(FileExistsError):run_case(directory,spec)
            self.assertEqual(hashes,{p.name:sha(p) for p in directory.iterdir()})
            failed=directory.parent/'failed'
            with patch('dafr.run_m6a_v1.fixture_events',side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):run_case(failed,spec)
            self.assertEqual(json.loads((failed/'completion.json').read_text())['status'],'failed')
            with self.assertRaises(FileExistsError):run_case(failed,spec)
    def test_saved_event_audit_and_tamper_rejection(self):
        spec=next(s for s in FIXTURES if s.name=='sustained_error_increase')
        with TemporaryDirectory() as temp:
            d=Path(temp).resolve()/'case';run_case(d,spec);self.assertTrue(verify_case(d,spec)['passed'])
            p=d/'outcomes.jsonl';lines=p.read_text().splitlines();o=json.loads(lines[0]);o['actual']+=1;lines[0]=json.dumps(o);p.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(ValueError):verify_case(d,spec)
    def test_historical_hashes_preserved(self):self.assertEqual(verify_history(),571)


if __name__=='__main__':unittest.main()
