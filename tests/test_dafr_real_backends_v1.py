"""Synthetic backend gate; no Alibaba fitting in tests."""
from dataclasses import replace
from datetime import timedelta
import copy,hashlib,json,shutil,sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
import xgboost as xgb
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from dafr.development_qualification_v1 import EPOCH
from dafr.real_adapters_v1 import RealAdapter,load_registered_adapter,sarimax_model
from dafr.real_streaming_v1 import RealStreamingSimulator
from dafr.run_m3b2_v1 import save_artifact,training_arrays,load_execution,load_source,enforce_memory,choose_global
def ts(i):return EPOCH+timedelta(minutes=5*(i+1))
def vals(n):return tuple(40.+i%5 for i in range(n))

class RealBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();cls.root=Path(cls.tmp.name).resolve()
        cls.plan=json.loads((ROOT/"configs/dafr_m3b_development_manifest_v1.json").read_text())
        cls.toy=copy.deepcopy(cls.plan)
        for c in cls.toy["xgboost"]["candidate_configurations"]:c.update(n_estimators=3,max_depth=1)
        cls.fit=vals(60)
        cls.arima,_=save_artifact(cls.root/"arima","synthetic","synthetic_source",cls.fit,"arima",0,cls.toy,synthetic=True,known_params=[20,.5,1])
        cls.xgb,_=save_artifact(cls.root/"xgboost","synthetic","synthetic_source",cls.fit,"xgboost",0,cls.toy,synthetic=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def engine(self,ref=None,run="test"):return RealStreamingSimulator(run,"synthetic",ref or self.arima,self.fit)

    def test_sequential_missing_filter_matches_batch(self):
        s=self.engine();full=list(self.fit)
        for i in range(60,80):
            value=None if i in (62,63,70) else 40.+i%5
            full.append(value)
            s.advance(ts(i),value,"gap" if value is None else None)
            a=s._adapters["arima"]
            batch=sarimax_model([np.nan if v is None else v for v in full],(1,0,0)).filter([20,.5,1])
            np.testing.assert_allclose(a.result.filtered_state[:,-1],batch.filtered_state[:,-1],rtol=1e-9,atol=1e-9)
            np.testing.assert_allclose(a.result.filtered_state_cov[:,:,-1],batch.filtered_state_cov[:,:,-1],rtol=1e-9,atol=1e-9)
            if value is None:
                f=a.result.filter_results
                np.testing.assert_allclose(f.filtered_state[:,0],f.predicted_state[:,0],atol=1e-10)
                np.testing.assert_allclose(f.filtered_state_cov[:,:,0],f.predicted_state_cov[:,:,0],atol=1e-10)
        self.assertEqual(a.resources()["state_steps"],20)
        self.assertEqual(a.resources()["genuine_measurement_updates"],17)

    def test_arima_nonmutating_h1_h12(self):
        s=self.engine();step=s.advance(ts(60),41.)
        a=s._adapters["arima"];before=a.state_sha256;params=a.parameter_sha256;context=s._context(step.tick)
        for h in (1,12):
            result=a.forecast(context,h)
            self.assertEqual(result.status,"ok");self.assertEqual(result.target,ts(60+h))
            self.assertEqual(a.state_sha256,before);self.assertEqual(a.parameter_sha256,params)

    def test_xgboost_feature_and_output_shapes(self):
        s=self.engine(self.xgb);step=s.advance(ts(60),41.)
        a=s._adapters["xgboost"];before=a.parameter_sha256;context=s._context(step.tick)
        row=np.array([[context.history[-1-o].value for o in (0,1,2,5,11,23)]],dtype=np.float32)
        for h in (1,12):
            expected=a.boosters[h].inplace_predict(row,strict_shape=True)
            self.assertEqual(expected.shape,(1,1));self.assertEqual(a.forecast(context,h).value,float(expected[0,0]))
            self.assertEqual(before,a.parameter_sha256)

    def test_bootstrap_without_duplicate_assimilation(self):
        s=self.engine();a=s._adapters["arima"]
        self.assertEqual(a.resources()["update_calls"],0);self.assertEqual(a.result.nobs,60)
        self.assertEqual(len(s._history),23)
        with self.assertRaises(ValueError):s.advance(ts(59),40.)
        self.assertEqual(a.resources()["update_calls"],0)
        step=s.advance(ts(60),41.)
        self.assertTrue(step.state.learned_eligible);self.assertEqual(a.resources()["update_calls"],1)

    def test_fingerprints_reject_model_scaler_metadata_tampering(self):
        for filename in ("scaler.json","params.json","metadata.json"):
            with TemporaryDirectory() as tmp:
                directory=Path(tmp).resolve()/"artifact";shutil.copytree(self.arima.directory,directory)
                (directory/filename).write_text("{}")
                with self.assertRaises(ValueError):load_registered_adapter(replace(self.arima,directory=directory),self.fit)

    def test_xgboost_fingerprint(self):
        with TemporaryDirectory() as tmp:
            directory=Path(tmp).resolve()/"artifact";shutil.copytree(self.xgb.directory,directory)
            with (directory/"model_h12.json").open("a") as out:out.write(" ")
            with self.assertRaises(ValueError):load_registered_adapter(replace(self.xgb,directory=directory),self.fit)

    def test_arbitrary_objects_and_wrong_fit_source_rejected(self):
        with self.assertRaises(ValueError):load_registered_adapter(object(),self.fit)
        with self.assertRaises(ValueError):load_registered_adapter(self.arima,self.fit[:-1]+(99.,))
        with self.assertRaises(ValueError):load_registered_adapter(replace(self.arima,source_sha256="wrong"),self.fit)
        with self.assertRaises(ValueError):RealAdapter(object(),None,None,None,None)

    def test_suffix_perturbation_invariance(self):
        a=self.engine(run="same");b=self.engine(run="same");aa=[];bb=[]
        for i in range(60,85):
            aa.append(a.advance(ts(i),40.+i%5))
            value=(None if i%2 else 99.) if i>=75 else 40.+i%5
            bb.append(b.advance(ts(i),value,"changed" if value is None else None))
        self.assertEqual(aa[:15],bb[:15]);self.assertNotEqual(aa[15:],bb[15:])

    def test_exact_missing_h12_target_delayed_feedback(self):
        s=self.engine();steps=[]
        for i in range(60,75):steps.append(s.advance(ts(i),None if i==72 else 40.,"gap" if i==72 else None))
        self.assertTrue(all(o.horizon==1 for step in steps[:12] for o in step.outcomes))
        f=next(f for f in steps[0].decisions if f.policy_id=="arima" and f.horizon==12)
        o=next(o for o in steps[12].outcomes if o.forecast_id==f.forecast_id)
        self.assertEqual(o.status,"target_unavailable");self.assertIsNone(o.absolute_error)
        self.assertFalse(any(o.forecast_id==f.forecast_id for o in steps[13].outcomes))

    def test_nonfinite_xgboost_logs_fallback(self):
        s=self.engine(self.xgb)
        with patch.object(xgb.Booster,"inplace_predict",return_value=np.array([[np.nan]])):
            step=s.advance(ts(60),41.)
        f=next(f for f in step.decisions if f.policy_id=="xgboost" and f.horizon==1)
        self.assertEqual(f.availability,"fallback");self.assertEqual(step.attempts[0].status,"numerical_failure")

    def test_failed_update_then_stale_abstention(self):
        s=self.engine();a=s._adapters["arima"]
        with patch.object(a.result,"extend",side_effect=RuntimeError("synthetic failure")):
            step=s.advance(ts(60),41.)
        self.assertEqual(step.updates[0].status,"numerical_failure")
        for i in range(61,65):step=s.advance(ts(i),None,"gap")
        self.assertTrue(a.resources()["state_invalid"]);self.assertTrue(all(f.availability=="abstained" for f in step.decisions))

    def test_training_targets_and_no_future_features(self):
        a=vals(90);b=a[:60]+(99.,)*30
        for h in (1,12):
            x,y,i=training_arrays(a[:60],h);xx,yy,j=training_arrays(b[:60],h)
            np.testing.assert_array_equal(x,xx);np.testing.assert_array_equal(y,yy);self.assertEqual(i,j)
            self.assertTrue(all(origin+h<60 for origin in i))
            np.testing.assert_array_equal(y,np.array([a[k+h] for k in i],dtype=np.float32))
        with self.assertRaises(ValueError):training_arrays(vals(865),1)

    def test_reproducible_weights_without_validation_labels(self):
        with TemporaryDirectory() as tmp:
            ref,_=save_artifact(Path(tmp)/"copy","synthetic","synthetic_source",self.fit,"xgboost",0,self.toy,synthetic=True)
            a=load_registered_adapter(ref,self.fit);b=load_registered_adapter(self.xgb,self.fit)
            self.assertEqual(a.parameter_sha256,b.parameter_sha256)

    def test_scope_and_old_locks(self):
        cfg,plan=load_execution()
        self.assertTrue(cfg["m3_training_allowed"]);self.assertFalse(cfg["confirmation_execution_allowed"])
        for name in ("dafr_engineering_pilot_v2.json","dafr_m3b_development_manifest_v1.json"):
            self.assertFalse(json.loads((ROOT/"configs"/name).read_text())["m3_training_allowed"])
        with patch.object(Path,"read_bytes") as read:
            with self.assertRaises(ValueError):load_source("m_3276",cfg)
            read.assert_not_called()

    def test_no_model_overwrite(self):
        with self.assertRaises(FileExistsError):
            save_artifact(self.arima.directory,"synthetic","synthetic_source",self.fit,"arima",0,self.toy,synthetic=True,known_params=[20,.5,1])

    def test_memory_guard_and_historical_hashes(self):
        with self.assertRaises(MemoryError):enforce_memory(0)
        r=json.loads((ROOT/"reports/dafr/m3b2_preservation_v1.json").read_text())
        self.assertEqual(r["file_count"],103)
        for path,sha in r["protected_sha256"].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha,path)

    def test_selection_ties_failures_and_h1_only(self):
        fits=[];rows=[]
        for family in ("arima","xgboost"):
            for c in (0,1,2):
                for machine in ("m_505","m_1426","m_3028"):
                    fits.append({"family":family,"candidate_index":c,"status":"accepted" if c<2 else "rejected"})
                    rows.append({"family":family,"candidate_index":c,"horizon":1,"matched_gate_policy":{"mae":1+c*1e-10,"rmse":2-c*.1}})
                    rows.append({"family":family,"candidate_index":c,"horizon":12,"matched_gate_policy":{"mae":100-c,"rmse":100.}})
        r=choose_global(rows,fits)
        self.assertEqual(r["families"]["arima"]["winner_candidate_index"],1);self.assertFalse(r["h12_selected_separately"])

if __name__=="__main__":unittest.main()

