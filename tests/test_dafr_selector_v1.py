"""M5A synthetic-only selector tests. No real-data outcomes inform settings."""
from collections import deque
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.adapters_v1 import MockAdapterSpec,ModelVersionV1,MockAdapterV1
from dafr.contracts_v2 import TickEventV2,CausalContextV2,TargetOutcomeV2
from dafr.selector_contracts_v1 import MatchedLossV1,SyntheticForecastV1
from dafr.selector_v1 import MatchedSelectorV1,SelectorConfigV1,load_selector_config
from dafr.selector_streaming_v1 import SelectorStreamingV1,SyntheticLedgerV1,run_synthetic,synthetic_events,mock_specs
from dafr.run_m5a_v1 import verify_synthetic_run

START=datetime(2026,1,1,tzinfo=timezone.utc)
def ts(i):return START+timedelta(minutes=5*i)
def replay(values,specs=None):
    s=SelectorStreamingV1('test_m5a',specs);steps=[]
    for i,v in enumerate(values):steps.append(s.advance(ts(i),v,'synthetic_gap' if v is None else None))
    return s,steps

def context(i=400):
    history=tuple(TickEventV2('unit','synthetic_m5a_v1','synthetic_machine',f'tick-{j}',j+1,ts(j),40.) for j in range(i-23,i+1))
    return CausalContextV2(ts(i),history,0,24,0,ts(i),0,'a'*64)

def primed(errors=(2.,1.),count=100,incumbent='arima',elapsed=100):
    """Prescribed internal unit state, independent of any empirical stream."""
    s=MatchedSelectorV1();ctx=context();s.now=ctx.origin
    s.incumbents[1]=incumbent;s.last_change[1]=s.now-timedelta(minutes=5*elapsed)
    for j in range(401-count,401):
        s.buffers[1].append(MatchedLossV1(ts(j-1),ts(j),1,0,'a'*64,(f'a-{j}',f'x-{j}'),('a_mock','x_mock'),errors))
    return s,ctx

def shadow_pair(origin=100,h=1,errors=(2.,1.),different_context=False):
    tick=TickEventV2('unit','synthetic_m5a_v1','synthetic_machine','arrival',(origin+h)*100+1,ts(origin+h),40.)
    fs=[];os=[]
    for k,name in enumerate(('arima','xgboost')):
        f=SyntheticForecastV1(f'shadow-{name}-{origin}-{h}','unit','synthetic_m5a_v1','synthetic_machine','shadow_'+name,
            ts(origin),ts(origin+h),h,origin*100+2+k,origin*100+1,0,'b'*64 if different_context and k else 'a'*64,'c'*64,
            True,'expert',40.-errors[k],name,'mock_v1','synthetic_mock',ts(origin),0,ModelVersionV1(name,'mock_v1',name))
        o=TargetOutcomeV2(f'outcome-{name}',tick.sequence+1+k,f.forecast_id,tick.event_id,f.run_id,f.dataset_id,f.machine_id,
            f.policy_id,f.policy_version,h,f.origin,f.target,f.sequence,tick.sequence,f.era,'scored',f.predicted_value,40.,
            errors[k],errors[k],errors[k]**2)
        fs.append(f);os.append(o)
    return tick,tuple(fs),tuple(os)


