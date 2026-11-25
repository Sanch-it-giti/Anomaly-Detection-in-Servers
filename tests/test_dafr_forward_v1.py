"""M4A scope and chronology tests; no actual new forward rows are read."""
import copy,csv,hashlib,io,json,sys
from dataclasses import FrozenInstanceError
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from dafr.development_qualification_v1 import EPOCH,FIELDS
from dafr.scoped_development_reader_v1 import read_authorized_rows,extract_development_segment
from dafr.forward_streaming_v1 import ForwardSimulator
from dafr.real_adapters_v1 import RealAdapter,digest_bytes
from dafr.run_m4a_v1 import load_config,historical_prefix,prohibit_fitting,missingness,macro_rows
def ts(i):return EPOCH+timedelta(seconds=300*(i+1))
def fixture(start=1152,end=1612,missing=()):
    out=io.StringIO(newline="");w=csv.writer(out);w.writerow(FIELDS)
    for i in range(start,end):
        w.writerow([ts(i).isoformat(),(i+1)*300,"" if i in missing else "40","failed" if i in missing else "valid","gap" if i in missing else ""])
    return out.getvalue().encode()
class Guard:
    def __init__(self,payload,limit):self.payload=payload;self.limit=limit;self.pos=0
    def read(self,n):
        if n!=1:raise AssertionError("Read-ahead requested")
        if self.pos>=self.limit:raise AssertionError("Forbidden tail read")
        value=self.payload[self.pos:self.pos+1];self.pos+=len(value);return value

class ScopedReaderTests(unittest.TestCase):
    def test_exact_460_rows_no_read_ahead(self):
        authorized=fixture(missing=(1160,1200))
        guard=Guard(authorized+b"FORBIDDEN_CALIBRATION_CPU",len(authorized))
        values,reasons,payload=read_authorized_rows(guard)
        self.assertEqual(len(values),460);self.assertEqual(guard.pos,len(authorized));self.assertEqual(payload,authorized)
        self.assertEqual(sum(v is None for v in values),2)
    def test_future_tail_perturbation_has_no_effect(self):
        authorized=fixture()
        a=read_authorized_rows(Guard(authorized+b"secret_a",len(authorized)))
        b=read_authorized_rows(Guard(authorized+b"other_secret",len(authorized)))
        self.assertEqual(a,b)
    def test_wrong_future_label_rejected_before_cpu_field(self):
        header=fixture(1152,1153).splitlines(keepends=True)[0]
        label=ts(1612).isoformat().encode()+b","+str(1613*300).encode()+b","
        guard=Guard(header+label+b"FORBIDDEN_CPU",len(header+label))
        with self.assertRaises(ValueError):read_authorized_rows(guard)
        self.assertEqual(guard.pos,len(header+label))
    def test_forbidden_bounds_rejected_before_read(self):
        handle=io.BytesIO()
        with patch.object(handle,"read") as read:
            with self.assertRaises(ValueError):read_authorized_rows(handle,1612,1842)
            read.assert_not_called()
    def test_bad_quality_and_truncated_rows_rejected(self):
        for payload in (fixture(1152,1153),fixture().replace(b",40,valid,",b",nan,valid,",1),
                        fixture().replace(b",40,valid,",b",40,failed,",1)):
            with self.assertRaises(ValueError):read_authorized_rows(io.BytesIO(payload))
    def test_public_extractor_scope_receipt_and_no_overwrite(self):
        config,_=load_config()
        with TemporaryDirectory() as temp:
            root=Path(temp).resolve();c=copy.deepcopy(config);machine="m_505"
            path=root/c["sources"][machine]["path"];path.parent.mkdir(parents=True)
            authorized=fixture();path.write_bytes(authorized+b"TAIL_CPU_DO_NOT_READ")
            c["sources"][machine]["expected_container_bytes"]=path.stat().st_size
            values,_,r=extract_development_segment(root,machine,c,root/"extract")
            self.assertEqual(r["bytes_read"],len(authorized))
            self.assertEqual(r["segment_sha256"],hashlib.sha256(authorized).hexdigest())
            self.assertFalse(r["read_ahead"]);self.assertFalse(r["decryption_performed"])
            with self.assertRaises(FileExistsError):extract_development_segment(root,machine,c,root/"extract")
    def test_confirmation_and_reserves_rejected_before_open(self):
        config,_=load_config()
        with patch.object(Path,"open") as opened:
            for machine in ("m_295","m_66","m_3276","../m_505"):
                with self.assertRaises(ValueError):extract_development_segment(ROOT,machine,config,ROOT/"unused")
            opened.assert_not_called()

class ForwardChronologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config,cls.sha=load_config()
        cls.prefix=historical_prefix("m_3028",cls.config)
        with prohibit_fitting() as audit:
            cls.base=ForwardSimulator("synthetic_forward","m_3028",cls.config,cls.prefix,cls.sha,ROOT)
        assert audit["fit_call_attempts"]==0
    def engine(self):return copy.deepcopy(self.base)
    def test_exact_reconstruction_matches_old_checkpoint_and_no_hindsight_ledger(self):
        s=self.engine()
        for family,sha in s.reconstructed_hashes.items():
            self.assertEqual(sha,self.config["models"]["m_3028"][family]["reconstructed_end_1151_state_sha256"])
        self.assertEqual(s.ledger.forecasts,());self.assertEqual(s.ledger.outcomes,())
        self.assertTrue(all(not buffer for buffer in s._support.values()))
    def test_exact_begin_end_boundaries_reject_before_mutation(self):
        s=self.engine();before=(s._sequence,s._ticks)
        with self.assertRaises(ValueError):s.advance(ts(1151),40.)
        self.assertEqual(before,(s._sequence,s._ticks))
        s.advance(ts(1152),40.)
        before=(s._sequence,s._ticks)
        with self.assertRaises(ValueError):s.advance(ts(1154),40.)
        self.assertEqual(before,(s._sequence,s._ticks))
        s._ticks=460
        with self.assertRaises(ValueError):s.advance(ts(1612),40.)
    def test_identical_contexts_horizons_and_selected_policy_provenance(self):
        s=self.engine();calls=[];original=RealAdapter.update
        def observe(adapter,tick,context):
            calls.append(context);return original(adapter,tick,context)
        with patch.object(RealAdapter,"update",observe):step=s.advance(ts(1152),40.)
        self.assertIs(calls[0],calls[1])
        for f in step.decisions:
            self.assertEqual(f.target,ts(1152+f.horizon))
            envelope=s.envelopes[f.forecast_id]
            if f.policy_id!="persistence":
                self.assertEqual(envelope.policy_selection_cutoff,ts(1151))
                self.assertLess(envelope.policy_selection_cutoff,f.origin)
    def test_missing_events_age_three_four_and_24_genuine_recovery(self):
        s=self.engine();era=s._era
        for i in range(1152,1156):step=s.advance(ts(i),None,"synthetic_gap")
        self.assertTrue(all(f.availability=="abstained" for f in step.decisions))
        self.assertEqual(s._era,era+1)
        for i in range(1156,1180):
            step=s.advance(ts(i),40.)
            if i<1179:self.assertFalse(step.state.learned_eligible)
        self.assertTrue(step.state.learned_eligible);self.assertEqual(s._era,era+1)
    def test_no_h12_feedback_before_exact_genuine_target(self):
        s=self.engine();steps=[]
        for i in range(1152,1166):steps.append(s.advance(ts(i),None if i==1164 else 40.,"gap" if i==1164 else None))
        self.assertTrue(all(o.horizon==1 for step in steps[:12] for o in step.outcomes))
        f=next(f for f in steps[0].decisions if f.policy_id=="arima" and f.horizon==12)
        o=next(o for o in steps[12].outcomes if o.forecast_id==f.forecast_id)
        self.assertEqual(o.status,"target_unavailable");self.assertIsNone(o.absolute_error)
        self.assertFalse(any(o.forecast_id==f.forecast_id for o in steps[13].outcomes))
    def test_future_suffix_perturbation_invariance(self):
        a=self.engine();b=self.engine();aa=[];bb=[]
        for i in range(1152,1174):
            aa.append(a.advance(ts(i),40.+i%4))
            v=(None if i%2 else 99.) if i>=1167 else 40.+i%4
            bb.append(b.advance(ts(i),v,"changed" if v is None else None))
        self.assertEqual(aa[:15],bb[:15]);self.assertNotEqual(aa[15:],bb[15:])
    def test_parameters_and_issued_records_immutable(self):
        s=self.engine();before={f:a.parameter_sha256 for f,a in s._adapters.items()}
        step=s.advance(ts(1152),40.);f=step.decisions[0];saved=copy.deepcopy(f)
        for i in range(1153,1160):s.advance(ts(i),41.)
        self.assertEqual(f,saved)
        self.assertEqual(before,{f:a.parameter_sha256 for f,a in s._adapters.items()})
        with self.assertRaises(FrozenInstanceError):f.predicted_value=0
    def test_refitting_is_explicitly_prohibited(self):
        with self.assertRaises(AssertionError):
            with prohibit_fitting():SARIMAX.fit(None)
    def test_no_stale_model_state_after_genuine_or_missing_update(self):
        s=self.engine()
        for i in range(1152,1158):
            step=s.advance(ts(i),None if i==1154 else 40.,"gap" if i==1154 else None)
            for u in step.updates:self.assertEqual(u.result.model_state_cutoff,ts(i))
    def test_macro_does_not_hide_an_empty_machine_subset(self):
        rows=[{"policy":p,"horizon":h,"expert_matched":{"count":1 if m<2 else 0,"mae":1 if m<2 else None,"rmse":1 if m<2 else None}}
              for p in ("persistence","arima","xgboost") for h in (1,12) for m in range(3)]
        self.assertTrue(all(r["mae"] is None for r in macro_rows(rows)))
    def test_missingness_retains_boundary_runs(self):
        m=missingness((None,None,40.,None,40.,None,None,None))
        self.assertEqual(m["longest_missing_run_bins"],3);self.assertEqual(m["missing_runs"],3)
    def test_297_protected_files_and_selected_models_unchanged(self):
        receipt=json.loads((ROOT/"reports/dafr/m4a_preservation_v1.json").read_text())
        self.assertEqual(receipt["file_count"],297)
        for p,sha in receipt["protected_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),sha,p)

if __name__=="__main__":unittest.main()

