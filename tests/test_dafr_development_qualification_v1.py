"""M3B-1 counting, scope and planning tests. No optimization or training."""

import csv
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dafr.development_qualification_v1 import (  # noqa: E402
    EPOCH, FIELDS, FIT_END, PREFIX_DIRECTORY, PRIMARY_IDS, RESERVE_IDS,
    disjoint_spans, example_origins, learned_origins, longest_run,
    prefix_summary, qualify_development_prefixes, read_development_mask, validate_prefix_csv,
)


def payload(n=1152, missing=()):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(FIELDS)
    for i in range(n):
        writer.writerow([(EPOCH + timedelta(seconds=300*(i+1))).isoformat(), str(300*(i+1)),
                         "" if i in missing else "0", "failed" if i in missing else "valid",
                         "test_gap" if i in missing else ""])
    return buffer.getvalue().encode()


class DevelopmentPlanningTests(unittest.TestCase):
    def test_source_validator_preserves_missing_positions_and_genuine_zero(self):
        mask = validate_prefix_csv(payload(missing={0, 24, 25, 26}))
        self.assertEqual(len(mask), 1152)
        self.assertEqual(sum(mask), 1148)
        self.assertFalse(mask[0])
        self.assertTrue(mask[1])
        self.assertNotIn(49, learned_origins(mask))
        self.assertIn(50, learned_origins(mask))

    def test_bad_schema_grid_values_quality_and_truncated_prefix_rejected(self):
        good = payload(2)
        changes = [good.replace(b"quality_status", b"wrong_field"),
                   good.replace(b",600,", b",300,"),
                   good.replace(b",0,valid,", b",nan,valid,"),
                   good.replace(b",0,valid,", b",101,valid,"),
                   good.replace(b",0,valid,", b",,valid,"),
                   good.replace(b",0,valid,", b",0,failed,"),
                   good.replace(b"+00:00", b""),
                   good.replace(b"2000-01-01T00:05:00+00:00", b"2000-01-01T05:35:00+05:30")]
        for data in changes:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_prefix_csv(data, 2)
        with self.assertRaises(ValueError):
            validate_prefix_csv(good, 3)
        with self.assertRaises(ValueError):
            validate_prefix_csv(good, 1)

    def test_confirmation_ids_rejected_before_any_data_read(self):
        with patch.object(Path, "read_bytes") as read:
            for machine in ("m_295", "m_66", "../m_505", "m_9999"):
                with self.assertRaises(ValueError):
                    read_development_mask(ROOT, machine, "0"*64)
            read.assert_not_called()

    def test_wrong_hash_and_symlink_redirection_are_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / PREFIX_DIRECTORY / "m_505.csv"
            target.parent.mkdir(parents=True)
            target.write_bytes(payload())
            with self.assertRaises(ValueError):
                read_development_mask(root, "m_505", "0"*64)
            expected = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(sum(read_development_mask(root, "m_505", expected)), 1152)
            other = root / "elsewhere.csv"
            other.write_bytes(target.read_bytes())
            target.unlink()
            target.symlink_to(other)
            with self.assertRaises(ValueError):
                read_development_mask(root, "m_505", expected)

    def test_training_targets_never_cross_cutoff_for_either_horizon(self):
        mask = (True,)*100
        self.assertEqual(len(example_origins(mask, 1, 0, 60)), 36)
        self.assertEqual(len(example_origins(mask, 12, 0, 60)), 25)
        for h in (1, 12):
            for origin in example_origins(mask, h, 0, 60):
                self.assertLess(origin+h, 60)
                self.assertLess(origin, origin+h)

    def test_validation_does_not_backdate_model_ready_origin(self):
        mask = (True,)*100
        for h, expected in ((1, 39), (12, 28)):
            origins = example_origins(mask, h, 60, 100, 60)
            self.assertEqual(len(origins), expected)
            self.assertEqual(origins[0], 60)
            self.assertEqual(origins[0]+h, 60+h)
            self.assertTrue(all(i>=60 and i+h<100 for i in origins))

    def test_missing_target_never_becomes_training_ground_truth(self):
        mask = tuple(i not in {35, 36} for i in range(100))
        self.assertNotIn(23, example_origins(mask, 12, 0, 60))
        self.assertNotIn(34, example_origins(mask, 1, 0, 60))
        self.assertFalse(any(mask[i] for i in (35, 36)))

    def test_intermediate_future_gap_does_not_require_imputation_for_direct_label(self):
        mask = tuple(i != 30 for i in range(80))
        self.assertIn(23, example_origins(mask, 12, 0, 60))
        # Inputs 0..23 and target 35 are genuine; the missing index 30 is not an input.
        self.assertNotIn(30, learned_origins(mask))

    def test_later_mask_changes_cannot_change_inner_fit_examples(self):
        a = (True,)*1152
        b = a[:864]+(False,)*288
        for h in (1, 12):
            self.assertEqual(example_origins(a,h,0,864), example_origins(b,h,0,864))

    def test_nonoverlapping_span_count_is_not_overlapping_window_count(self):
        origins = tuple(range(23, 100))
        self.assertEqual(disjoint_spans(origins, 1), 4)
        self.assertEqual(disjoint_spans(origins, 12), 3)
        self.assertLess(disjoint_spans(origins,12), len(origins))

    def test_invalid_masks_horizons_and_bounds_are_rejected(self):
        for mask,h,start,end,origin in [([True]*100,1,0,60,0), ((1,)*100,1,0,60,0),
                                      ((True,)*100,True,0,60,0), ((True,)*100,2,0,60,0),
                                      ((True,)*100,1,0,101,0), ((True,)*100,1,60,60,0),
                                      ((True,)*100,1,0,60,-1)]:
            with self.assertRaises(ValueError):
                example_origins(mask,h,start,end,origin)

    def test_failing_frozen_screens_do_not_qualify_an_empty_mask(self):
        screens=json.loads((ROOT/'configs/dafr_engineering_pilot_v2.json').read_text())['prefix_eligibility']
        result=prefix_summary((False,)*1152,screens)
        self.assertFalse(result['all_v2_screens_pass'])
        self.assertTrue(all(v is False for v in result['screen_results'].values()))

    def test_actual_six_prefixes_match_manifest_and_independent_counts(self):
        evidence=qualify_development_prefixes(ROOT)
        manifest=json.loads((ROOT/'configs/dafr_m3b_development_manifest_v1.json').read_text())
        self.assertEqual(evidence,manifest['machine_evidence'])
        expected={"m_505":(329,314,206,204),"m_1426":(303,284,236,224),"m_3028":(243,223,254,242)}
        for machine,r in evidence.items():
            self.assertTrue(r['all_v2_screens_pass'])
            mask=read_development_mask(ROOT,machine,r['source_sha256'])
            for h in (1,12):
                training=[]; validation=[]
                for i in range(1152):
                    if i<23 or i+h>=1152 or not mask[i+h] or False in mask[i-23:i+1]:
                        continue
                    if i+h<864:training.append(i)
                    if i>=864:validation.append(i)
                saved=r['per_horizon'][str(h)]
                self.assertEqual(len(training),saved['xgboost_direct_training_examples'])
                self.assertEqual(len(validation),saved['arima_xgboost_lstm_common_validation_pairs'])
            if machine in expected:
                self.assertEqual(tuple(r['per_horizon'][str(h)][key] for key in ('xgboost_direct_training_examples','arima_xgboost_lstm_common_validation_pairs') for h in (1,12)), expected[machine])

    def test_original_primary_and_reserve_order_and_execution_locks(self):
        manifest=json.loads((ROOT/'configs/dafr_m3b_development_manifest_v1.json').read_text())
        self.assertEqual(tuple(manifest['selected_primary_ids']),PRIMARY_IDS)
        self.assertEqual(tuple(manifest['eligible_reserve_ids_in_original_order']),RESERVE_IDS)
        self.assertEqual(manifest['reserves_promoted'],[])
        self.assertFalse(manifest['m3_training_allowed'])
        self.assertFalse(manifest['confirmation_execution_allowed'])
        self.assertFalse(manifest['selection']['prior_nab_outcomes_used'])
        self.assertTrue(manifest['selection']['no_winner_backdated_into_validation'])

    def test_arima_common_likelihood_settings_construct_without_fitting(self):
        import numpy as np
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        manifest=json.loads((ROOT/'configs/dafr_m3b_development_manifest_v1.json').read_text())['arima']
        y=np.full(60,40.0); y[15:18]=np.nan
        for order in manifest['candidate_orders']:
            model=SARIMAX(y,order=tuple(order),trend='c' if order[1]==0 else 'n',
                simple_differencing=False,enforce_stationarity=True,enforce_invertibility=True,
                initialization='approximate_diffuse',loglikelihood_burn=24)
            self.assertEqual(model.nobs,60)
            self.assertEqual(model.loglikelihood_burn,24)
            self.assertEqual(model.ssm.initialization.initialization_type,'approximate_diffuse')
            self.assertEqual(model.ssm.initialization.approximate_diffuse_variance,1000000)
        # No .fit(), filter, smoothing, parameter estimation or forecast is called.

    def test_all_95_historical_hashes_and_six_input_hashes_preserved(self):
        receipt=json.loads((ROOT/'reports/dafr/m3b1_preservation_v1.json').read_text())
        self.assertEqual(receipt['file_count'],95)
        for path,expected in {**receipt['protected_sha256'],**receipt['development_input_sha256']}.items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)


if __name__=='__main__':
    unittest.main()