class SelectorUnitTests(unittest.TestCase):
    def test_99_matched_pairs_cannot_switch(self):
        s,c=primed(count=99)
        r=s.choose(c,1,frozenset(('arima','xgboost')))
        self.assertEqual(r.incumbent,'arima');self.assertEqual(r.reason,'insufficient_matched_support')
    def test_insufficient_support_retains_nondefault_incumbent(self):
        s,c=primed(errors=(0.,10.),count=99,incumbent='xgboost')
        r=s.choose(c,1,frozenset(('arima','xgboost')))
        self.assertEqual(r.incumbent,'xgboost');self.assertFalse(r.switched)
    def test_100_pairs_and_sufficient_margin_can_switch(self):
        s,c=primed();r=s.choose(c,1,frozenset(('arima','xgboost')))
        self.assertTrue(r.switched);self.assertEqual(r.incumbent,'xgboost');self.assertEqual(r.matched_count,100)
    def test_absolute_hysteresis(self):
        s,c=primed(errors=(.15,.10));r=s.choose(c,1,frozenset(('arima','xgboost')))
        self.assertFalse(r.switched);self.assertEqual(r.reason,'hysteresis_hold')
    def test_relative_hysteresis(self):
        s,c=primed(errors=(20.,19.5));r=s.choose(c,1,frozenset(('arima','xgboost')))
        self.assertFalse(r.switched);self.assertEqual(r.required_improvement,1.)
    def test_dwell_23_holds_and_24_allows(self):
        for elapsed,switched in ((23,False),(24,True)):
            s,c=primed(elapsed=elapsed);r=s.choose(c,1,frozenset(('arima','xgboost')))
            self.assertEqual(r.switched,switched)
    def test_exact_ties_retain_either_incumbent(self):
        for incumbent in ('arima','xgboost'):
            s,c=primed(errors=(1.,1.),incumbent=incumbent)
            r=s.choose(c,1,frozenset(('arima','xgboost')))
            self.assertEqual(r.incumbent,incumbent);self.assertEqual(r.reason,'tie_hold_incumbent')
    def test_unavailable_incumbent_does_not_force_switch(self):
        s,c=primed();r=s.choose(c,1,frozenset(('xgboost',)))
        self.assertEqual(r.reason,'incumbent_unavailable');self.assertFalse(r.switched)
    def test_unavailable_challenger_holds(self):
        s,c=primed();r=s.choose(c,1,frozenset(('arima',)))
        self.assertEqual(r.reason,'challenger_unavailable')
    def test_genuine_exact_shadow_pairs_only(self):
        tick,fs,os=shadow_pair();s=MatchedSelectorV1()
        pairs=s.reveal_feedback(tick,0,os,{f.forecast_id:f for f in fs})
        self.assertEqual(len(pairs),1);self.assertEqual(len(s.buffers[1]),1);self.assertFalse(s.buffers[12])
    def test_one_expert_error_never_creates_comparison_support(self):
        tick,fs,os=shadow_pair();s=MatchedSelectorV1()
        s.reveal_feedback(tick,0,os[:1],{f.forecast_id:f for f in fs})
        self.assertFalse(s.buffers[1])
    def test_different_contexts_cannot_be_matched(self):
        tick,fs,os=shadow_pair(different_context=True);s=MatchedSelectorV1()
        s.reveal_feedback(tick,0,os,{f.forecast_id:f for f in fs});self.assertFalse(s.buffers[1])
    def test_future_feedback_rejected_without_state_change(self):
        tick,fs,os=shadow_pair(h=12);s=MatchedSelectorV1()
        early=replace(tick,timestamp=ts(101))
        with self.assertRaises(ValueError):s.reveal_feedback(early,0,os,{f.forecast_id:f for f in fs})
        self.assertIsNone(s.now);self.assertTrue(all(not b for b in s.buffers.values()))
    def test_feedback_cannot_be_replayed_or_duplicated(self):
        tick,fs,os=shadow_pair();records={f.forecast_id:f for f in fs};s=MatchedSelectorV1()
        with self.assertRaises(ValueError):s.reveal_feedback(tick,0,os+os[:1],records)
        s.reveal_feedback(tick,0,os,records)
        with self.assertRaises(ValueError):s.reveal_feedback(tick,0,os,records)
    def test_decision_cannot_be_revised_within_same_origin(self):
        s,c=primed();s.choose(c,1,frozenset(('arima','xgboost')))
        with self.assertRaises(ValueError):s.choose(c,1,frozenset(('arima',)))
    def test_active_support_expires_by_grid_age_even_without_feedback(self):
        s,c=primed(count=1);p=s.buffers[1][0]
        s.now=p.target+timedelta(minutes=5*286)
        tick=TickEventV2('unit','synthetic_m5a_v1','synthetic_machine','expire',99999,s.now+timedelta(minutes=5),None,'gap')
        s.reveal_feedback(tick,0,(),{});self.assertEqual(len(s.buffers[1]),1)
        s.reveal_feedback(replace(tick,event_id='expire2',sequence=100000,timestamp=tick.timestamp+timedelta(minutes=5)),0,(),{})
        self.assertFalse(s.buffers[1])
    def test_frozen_config_and_locks_fail_closed(self):
        with self.assertRaises(ValueError):SelectorConfigV1(min_matched_scores=99)
        with self.assertRaises(ValueError):SelectorConfigV1(min_matched_scores=True)
        with TemporaryDirectory() as temp:
            p=Path(temp)/'config.json';c=json.loads((ROOT/'configs/dafr_m5a_synthetic_v1.json').read_text());c['real_data_execution_allowed']=True;p.write_text(json.dumps(c))
            with self.assertRaises(ValueError):load_selector_config(p)


