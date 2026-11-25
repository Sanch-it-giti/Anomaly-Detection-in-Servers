"""M7A synthetic chronology, exact quantiles, attribution and saved audits."""
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
from dafr.interval_v1 import RollingIntervalsV1,order_statistic,load_interval_config
from dafr.interval_streaming_v1 import SyntheticIntervalStreamV1
from dafr.interval_fixtures_v1 import FIXTURES,fixture_events,fixture_specs
from dafr.interval_contracts_v1 import CalibrationScoreV1,IntervalRecordV1,IntervalOutcomeV1
from dafr.audit_m7a_v1 import audit_interval_run
from dafr.run_m7a_v1 import run_case,verify_preservation,demonstrate
from dafr.drift_fixtures_v1 import START
from dafr.contracts_v2 import TickEventV2


def spec(name):return next(s for s in FIXTURES if s.name==name)
def replay(name):
    s=spec(name);sim=SyntheticIntervalStreamV1(name,fixture_specs(s))
    return sim,[sim.advance(*row) for row in fixture_events(s)]


class IntervalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.sim,cls.steps=replay('stable')
    def available(self):return next(r for s in self.steps for r in s.intervals if r.status=='available')

    def test_original_protocol_requires_both_nominal_levels(self):
        c,_=load_interval_config();self.assertEqual(c['nominal_percent'],[90,95])
        self.assertEqual((c['minimum_support'],c['capacity'],c['recency_grid_ticks']),(100,288,288))
        self.assertFalse(c['confirmation_execution_allowed'])

    def test_exact_order_statistic_not_interpolation(self):
        self.assertEqual(order_statistic(range(100),90),(91,90))
        self.assertEqual(order_statistic(range(100),95),(96,95))

    def test_integer_boundary_without_float_ceil_error(self):
        self.assertEqual(order_statistic(range(119),95),(114,113))

    def test_rank_exceeding_available_scores(self):
        self.assertEqual(order_statistic(range(10),95),(11,None))
        self.assertEqual(order_statistic([],90),(1,None))

    def test_invalid_quantile_inputs_rejected(self):
        for errors,p in (([float('nan')],90),([-1],90),([True],90),([1],91),([1],True)):
            with self.assertRaises(ValueError):order_statistic(errors,p)

    def test_minimum_support_is_100_not_99(self):
        for h in (1,12):
            rows=[r for s in self.steps for r in s.intervals if r.forecast.policy_id=='persistence' and r.forecast.horizon==h and r.nominal_percent==90]
            self.assertEqual(next(r for r in rows if r.support.count==99).status,'insufficient_support')
            self.assertEqual(next(r for r in rows if r.status=='available').support.count,100)

    def test_separate_h12_feedback_and_exact_target(self):
        scores=[score for s in self.steps[:12] for score in s.scores if score.forecast.horizon==12]
        self.assertEqual(scores,[])
        first=next(score for score in self.steps[12].scores if score.forecast.horizon==12)
        self.assertEqual(first.outcome.target-first.forecast.origin,timedelta(minutes=60))
        for s in self.steps:
            for r in s.intervals:self.assertLessEqual(r.support.latest_target or r.forecast.origin,r.forecast.origin)

    def test_policy_buffers_do_not_pool_shadow_adaptive_persistence(self):
        rows=[r for r in self.steps[200].intervals if r.nominal_percent==90 and r.forecast.horizon==12]
        self.assertEqual(len(rows),4)
        self.assertEqual(len({r.support.scores_sha256 for r in rows}),4)
        for r in rows:self.assertEqual(r.support.policy_id,r.forecast.policy_id)

    def test_both_levels_share_scores_and_nested_raw_bounds(self):
        for s in self.steps:
            for f in s.source.decisions:
                a=self.sim.engine.intervals[f.forecast_id,90];b=self.sim.engine.intervals[f.forecast_id,95]
                self.assertEqual(a.support,b.support)
                if a.status=='available':self.assertLessEqual(b.lower,a.lower);self.assertGreaterEqual(b.upper,a.upper)

    def test_own_policy_fallback_not_borrowed_expert_interval(self):
        _,steps=replay('numerical_failures')
        fallbacks=[r for s in steps for r in s.intervals if r.forecast.availability=='fallback']
        self.assertTrue(fallbacks)
        for r in fallbacks:self.assertEqual(r.support.policy_id,'adaptive')
        scores=[c for s in steps for c in s.scores if c.forecast.availability=='fallback']
        self.assertTrue(scores);self.assertTrue(all(c.forecast.policy_id=='adaptive' for c in scores))

    def test_numerical_failures_have_no_expert_interval(self):
        _,steps=replay('numerical_failures')
        failures=[r for s in steps for r in s.intervals if r.forecast.availability=='numerical_failure']
        self.assertTrue(failures)
        for r in failures:self.assertEqual(r.status,'center_unavailable');self.assertIsNone(r.lower)

    def test_raw_bounds_are_not_clipped_to_cpu_range(self):
        r=self.available();center=r.forecast.predicted_value
        raw=replace(r,radius=100.,lower=center-100.,upper=center+100.)
        self.assertLess(raw.lower,0);self.assertGreater(raw.upper,100)
        self.assertEqual(raw.upper-raw.lower,200.)
        with self.assertRaises(ValueError):replace(raw,clipping='cpu_clipped')

    def test_genuine_coverage_width_and_interval_score(self):
        for s in self.steps:
            source={o.event_id:o for o in s.source.outcomes}
            for o in s.interval_outcomes:
                if o.status=='scored':
                    r=self.sim.engine.intervals[o.forecast_id,o.nominal_percent];y=source[o.source_outcome_id].actual
                    self.assertEqual(o.covered,r.lower<=y<=r.upper)
                    self.assertEqual(o.width,r.upper-r.lower)
                    self.assertEqual(o.interval_score,o.width+(200/(100-o.nominal_percent))*max(r.lower-y,0,y-r.upper))

    def test_zero_residual_and_zero_width_valid(self):
        self.assertEqual(order_statistic([0.]*100,90),(91,0.))
        r=self.available();zero=replace(r,radius=0.,lower=r.forecast.predicted_value,upper=r.forecast.predicted_value)
        self.assertEqual(zero.upper-zero.lower,0)

    def test_missing_targets_have_no_error_or_coverage(self):
        _,steps=replay('short_gaps')
        for s in steps:
            if not s.source.tick.genuine:
                self.assertEqual(s.scores,())
                for o in s.interval_outcomes:self.assertEqual(o.status,'target_unavailable');self.assertIsNone(o.covered)

    def test_long_gap_reset_once_and_genuine_recovery(self):
        sim,steps=replay('long_gap_recovery')
        resets=[i for i,s in enumerate(steps) if s.calibration_clock['reset']]
        self.assertEqual(resets,[3,173,357])
        for i in resets:
            self.assertTrue(all(r.support.count==0 for r in steps[i].intervals))
        self.assertTrue(any(r.status=='available' for s in steps[300:354] for r in s.intervals))
        self.assertTrue(all(r.support.count==0 for r in steps[-1].intervals))

    def test_old_era_genuine_errors_do_not_seed_new_support(self):
        _,steps=replay('long_gap_recovery')
        ignored=[c for s in steps for c in s.scores if not c.accepted_for_current_era]
        self.assertTrue(ignored)
        for s in steps:
            for c in s.scores:
                if not c.accepted_for_current_era:self.assertLess(c.forecast.era,s.intervals[0].support.era)

    def test_all_missing_stream_abstains_without_intervals(self):
        sim=SyntheticIntervalStreamV1('all_missing')
        for i in range(15):
            s=sim.advance(START+timedelta(minutes=5*i),None,'gap')
            self.assertEqual(s.scores,());self.assertTrue(all(r.status=='center_unavailable' for r in s.intervals))
        self.assertEqual(sim.engine.outcomes,{})

    def test_cold_start_and_insufficient_support_preserve_centers(self):
        _,steps=replay('insufficient_support')
        for s in steps:
            for r in s.intervals:
                self.assertNotEqual(r.status,'available')
                if r.forecast.issued:self.assertIsNotNone(r.forecast.predicted_value)

    def test_boundary_pending_forecasts_never_have_coverage(self):
        last=self.steps[-1]
        for r in last.intervals:
            if r.forecast.issued:self.assertNotIn(r.interval_id,self.sim.engine.outcomes)

    def test_age_expiry_during_continuous_telemetry_and_failures(self):
        _,steps=replay('calibration_expiry')
        self.assertFalse(any(s.calibration_clock['reset'] for s in steps))
        expired=sum(s.calibration_clock['expired_scores'] for s in steps)
        self.assertGreater(expired,0)
        recovered=[r for r in steps[450].intervals if r.forecast.policy_id.startswith('shadow_')]
        self.assertTrue(all(r.status=='insufficient_support' for r in recovered))

    def test_capacity_and_elapsed_recency(self):
        for s in self.steps:
            for r in s.intervals:
                self.assertLessEqual(r.support.count,288)
                if r.support.oldest_target:self.assertLessEqual(r.forecast.origin-r.support.oldest_target,timedelta(minutes=5*287))

    def test_intervals_do_not_change_forecasts_selector_or_drift(self):
        disabled=SyntheticIntervalStreamV1('stable',enabled=False)
        for row,expected in zip(fixture_events(spec('stable')),self.steps):
            actual=disabled.advance(*row)
            self.assertEqual(actual.source,expected.source);self.assertEqual(actual.drift,expected.drift)
            self.assertEqual(actual.intervals,())

    def test_future_suffix_values_and_masks_cannot_change_prefix(self):
        a=SyntheticIntervalStreamV1('future');b=copy.deepcopy(a)
        for i,row in enumerate(fixture_events(spec('stable'))):
            first=a.advance(*row);second=b.advance(*(row if i<140 else (row[0],None,'perturbed')))
            if i<140:self.assertEqual(first,second)

    def test_interval_and_support_are_immutable(self):
        r=self.available()
        with self.assertRaises(FrozenInstanceError):r.lower=0
        with self.assertRaises(FrozenInstanceError):r.support.count=999

    def test_interval_contract_rejects_future_pooled_or_wrong_bounds(self):
        r=self.available()
        with self.assertRaises(ValueError):replace(r,lower=r.lower-1)
        with self.assertRaises(ValueError):replace(r,support=replace(r.support,policy_id='other'))
        with self.assertRaises(ValueError):replace(r.support,latest_target=r.forecast.target)

    def test_error_contract_rejects_missing_or_foreign_link(self):
        score=next(c for s in self.steps for c in s.scores)
        with self.assertRaises(ValueError):CalibrationScoreV1(score.forecast,replace(score.outcome,forecast_id='other'),True)

    def test_clock_requires_cadence_and_exact_telemetry_era(self):
        e=RollingIntervalsV1();tick=self.steps[0].source.tick;e.clock(tick,0)
        with self.assertRaises(ValueError):e.clock(tick,0)
        with self.assertRaises(ValueError):e.clock(replace(tick,timestamp=tick.timestamp+timedelta(minutes=5)),1)

    def test_duplicate_issuance_and_late_feedback_rejected(self):
        e=RollingIntervalsV1();s=self.steps[0];e.clock(s.source.tick,0);f=s.source.decisions[0];e.issue(f)
        with self.assertRaises(ValueError):e.issue(f)
        score=next(c for s in self.steps for c in s.scores)
        with self.assertRaises(ValueError):e.mature(score.forecast,score.outcome)

    def test_future_h12_and_duplicate_matured_feedback_rejected(self):
        e=RollingIntervalsV1();first=self.steps[0]
        e.clock(first.source.tick,0)
        for f in first.source.decisions:e.issue(f)
        future=next(c for c in self.steps[12].scores if c.forecast.horizon==12)
        e.clock(self.steps[1].source.tick,0)
        with self.assertRaises(ValueError):e.mature(future.forecast,future.outcome)
        current=next(c for c in self.steps[1].scores if c.forecast.policy_id=='persistence')
        e.mature(current.forecast,current.outcome)
        with self.assertRaises(ValueError):e.mature(current.forecast,current.outcome)

    def test_model_version_change_does_not_inherit_calibration(self):
        e=RollingIntervalsV1();first=self.steps[0];e.clock(first.source.tick,0)
        f=next(f for f in first.source.decisions if f.policy_id=='shadow_arima');e.issue(f)
        second=self.steps[1];e.clock(second.source.tick,0)
        f=next(f for f in second.source.decisions if f.policy_id=='shadow_arima')
        changed=replace(f,requested_metadata=replace(f.requested_metadata,version='changed_model'))
        with self.assertRaises(ValueError):e.issue(changed)

    def test_wrong_actual_observation_cannot_enter_calibration(self):
        e=RollingIntervalsV1();e.clock(self.steps[0].source.tick,0)
        score=next(c for c in self.steps[1].scores if c.forecast.policy_id=='persistence')
        e.issue(score.forecast);e.clock(self.steps[1].source.tick,0)
        o=score.outcome;error=o.signed_error+1
        wrong=replace(o,actual=o.actual+1,signed_error=error,absolute_error=abs(error),squared_error=error*error)
        with self.assertRaises(ValueError):e.mature(score.forecast,wrong)
        self.assertEqual(len(e._buffers),0)

    def test_duplicate_policy_origin_under_new_id_rejected(self):
        e=RollingIntervalsV1();e.clock(self.steps[0].source.tick,0)
        f=self.steps[0].source.decisions[0];e.issue(f)
        with self.assertRaises(ValueError):e.issue(replace(f,forecast_id='different_id'))

    def test_no_missing_coverage_can_be_fabricated(self):
        with self.assertRaises(ValueError):IntervalOutcomeV1('i','o','f',START,90,'target_unavailable',True,0.,0.)

    def test_saved_independent_audit_and_hash_tampering(self):
        with TemporaryDirectory() as temp:
            p=Path(temp)/'run';run_case(p,spec('stable'));result=audit_interval_run(p)
            self.assertEqual(result['status'],'passed')
            with (p/'intervals.jsonl').open('a') as out:out.write('tamper')
            with self.assertRaises(ValueError):audit_interval_run(p)

    def test_saved_audit_rejects_wrong_quantile_even_rehashed(self):
        from dafr.audit_m7a_v1 import file_sha
        with TemporaryDirectory() as temp:
            p=Path(temp)/'run';run_case(p,spec('stable'))
            lines=[json.loads(s) for s in (p/'intervals.jsonl').read_text().splitlines()]
            row=next(r for r in lines if r['status']=='available');row['quantile_rank']-=1
            (p/'intervals.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in lines))
            pins=json.loads((p/'hashes.json').read_text());pins['intervals.jsonl']=file_sha(p/'intervals.jsonl');(p/'hashes.json').write_text(json.dumps(pins))
            with self.assertRaises(ValueError):audit_interval_run(p)

    def test_exclusive_case_output(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError):run_case(Path(temp),spec('stable'))

    def test_exclusive_top_level_run_before_execution(self):
        p=ROOT/'data/processed/dafr/m7a_synthetic_v1/test-existing-m7a';p.mkdir(parents=True,exist_ok=False)
        try:
            with patch('dafr.run_m7a_v1.run_case') as case:
                with self.assertRaises(FileExistsError):demonstrate(p.name)
                case.assert_not_called()
        finally:p.rmdir()

    def test_no_dataset_or_model_loading_by_interval_driver(self):
        original=Path.open;seen=[]
        def guarded(path,*args,**kwargs):
            name=str(path.resolve())
            if '/data/' in name or path.suffix in ('.csv','.pkl','.ubj'):
                seen.append(name);raise AssertionError('Real observation/model access prohibited')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):
            sim=SyntheticIntervalStreamV1('isolated')
            for row in list(fixture_events(spec('stable')))[:2]:sim.advance(*row)
        self.assertEqual(seen,[])

    def test_historical_hashes_and_checkpoint_bytes(self):
        r=verify_preservation();self.assertEqual(r['historical_hashes'],739)
        self.assertEqual(r['historical_checkpoint_files'],27);self.assertFalse(r['historical_models_loaded'])


if __name__=='__main__':unittest.main()
