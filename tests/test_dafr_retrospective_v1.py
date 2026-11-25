"""Retrospective chronology/integrity tests. No model or new dataset access."""
from dataclasses import replace,asdict,FrozenInstanceError
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,json,sys,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from dafr.retrospective_sources_v1 import (load_m4a_input,load_config,FrameV1,ReplayInputV1,
    SavedForecastV1,SourceRefV1,decode_forecast,canonical_sha,LABEL)
from dafr.retrospective_replay_v1 import RetrospectiveReplayV1
from dafr.run_m5b2_v1 import comparisons,macro_metrics,verify_history,run
from dafr.audit_m5b2_v1 import verify_machine
from dafr.selector_v1 import MatchedSelectorV1
from dafr.streaming_v2 import StreamingSimulatorV2,StubExpertV2,ForecastLedgerV2,_write_json


def synthetic_input(values):
    """Clearly synthetic immutable source ledgers for gap/reset stress tests."""
    engine=StreamingSimulatorV2('synthetic_source','synthetic_cpu','synthetic_machine',
        (StubExpertV2(),StubExpertV2('arima','a_v1'),StubExpertV2('xgboost','x_v1','offset',.1)))
    start=datetime(2026,1,1,tzinfo=timezone.utc);prefix=[]
    for j in range(23):prefix.append(engine.advance(start+timedelta(minutes=5*j),40+.1*(j-23)).tick)
    engine.ledger=ForecastLedgerV2()
    frames=[]
    for i,v in enumerate(values):
        step=engine.advance(start+timedelta(minutes=5*(23+i)),v,'synthetic_gap' if v is None else None)
        saved=[]
        for f in step.decisions:
            ref=SourceRefV1(f'synthetic/{f.policy_id}/predictions.jsonl',i*2+f.horizon,f.run_id,f.forecast_id,'a'*64)
            saved.append(SavedForecastV1(f,ref,'b'*64 if f.policy_id!='persistence' else None,'c'*64,start))
        frames.append(FrameV1(step.tick,step.state,tuple(saved),step.outcomes,step.reset))
    return ReplayInputV1('synthetic_machine',tuple(prefix),0,tuple(frames),())


def evaluate(inputs):
    r=RetrospectiveReplayV1('unit_replay',inputs,'e'*64);steps=tuple(r.advance(f) for f in inputs.frames)
    return r,steps


class RetrospectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs={m:load_m4a_input(m) for m in ('m_505','m_1426','m_3028')}
        cls.results={m:evaluate(b) for m,b in cls.inputs.items()}
        cls.bundle=cls.inputs['m_3028'];cls.replay,cls.steps=cls.results['m_3028']
    def engine(self):return RetrospectiveReplayV1('unit_replay',self.bundle,'e'*64)
    def test_only_allowed_machine_can_be_loaded(self):
        with patch.object(Path,'read_bytes') as read:
            with self.assertRaises(ValueError):load_m4a_input('m_3276')
            read.assert_not_called()
    def test_frozen_config_and_locks(self):
        c,_,_=load_config();self.assertFalse(c['confirmation_execution_allowed']);self.assertEqual(c['origin_indices'],[1152,1612])
        self.assertEqual(c['selector'],json.loads((ROOT/'configs/dafr_m5a_synthetic_v1.json').read_text())['selector'])
        with TemporaryDirectory() as t:
            p=Path(t)/'configs';p.mkdir();c['training_allowed']=True
            (p/'dafr_m5b2_retrospective_v1.json').write_text(json.dumps(c))
            with self.assertRaises(ValueError):load_config(Path(t))
    def test_no_preblock_losses_or_forecasts_imported(self):
        r=self.engine();self.assertFalse(r._issued);self.assertFalse(r.pending_ids)
        self.assertTrue(all(not b for b in r.selector.buffers.values()));self.assertEqual(r.selector.incumbents,{1:'arima',12:'arima'})
        self.assertIs(type(r.selector),MatchedSelectorV1)
    def test_all_original_contexts_reproduced(self):
        for m,(r,steps) in self.results.items():
            self.assertEqual(len(steps),460)
            for frame,step in zip(self.inputs[m].frames,steps):self.assertEqual(step.context.context_sha256,frame.state.context_sha256)
    def test_exact_targets_and_source_links(self):
        originals={s.forecast.forecast_id:s for f in self.bundle.frames for s in f.forecasts}
        for d in self.replay.decisions:
            self.assertEqual(d.target-d.origin,timedelta(minutes=5*d.horizon))
            self.assertEqual(d.predicted_value,originals[d.source_reference.forecast_id].forecast.predicted_value)
            self.assertEqual(d.source_reference,originals[d.source_reference.forecast_id].reference)
    def test_h12_loss_delayed_until_exact_arrival(self):
        self.assertTrue(all(p.horizon==1 for step in self.steps[:12] for p in step.pairs))
        self.assertTrue(any(p.horizon==12 for p in self.steps[12].pairs))
    def test_99_100_support_boundary_each_horizon(self):
        for h,index in ((1,100),(12,111)):
            before=next(s for s in self.steps[index-1].selections if s.horizon==h)
            now=next(s for s in self.steps[index].selections if s.horizon==h)
            self.assertEqual(before.matched_count,99);self.assertFalse(before.switched);self.assertEqual(now.matched_count,100)
    def test_horizon_support_is_independent(self):
        ss={s.horizon:s for s in self.steps[100].selections}
        self.assertEqual(ss[1].matched_count,100);self.assertEqual(ss[12].matched_count,89)
    def test_future_feedback_rejected_before_mutation(self):
        r=self.engine();future=next(o for o in self.bundle.frames[12].outcomes if o.horizon==12)
        with self.assertRaises(ValueError):r.advance(replace(self.bundle.frames[0],outcomes=(future,)))
        self.assertEqual(r._ticks,0);self.assertFalse(r.decisions);self.assertIsNone(r.selector.now)
    def test_missing_source_outcome_not_silently_dropped(self):
        r=self.engine();r.advance(self.bundle.frames[0]);before=r._sequence
        frame=self.bundle.frames[1]
        with self.assertRaises(ValueError):r.advance(replace(frame,outcomes=frame.outcomes[1:]))
        self.assertEqual(r._sequence,before)
    def test_skipped_duplicate_tick_rejected(self):
        r=self.engine()
        with self.assertRaises(ValueError):r.advance(self.bundle.frames[1])
        r.advance(self.bundle.frames[0])
        with self.assertRaises(ValueError):r.advance(self.bundle.frames[0])
    def test_missing_expert_is_a_blocker(self):
        frame=self.bundle.frames[0];r=self.engine()
        with self.assertRaises(ValueError):r.advance(replace(frame,forecasts=frame.forecasts[:-1]))
        self.assertEqual(r._ticks,0)
    def test_version_change_rejected(self):
        frame=self.bundle.frames[0];saved=frame.forecasts[1]
        bad=replace(saved,forecast=replace(saved.forecast,policy_version='changed'))
        with self.assertRaises(ValueError):self.engine().advance(replace(frame,forecasts=(frame.forecasts[0],bad)+frame.forecasts[2:]))
    def test_context_change_rejected(self):
        frame=self.bundle.frames[0];saved=frame.forecasts[1]
        bad=replace(saved,forecast=replace(saved.forecast,context_sha256='f'*64))
        with self.assertRaises(ValueError):self.engine().advance(replace(frame,forecasts=(frame.forecasts[0],bad)+frame.forecasts[2:]))
    def test_source_reference_identity_cannot_change(self):
        frame=self.bundle.frames[0];saved=frame.forecasts[1]
        bad=replace(saved,reference=replace(saved.reference,forecast_id='unknown'))
        with self.assertRaises(ValueError):self.engine().advance(replace(frame,forecasts=(frame.forecasts[0],bad)+frame.forecasts[2:]))
    def test_unrevealed_future_value_mask_and_forecast_invariance(self):
        changed=list(self.bundle.frames)
        for i in range(50,len(changed)):
            frame=changed[i];tick=replace(frame.tick,value=None,missing_reason='changed_future')
            saved=frame.forecasts[1]
            bad=replace(saved,forecast=replace(saved.forecast,predicted_value=99.))
            changed[i]=replace(frame,tick=tick,forecasts=(frame.forecasts[0],bad)+frame.forecasts[2:])
        altered=replace(self.bundle,frames=tuple(changed));a=self.engine();b=RetrospectiveReplayV1('unit_replay',altered,'e'*64)
        aa=[a.advance(f) for f in self.bundle.frames[:50]];bb=[b.advance(f) for f in altered.frames[:50]]
        self.assertEqual(aa,bb)
    def test_fallback_losses_do_not_rank_experts(self):
        r,steps=self.results['m_505']
        self.assertTrue(any(o.status=='scored' for step in steps[1:4] for o in step.outcomes))
        self.assertFalse(any(p.horizon==1 for step in steps[:4] for p in step.pairs))
        for step in steps:
            for d in step.decisions:
                if d.availability=='fallback':self.assertIn('/persistence/',d.source_reference.path)
    def test_missing_exact_target_not_shifted(self):
        # This missing position is already in the authorized saved M4A block.
        frame=next(f for f in self.bundle.frames if not f.tick.genuine)
        for h in (1,12):
            ds=[d for d in self.replay.decisions if d.target==frame.tick.timestamp and d.horizon==h]
            self.assertEqual(len(ds),1)
            os=[o for o in self.replay.outcomes if o.decision_id==ds[0].decision_id]
            self.assertEqual(len(os),1);self.assertEqual(os[0].status,'target_unavailable');self.assertIsNone(os[0].absolute_error)
    def test_boundary_pending_never_scored(self):
        self.assertEqual(len(self.replay.pending_ids),13)
        resolved={o.decision_id for o in self.replay.outcomes}
        self.assertTrue(set(self.replay.pending_ids).isdisjoint(resolved))
        last=self.bundle.frames[-1].tick.timestamp
        self.assertTrue(all(o.target<=last for o in self.replay.outcomes))
    def test_forecasts_and_outcomes_immutable(self):
        with self.assertRaises(FrozenInstanceError):self.replay.decisions[0].predicted_value=0
        with self.assertRaises(FrozenInstanceError):self.replay.outcomes[0].actual=0
    def test_exact_event_order(self):
        last=0
        for step in self.steps:
            seq=[e.sequence for e in step.events];self.assertEqual(seq,sorted(set(seq)));self.assertGreater(seq[0],last);last=seq[-1]
            state=next(e.sequence for e in step.events if e.kind=='causal_state')
            self.assertTrue(all(o.sequence<state for o in step.outcomes));self.assertTrue(all(d.sequence>state for d in step.decisions))
    def test_equal_target_sets_and_complete_policy_distinction(self):
        rows=comparisons(self.bundle,self.replay)
        for h,count,complete in ((1,434,458),(12,423,447)):
            self.assertEqual({r['count'] for r in rows if r['horizon']==h and r['scope']=='expert_matched'},{count})
            self.assertEqual({r['count'] for r in rows if r['horizon']==h and r['scope']=='complete_policy_matched'},{complete})
    def test_equal_machine_macro_not_pooled(self):
        rows=[{'horizon':1,'scope':'expert_matched','policy':'adaptive','count':n,'mae':v,'rmse':v} for n,v in ((1,1.),(10,2.),(100,9.))]
        row=next(r for r in macro_metrics(rows) if (r['horizon'],r['scope'],r['policy'])==(1,'expert_matched','adaptive'))
        self.assertEqual(row['mae'],4.)
        rows[0]['count']=0
        row=next(r for r in macro_metrics(rows) if (r['horizon'],r['scope'],r['policy'])==(1,'expert_matched','adaptive'))
        self.assertIsNone(row['mae'])
    def test_source_fingerprint_tamper_rejected_without_file_change(self):
        original=Path.read_bytes
        def changed(path):
            data=original(path)
            return data+b' ' if path.name=='events.jsonl' and path.parent.name=='m_3028' else data
        with patch.object(Path,'read_bytes',changed):
            with self.assertRaises(ValueError):load_m4a_input('m_3028')
    def test_source_envelope_cannot_omit_checkpoint_provenance(self):
        saved=self.bundle.frames[0].forecasts[1];line=(ROOT/saved.reference.path).read_text().splitlines()[saved.reference.line-1]
        raw=json.loads(line);del raw['requested_checkpoint_sha256']
        with self.assertRaises(ValueError):decode_forecast(raw,saved.reference.path,saved.reference.line)
    def test_new_reader_has_no_original_dataset_access(self):
        original=Path.open;allowed=ROOT/'data/processed/dafr/m4a_development_v1/m4a-development-20261031-001'
        def guard(path,*args,**kwargs):
            mode=args[0] if args else kwargs.get('mode','r')
            if 'r' in mode and path.is_relative_to(ROOT/'data') and not path.is_relative_to(allowed):raise AssertionError('New dataset access')
            if 'r' in mode and path.suffix=='.csv':raise AssertionError('Dataset CSV opened')
            if 'r' in mode and path.is_relative_to(ROOT/'models') and path.name!='metadata.json':raise AssertionError('Model weights loaded')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard):load_m4a_input('m_3028')
    def test_no_overwrite_before_any_source_read(self):
        with TemporaryDirectory() as temp:
            p=Path(temp)/'data/processed/dafr/m5b2_retrospective_v1/reserved';p.mkdir(parents=True)
            (p/'sentinel').write_text('preserve')
            with patch('dafr.run_m5b2_v1.load_m4a_input') as source:
                with self.assertRaises(FileExistsError):run('reserved',Path(temp))
                source.assert_not_called()
            self.assertEqual((p/'sentinel').read_text(),'preserve')
    def test_independent_saved_audit_and_tamper_rejection(self):
        with TemporaryDirectory() as temp:
            d=Path(temp)
            for name,items in (
                ('decisions',(asdict(x) for x in self.replay.decisions)),('outcomes',(asdict(x) for x in self.replay.outcomes)),
                ('events',({'label':LABEL,'sequence':e.sequence,'kind':e.kind,'record':asdict(e.record)} for step in self.steps for e in step.events))):
                with (d/(name+'.jsonl')).open('x') as out:
                    for item in items:_write_json(out,item)
            result=verify_machine(d,self.bundle);self.assertTrue(result['passed']);self.assertEqual(result['decisions'],920)
            for a,b in zip(comparisons(self.bundle,self.replay),result['recomputed_comparisons']):
                self.assertEqual(a['count'],b['count']);self.assertAlmostEqual(a['mae'],b['mae']);self.assertAlmostEqual(a['rmse'],b['rmse'])
            p=d/'decisions.jsonl';lines=p.read_text().splitlines();row=json.loads(lines[0]);row['predicted_value']+=1
            lines[0]=json.dumps(row);p.write_text('\n'.join(lines)+'\n')
            with self.assertRaises(ValueError):verify_machine(d,self.bundle)
    def test_protected_historical_hashes(self):self.assertEqual(verify_history(),505)


class SyntheticReplayRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vals=[40+.1*i if not 140<=i<146 else None for i in range(185)]
        cls.inputs=synthetic_input(vals);cls.replay,cls.steps=evaluate(cls.inputs)
    def test_three_tick_fallback_and_fourth_tick_abstention(self):
        for step in self.steps[140:143]:self.assertTrue(all(d.availability=='fallback' for d in step.decisions))
        self.assertTrue(all(d.availability=='abstained' for d in self.steps[143].decisions))
    def test_reset_once_and_default_restart_distinct_from_switch(self):
        self.assertTrue(all(s.incumbent=='xgboost' for s in self.steps[139].selections))
        self.assertEqual(sum(s.state.reset for s in self.steps),1)
        self.assertTrue(all(s.incumbent=='arima' and not s.switched and s.matched_count==0 for s in self.steps[143].selections))
    def test_24_genuine_recovery(self):
        self.assertTrue(all(d.availability=='fallback' for d in self.steps[168].decisions))
        self.assertTrue(all(d.availability=='expert' for d in self.steps[169].decisions))
    def test_old_era_losses_retained_without_new_support(self):
        self.assertTrue(any(p.era==0 for step in self.steps[146:152] for p in step.pairs))
        self.assertTrue(all(s.matched_count==0 for s in self.steps[151].selections))
    def test_recent_support_cap_and_grid_age(self):
        r,steps=evaluate(synthetic_input([40+.1*i for i in range(340)]))
        self.assertEqual(len(r.selector.buffers[1]),288)
        self.assertTrue(all(p.target>=steps[-1].context.origin-timedelta(minutes=5*287) for b in r.selector.buffers.values() for p in b))
        self.assertGreater(sum(step.state.expired_by_age[0] for step in steps),0)


if __name__=='__main__':unittest.main()