class SelectorIntegrationTests(unittest.TestCase):
    def test_cold_start_default_and_gate(self):
        s,steps=replay([40.]*24)
        self.assertTrue(all(r.incumbent=='arima' and not r.switched for x in steps for r in x.selections))
        self.assertTrue(all(f.availability=='fallback' for f in steps[22].decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(f.availability=='expert' for f in steps[23].decisions if f.policy_id=='adaptive'))
    def test_h12_delayed_feedback_and_exact_targets(self):
        s,steps=replay([40.]*40)
        self.assertTrue(all(p.horizon!=12 for step in steps[:35] for p in step.matched))
        self.assertTrue(any(p.horizon==12 for p in steps[35].matched))
        for f in s.ledger.decisions:self.assertEqual(f.target-f.origin,timedelta(minutes=5*f.horizon))
    def test_minimum_support_earliest_possible_tick(self):
        s,steps=replay([40.]*136)
        for h,first in ((1,123),(12,134)):
            counts=[next(r for r in step.selections if r.horizon==h).matched_count for step in steps]
            self.assertEqual(counts[first-1],99);self.assertEqual(counts[first],100)
    def test_missing_exact_h1_and_h12_targets_no_shift(self):
        values=[40.]*50;values[35]=None;s,steps=replay(values)
        for h,origin in ((1,34),(12,23)):
            f=next(f for f in steps[origin].decisions if f.policy_id=='shadow_arima' and f.horizon==h)
            outcomes=[o for o in s.ledger.outcomes if o.forecast_id==f.forecast_id]
            self.assertEqual(len(outcomes),1);self.assertEqual(outcomes[0].status,'target_unavailable')
            self.assertIsNone(outcomes[0].absolute_error)
        self.assertFalse(steps[35].matched)
    def test_identical_causal_contexts_and_updates_for_all_ticks(self):
        s,steps=replay([40.]*30+[None]*4+[40.]*30)
        for step in steps:
            updates=[e.record for e in step.events if e.kind=='adapter_update']
            self.assertEqual(len(updates),2);self.assertEqual(updates[0].context_sha256,updates[1].context_sha256)
        self.assertTrue(all(a.resources().update_calls==64 for a in s._adapters.values()))
    def test_long_gap_resets_once_and_24_genuine_recovery(self):
        s,steps=replay([40.]*150+[None]*6+[40.]*30)
        self.assertEqual(sum(x.reset is not None for x in steps),1)
        self.assertIsNotNone(steps[153].reset)
        self.assertTrue(all(r.matched_count==0 and r.incumbent=='arima' for r in steps[153].selections))
        for i in range(156,179):self.assertTrue(all(f.availability=='fallback' for f in steps[i].decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(f.availability=='expert' for f in steps[179].decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(r.matched_count<100 for r in steps[-1].selections))
    def test_old_era_h12_outcomes_preserved_but_not_active(self):
        s,steps=replay([40.]*150+[None]*4+[40.]*5)
        old=[p for step in steps[154:] for p in step.matched if p.era==0]
        self.assertTrue(old)
        self.assertFalse(s.selector.buffers[12])
        self.assertTrue(any(o.status=='scored' and o.forecast_era==0 and o.target>=ts(154) for o in s.ledger.outcomes))
    def test_leading_trailing_and_all_missing_streams(self):
        for values in ([None]*8,[None]*4+[40.]*25+[None]*6):
            s,steps=replay(values)
            self.assertTrue(all(f.predicted_value is None for f in steps[0].decisions))
            self.assertTrue(all(f.availability=='abstained' for f in steps[-1].decisions if f.policy_id in ('adaptive','persistence')))
    def test_three_tick_fallback_expires_on_fourth(self):
        s,steps=replay([40.]*30+[None]*4)
        for step in steps[30:33]:self.assertTrue(all(f.availability=='fallback' for f in step.decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(f.availability=='abstained' for f in steps[33].decisions if f.policy_id=='adaptive'))
    def test_numerical_failure_logs_fallback_without_fake_shadow_loss(self):
        specs=list(mock_specs());specs[0]=replace(specs[0],fault='forecast_nonfinite',fault_ticks=(130,),fault_horizon=1)
        s,steps=replay([40.]*145,tuple(specs))
        f=next(f for f in steps[130].decisions if f.policy_id=='shadow_arima' and f.horizon==1)
        policy=next(f for f in steps[130].decisions if f.policy_id=='adaptive' and f.horizon==1)
        self.assertEqual(f.availability,'numerical_failure');self.assertIsNone(f.predicted_value)
        self.assertEqual(policy.availability,'fallback');self.assertEqual(policy.source_expert,'persistence')
        self.assertFalse(any(o.forecast_id==f.forecast_id for o in s.ledger.outcomes))
        self.assertFalse(any(p.origin==ts(130) and p.horizon==1 for step in steps for p in step.matched))
    def test_update_failure_remains_invalid_no_hidden_retraining(self):
        specs=list(mock_specs());specs[0]=replace(specs[0],fault='update_error',fault_ticks=(30,))
        s,steps=replay([40.]*150,tuple(specs))
        self.assertTrue(s._adapters['arima'].resources().state_invalid)
        self.assertTrue(all(f.availability=='fallback' for step in steps[30:] for f in step.decisions if f.policy_id=='adaptive'))
        self.assertTrue(all(r.incumbent=='arima' for step in steps for r in step.selections))
    def test_selective_availability_cannot_create_false_advantage(self):
        specs=list(mock_specs());specs[1]=replace(specs[1],fault='forecast_unavailable',fault_ticks=tuple(range(24,200,2)),fault_horizon=None)
        s,steps=replay([40.]*200,tuple(specs))
        self.assertTrue(all(r.matched_count<100 for r in steps[-1].selections))
        self.assertTrue(all(r.incumbent=='arima' for step in steps for r in step.selections))
    def test_future_suffix_perturbation_invariance(self):
        prefix=[40.+(i%7) for i in range(145)]
        a,aa=replay(prefix+[41.]*20);b,bb=replay(prefix+[None]*20)
        self.assertEqual(aa[:145],bb[:145]);self.assertNotEqual(aa[145:],bb[145:])
    def test_independent_horizon_selection(self):
        s=SelectorStreamingV1('horizon_test');last=None
        for row in synthetic_events('horizon_divergence'):last=s.advance(*row)
        self.assertEqual(s.selector.incumbents,{1:'arima',12:'xgboost'})
        self.assertEqual(s.selector.switches[1],0);self.assertGreater(s.selector.switches[12],0)
    def test_immutable_forecasts_and_exact_shadow_link(self):
        s,steps=replay([40.]*30);f=next(f for f in steps[23].decisions if f.policy_id=='adaptive')
        saved=f
        s.advance(ts(30),41.)
        self.assertEqual(saved,f)
        with self.assertRaises(FrozenInstanceError):f.predicted_value=0
        source=s.ledger._records[f.source_shadow_id]
        self.assertEqual(source.predicted_value,f.predicted_value);self.assertEqual(source.target,f.target)
    def test_event_order_and_separate_accounting(self):
        s,steps=replay([40.]*145)
        for step in steps:
            seq=[e.sequence for e in step.events];self.assertEqual(seq,sorted(set(seq)))
            for o in step.outcomes:self.assertLess(o.sequence,min(f.sequence for f in step.decisions))
            for p in step.matched:self.assertLessEqual(p.target,step.tick.timestamp)
        self.assertTrue(any(o.policy_id=='adaptive' for o in s.ledger.outcomes))
        self.assertTrue(all(s.ledger._records[fid].policy_id.startswith('shadow_') for b in s.selector.buffers.values() for p in b for fid in p.forecast_ids))
    def test_buffer_capacity_288_and_grid_recency(self):
        s,steps=replay([40.]*340)
        self.assertEqual(len(s.selector.buffers[1]),288);self.assertEqual(len(s.selector.buffers[12]),288)
        for b in s.selector.buffers.values():self.assertGreaterEqual(b[0].target,ts(339-287))
    def test_invalid_ticks_and_arbitrary_models_rejected(self):
        s=SelectorStreamingV1('invalid')
        for v in (float('nan'),101.,-1.):
            with self.assertRaises(ValueError):s.advance(ts(0),v)
        self.assertEqual(s._ticks,0);s.advance(ts(0),40.)
        with self.assertRaises(ValueError):s.advance(ts(2),40.)
        with self.assertRaises(ValueError):SelectorStreamingV1('bad',(object(),object()))
    def test_synthetic_engine_does_not_read_data_or_models(self):
        original=Path.open
        def guard(path,*args,**kwargs):
            mode=args[0] if args else kwargs.get('mode','r')
            if 'r' in mode and ('data' in path.parts or 'models' in path.parts):raise AssertionError('M5A read a real data/model path')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):replay([40.]*145)
    def test_no_overwrite_and_failed_run_id_remains_reserved(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);out=run_synthetic('unique','stable',root)
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
            with self.assertRaises(FileExistsError):run_synthetic('unique','stable',root)
            self.assertEqual(hashes,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
            with patch('dafr.selector_streaming_v1.synthetic_events',side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):run_synthetic('failed','stable',root)
            self.assertEqual(json.loads((out.parent/'failed/completion.json').read_text())['status'],'failed')
            with self.assertRaises(FileExistsError):run_synthetic('failed','stable',root)
    def test_saved_audit_recomputes_support_and_rejects_changed_prediction(self):
        with TemporaryDirectory() as temp:
            out=run_synthetic('audit','stable',Path(temp))
            result=verify_synthetic_run(out,'stable')
            self.assertTrue(result['passed']);self.assertEqual(result['decisions'],3200)
            p=out/'policy_predictions.jsonl';lines=p.read_text().splitlines()
            row=json.loads(lines[0]);row['predicted_value']+=1;lines[0]=json.dumps(row)
            p.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(AssertionError):verify_synthetic_run(out,'stable')
    def test_374_historical_artifact_hashes_preserved(self):
        inventory=json.loads((ROOT/'reports/dafr/m5a_preservation_v1.json').read_text())
        self.assertEqual(inventory['file_count'],374)
        for p,sha in inventory['protected_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),sha,p)


if __name__=='__main__':unittest.main()
