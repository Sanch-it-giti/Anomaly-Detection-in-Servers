"""M3A: deterministic synthetic adapter lifecycle and preservation tests."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dafr.adapters_v1 import (  # noqa: E402
    AdapterResultV1, ExpertAdapterV1, MockAdapterSpec, MockAdapterV1, ModelVersionV1,
    ORIGIN_OFFSETS, default_mock_specs_v1, genuine_window_v1, origin_features_v1,
)
from dafr.streaming_adapters_v1 import AdapterStreamingSimulatorV1, run_mock_stream_v1  # noqa: E402
from dafr.streaming_v2 import StreamingSimulatorV2, synthetic_missing_series_v2  # noqa: E402


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rows(n, missing=()):
    return tuple((START + timedelta(minutes=5 * i), None if i in missing else 30.0 + i % 40,
                  "test_gap" if i in missing else None) for i in range(n))


def replay(samples, specs=None):
    simulator = AdapterStreamingSimulatorV1("test", "synthetic", specs=specs)
    return simulator, tuple(simulator.advance(*row) for row in samples)


def d(step, name="mock_arima", horizon=1):
    return next(f for f in step.decisions if f.policy_id == name and f.horizon == horizon)


def fault_spec(fault, ticks=(23,), horizon=None):
    return (MockAdapterSpec(ModelVersionV1("fault_mock", "v1", "arima"),
                            fault=fault, fault_ticks=ticks, fault_horizon=horizon),)


class AdapterLifecycleTests(unittest.TestCase):
    def test_future_value_mask_and_suffix_length_do_not_change_past(self):
        original = rows(90, {28, 50, 51, 52, 53})
        changed = original[:45] + tuple((t, 99.0, None) for t, _, _ in original[45:])
        _, a = replay(original)
        _, b = replay(changed)
        _, short = replay(original[:45])
        # Runtime measurement lives outside these deterministic causal events.
        self.assertEqual(a[:45], b[:45])
        self.assertEqual(a[:45], short)
        self.assertNotEqual(a[45:], b[45:])

    def test_identical_context_object_and_origin_for_updates_and_forecasts(self):
        seen = []
        update, forecast = MockAdapterV1.update, MockAdapterV1.forecast

        def record_update(adapter, tick, context):
            seen.append(("update", adapter.metadata.expert_id, context))
            return update(adapter, tick, context)

        def record_forecast(adapter, context, horizon):
            seen.append(("forecast", adapter.metadata.expert_id, context))
            return forecast(adapter, context, horizon)

        with patch.object(MockAdapterV1, "update", record_update), patch.object(MockAdapterV1, "forecast", record_forecast):
            _, steps = replay(rows(30))
        for step in steps:
            contexts = [c for _, _, c in seen if c.origin == step.tick.timestamp]
            self.assertEqual(len(contexts), 9 if step.state.learned_eligible else 3)
            self.assertTrue(all(c is contexts[0] for c in contexts))
            self.assertTrue(all(t.timestamp <= step.tick.timestamp for t in contexts[0].history))
            self.assertEqual({f.context_sha256 for f in step.decisions}, {contexts[0].context_sha256})

    def test_exact_horizons_and_only_current_genuine_window(self):
        _, steps = replay(rows(30))
        for step in steps:
            for f in step.decisions:
                self.assertEqual(f.target, f.origin + timedelta(minutes=5 * f.horizon))
            for attempt in step.attempts:
                if attempt.result:
                    self.assertEqual(attempt.result.target, step.tick.timestamp + timedelta(minutes=5 * attempt.horizon))
                    self.assertEqual(attempt.result.observation_cutoff, step.tick.timestamp)
        self.assertTrue(all(f.availability == "fallback" for f in steps[22].decisions if f.policy_id != "persistence"))
        self.assertTrue(all(f.availability == "expert" for f in steps[23].decisions if f.policy_id != "persistence"))

    def test_every_tick_updates_arima_step_and_only_genuine_ticks_measurement(self):
        missing = {2, 3, 4, 5, 20}
        simulator, steps = replay(rows(40, missing))
        for i, step in enumerate(steps):
            self.assertEqual(len(step.updates), 3)
            for update in step.updates:
                self.assertEqual(update.result.state_steps, i + 1)
                self.assertEqual(update.result.measurement_updates, i + 1 - len(missing.intersection(range(i + 1))))
                self.assertEqual(update.result.reason, "missing_transition" if i in missing else "genuine_update")
        for resource in simulator.resource_reports():
            self.assertEqual(resource.state_steps, 40)
            self.assertEqual(resource.measurement_updates, 35)
            self.assertEqual(resource.buffered_grid_slots, 24)

    def test_no_missing_compression_and_gate_recovers_at_24_genuine_ticks(self):
        simulator, steps = replay(rows(60, {24, 25, 26, 27}))
        self.assertTrue(steps[23].state.learned_eligible)
        self.assertFalse(steps[50].state.learned_eligible)
        self.assertTrue(steps[51].state.learned_eligible)
        self.assertEqual(d(steps[27]).availability, "abstained")
        self.assertEqual(d(steps[28]).availability, "fallback")
        for adapter in simulator._adapters.values():
            self.assertEqual(adapter.resources().update_calls, 60)

    def test_features_are_origin_relative_and_lstm_gets_same_window(self):
        simulator, steps = replay(rows(26))
        context = simulator._context(steps[-1].tick)
        values = genuine_window_v1(context)
        self.assertEqual(values, tuple(r[1] for r in rows(26)[-24:]))
        self.assertEqual(origin_features_v1(context), tuple(values[-1-o] for o in ORIGIN_OFFSETS))
        self.assertEqual(ORIGIN_OFFSETS, (0, 1, 2, 5, 11, 23))
        self.assertEqual(d(steps[-1], "mock_lstm", 12).predicted_value, sum(values) / 24 + 12 * .25)
        self.assertEqual(d(steps[-1], "mock_xgboost").predicted_value,
                         sum(origin_features_v1(context)) / 6 + .25)

    def test_window_helpers_and_forecast_reject_missing_or_insufficient_history(self):
        simulator, steps = replay(rows(30, {28}))
        for context in (simulator._context(steps[-1].tick),):
            with self.assertRaises(ValueError):
                genuine_window_v1(context)
            with self.assertRaises(ValueError):
                origin_features_v1(context)
            for adapter in simulator._adapters.values():
                with self.assertRaises(ValueError):
                    adapter.forecast(context, 1)

    def test_update_precedes_forecast_and_forecast_cannot_update_state(self):
        simulator, steps = replay(rows(25))
        context = simulator._context(steps[-1].tick)
        adapter = simulator._adapters["mock_arima"]
        digest = adapter.state_sha256
        result12 = adapter.forecast(context, 12)
        result1 = adapter.forecast(context, 1)
        self.assertEqual(adapter.state_sha256, digest)
        self.assertEqual((result12.value, result1.value), (d(steps[-1], horizon=12).predicted_value, d(steps[-1]).predicted_value))
        fresh = MockAdapterV1(default_mock_specs_v1()[0])
        with self.assertRaises(ValueError):
            fresh.forecast(context, 1)

    def test_forged_context_cannot_reuse_a_digest_with_different_values(self):
        simulator, steps = replay(rows(25))
        context = simulator._context(steps[-1].tick)
        changed = replace(context.history[0], value=99.0)
        forged = replace(context, history=(changed,) + context.history[1:])
        self.assertEqual(forged.context_sha256, context.context_sha256)
        for adapter in simulator._adapters.values():
            with self.assertRaises(ValueError):
                adapter.forecast(forged, 1)

    def test_update_unavailable_is_logged_and_does_not_silently_recover(self):
        simulator, steps = replay(rows(26), fault_spec("update_unavailable"))
        self.assertEqual(steps[23].updates[0].status, "unavailable")
        self.assertEqual(steps[24].updates[0].reason, "state_invalid")
        self.assertEqual(d(steps[25], "fault_mock").availability, "fallback")
        self.assertTrue(simulator.resource_reports()[0].state_invalid)

    def test_fitted_cutoffs_and_model_availability_propagate_only_on_expert_source(self):
        version = ModelVersionV1("declared_mock", "v7", "lstm", START - timedelta(minutes=5),
                                 START - timedelta(minutes=15), START - timedelta(minutes=10))
        _, steps = replay(rows(25), (MockAdapterSpec(version),))
        fallback = d(steps[22], "declared_mock")
        self.assertEqual(fallback.selected_expert, "persistence")
        self.assertIsNone(fallback.training_cutoff)
        self.assertIsNone(fallback.scaling_cutoff)
        self.assertIsNone(fallback.version_available_at)
        expert = d(steps[23], "declared_mock")
        self.assertEqual(expert.training_cutoff, version.training_cutoff)
        self.assertEqual(expert.scaling_cutoff, version.scaling_cutoff)
        self.assertEqual(expert.version_available_at, version.available_at)
        self.assertEqual(expert.source_version, "v7")
        self.assertEqual(steps[22].attempts[0].metadata, version)

    def test_future_fit_scale_or_availability_is_rejected_before_replay_mutates(self):
        for version in (
            ModelVersionV1("future", "v1", "arima", START + timedelta(minutes=5)),
            ModelVersionV1("future", "v1", "xgboost", START + timedelta(minutes=10), START + timedelta(minutes=5)),
            ModelVersionV1("future", "v1", "lstm", START + timedelta(minutes=10), None, START + timedelta(minutes=5)),
            ModelVersionV1("future", "v1", "arima", START, START),
        ):
            simulator = AdapterStreamingSimulatorV1("future", "synthetic", specs=(MockAdapterSpec(version),))
            with self.assertRaises(ValueError):
                simulator.advance(*rows(1)[0])
            self.assertEqual(simulator._ticks, 0)
            self.assertEqual(simulator._sequence, 0)
            self.assertEqual(simulator.resource_reports()[0].update_calls, 0)

    def test_bad_metadata_order_timezone_and_reserved_expert_are_rejected(self):
        for kwargs in ({"available_at": START.replace(tzinfo=None)},
                       {"training_cutoff": START}, {"scaling_cutoff": START},
                       {"provenance_kind": "real_model"}):
            with self.assertRaises(ValueError):
                ModelVersionV1("bad", "v1", "arima", **kwargs)
        with self.assertRaises(ValueError):
            ModelVersionV1("persistence", "v1", "arima")

    def test_forecast_failure_modes_fallback_then_retry_without_refit(self):
        for fault in ("forecast_error", "forecast_nonfinite", "forecast_unavailable"):
            _, steps = replay(rows(26), fault_spec(fault))
            failed = d(steps[23], "fault_mock")
            self.assertEqual(failed.availability, "fallback")
            self.assertEqual(failed.selected_expert, "persistence")
            self.assertIn(steps[23].attempts[0].status, ("numerical_failure", "unavailable"))
            self.assertEqual(d(steps[24], "fault_mock").availability, "expert")

    def test_horizon_specific_failure_does_not_taint_other_horizon(self):
        _, steps = replay(rows(25), fault_spec("forecast_nonfinite", horizon=1))
        self.assertEqual(d(steps[23], "fault_mock", 1).availability, "fallback")
        self.assertEqual(d(steps[23], "fault_mock", 12).availability, "expert")

    def test_failed_updates_latch_unavailable_without_compressing_ticks(self):
        simulator, steps = replay(rows(32, {25, 26, 27, 28, 29}), fault_spec("update_error"))
        self.assertEqual(steps[23].updates[0].status, "numerical_failure")
        self.assertEqual(steps[24].updates[0].status, "unavailable")
        self.assertEqual(d(steps[24], "fault_mock").availability, "fallback")
        self.assertEqual(d(steps[28], "fault_mock").availability, "abstained")
        self.assertEqual(d(steps[30], "fault_mock").availability, "fallback")
        report = simulator.resource_reports()[0]
        self.assertEqual(report.update_calls, 32)
        self.assertEqual(report.state_steps, 23)
        self.assertTrue(report.state_invalid)
        self.assertEqual(report.forecast_calls, 0)

    def test_genuine_and_missing_updates_are_called_even_while_gated(self):
        simulator, steps = replay(rows(15, set(range(15))))
        self.assertEqual(len(simulator.ledger.forecasts), 0)
        self.assertEqual(len(simulator.ledger.outcomes), 0)
        self.assertTrue(all(len(step.updates) == 3 for step in steps))
        self.assertTrue(all(r.update_calls == 15 and r.forecast_calls == 0 and r.measurement_updates == 0 for r in simulator.resource_reports()))

    def test_fixed_parameters_and_versions_cannot_change_mid_replay(self):
        simulator, _ = replay(rows(25))
        adapter = simulator._adapters["mock_arima"]
        adapter._spec = replace(adapter._spec, offset_per_step=1.0)
        count = simulator._ticks
        with self.assertRaises(ValueError):
            simulator.advance(*rows(26)[25])
        self.assertEqual(simulator._ticks, count)
        with self.assertRaises(FrozenInstanceError):
            adapter.metadata.version = "v99"

    def test_no_fit_refit_or_scaler_training_api_exists(self):
        self.assertEqual(ExpertAdapterV1.__abstractmethods__, {"metadata", "update", "forecast", "resources"})
        for spec in default_mock_specs_v1():
            adapter = MockAdapterV1(spec)
            for method in ("fit", "refit", "partial_fit", "fit_scaler"):
                self.assertFalse(hasattr(adapter, method))

    def test_arbitrary_objects_and_mock_subclasses_are_not_authorized(self):
        class PretendAdapter:
            pass

        class SubSpec(MockAdapterSpec):
            pass

        spec = default_mock_specs_v1()[0]
        for specs in ((PretendAdapter(),), (MockAdapterV1(spec),), [spec], (),
                      (SubSpec(spec.metadata),), (spec, spec)):
            with self.assertRaises(ValueError):
                AdapterStreamingSimulatorV1("unsafe", "synthetic", specs=specs)

    def test_response_identity_and_context_tampering_abort_instead_of_fallback(self):
        original = MockAdapterV1.forecast

        def bad_response(adapter, context, horizon):
            return replace(original(adapter, context, horizon), expert_id="wrong_expert")

        simulator, _ = replay(rows(23))
        with patch.object(MockAdapterV1, "forecast", bad_response), self.assertRaises(ValueError):
            simulator.advance(*rows(24)[23])

    def test_prediction_side_effect_is_detected(self):
        original = MockAdapterV1.forecast

        def stateful_forecast(adapter, context, horizon):
            adapter._state += 1
            return original(adapter, context, horizon)

        simulator, _ = replay(rows(23))
        with patch.object(MockAdapterV1, "forecast", stateful_forecast), self.assertRaises(ValueError):
            simulator.advance(*rows(24)[23])

    def test_missing_targets_and_h12_feedback_remain_exact_and_delayed(self):
        simulator, steps = replay(rows(45, {28}))
        self.assertTrue(all(o.horizon == 1 for step in steps[:12] for o in step.outcomes))
        forecast = d(steps[16], horizon=12)
        outcome = next(o for o in steps[28].outcomes if o.forecast_id == forecast.forecast_id)
        self.assertEqual(outcome.status, "target_unavailable")
        self.assertIsNone(outcome.actual)
        self.assertIsNone(outcome.absolute_error)
        self.assertTrue(all(o.forecast_id != forecast.forecast_id for o in steps[29].outcomes))
        self.assertEqual(len([o for o in simulator.ledger.outcomes if o.forecast_id == forecast.forecast_id]), 1)

    def test_no_issued_prediction_can_be_revised_after_later_updates(self):
        simulator = AdapterStreamingSimulatorV1("immutable", "synthetic")
        for row in rows(25):
            step = simulator.advance(*row)
        original = d(step)
        saved = asdict(original)
        for row in rows(45)[25:]:
            simulator.advance(*row)
        self.assertEqual(saved, asdict(original))
        self.assertEqual(next(f for f in simulator.ledger.forecasts if f.forecast_id == original.forecast_id), original)
        with self.assertRaises(FrozenInstanceError):
            original.predicted_value = 0

    def test_event_order_and_m2d_chronology_parity(self):
        samples = synthetic_missing_series_v2()
        _, steps = replay(samples)
        baseline = StreamingSimulatorV2("test", "synthetic")
        old_steps = tuple(baseline.advance(*row) for row in samples)
        sequences = []
        for step, old in zip(steps, old_steps):
            self.assertEqual((step.state.era, step.state.learned_eligible, step.state.context_sha256,
                              step.state.genuine_streak, step.state.missing_streak),
                             (old.state.era, old.state.learned_eligible, old.state.context_sha256,
                              old.state.genuine_streak, old.state.missing_streak))
            for horizon in (1, 12):
                a, b = d(step, "persistence", horizon), d(old, "persistence", horizon)
                for field in ("predicted_value", "availability", "target", "support_count", "support_latest_target"):
                    self.assertEqual(getattr(a, field), getattr(b, field))
            events = step.ordered()
            sequences.extend(e.sequence for _, e in events)
            self.assertTrue(all(o.sequence < step.updates[0].sequence for o in step.outcomes))
            self.assertTrue(all(u.sequence < step.state.sequence for u in step.updates))
            self.assertTrue(all(step.state.sequence < f.sequence for f in step.decisions))
            for attempt in step.attempts:
                f = d(step, attempt.metadata.expert_id, attempt.horizon)
                self.assertLess(attempt.sequence, f.sequence)
        self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_resources_are_bounded_observational_not_decision_inputs(self):
        simulator, steps = replay(rows(80, {25, 26, 27, 28}))
        for r in simulator.resource_reports():
            self.assertEqual(r.buffered_grid_slots, 24)
            self.assertEqual(r.update_calls, 80)
            self.assertGreater(r.elapsed_nanoseconds, 0)
        serialized = json.dumps(asdict(steps[-1]), default=str)
        self.assertNotIn("elapsed_nanoseconds", serialized)


class AdapterArtifactTests(unittest.TestCase):
    def test_mock_outputs_record_provenance_and_refuse_overwrite(self):
        with TemporaryDirectory() as temp:
            out = run_mock_stream_v1(rows(30, {28}), run_id="run", project_root=Path(temp))
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertFalse(manifest["training_performed"])
            self.assertFalse(manifest["confirmation_execution_allowed"])
            self.assertFalse(manifest["m3_training_allowed"])
            self.assertEqual(manifest["m2d_protocol_sha256"], hashlib.sha256((ROOT / "configs/dafr_engineering_pilot_v2.json").read_bytes()).hexdigest())
            events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines()]
            self.assertIn("adapter_update", {e["kind"] for e in events})
            self.assertIn("adapter_attempt", {e["kind"] for e in events})
            with self.assertRaises(FileExistsError):
                run_mock_stream_v1(rows(1), run_id="run", project_root=Path(temp))
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})

    def test_invalid_stream_has_failure_receipt_and_reserved_id(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                run_mock_stream_v1((rows(3)[0], rows(3)[2]), run_id="invalid", project_root=Path(temp))
            out = Path(temp) / "data/processed/dafr/m3a_mock_v1/invalid"
            self.assertEqual(json.loads((out / "completion.json").read_text())["status"], "failed")
            with self.assertRaises(FileExistsError):
                run_mock_stream_v1(rows(1), run_id="invalid", project_root=Path(temp))

    def test_output_symlinks_and_traversal_are_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                run_mock_stream_v1(rows(1), run_id="../bad", project_root=root)
            outside = root / "outside"
            outside.mkdir()
            (root / "data").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                run_mock_stream_v1(rows(1), run_id="bad", project_root=root)
            self.assertFalse(list(outside.iterdir()))

    def test_all_85_prior_artifact_hashes_and_m2d_locks_are_unchanged(self):
        receipt = json.loads((ROOT / "reports/dafr/m3a_preservation_v1.json").read_text())
        self.assertEqual(receipt["file_count"], 85)
        for path, expected in receipt["protected_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)
        config = json.loads((ROOT / "configs/dafr_engineering_pilot_v2.json").read_text())
        self.assertFalse(config["confirmation_execution_allowed"])
        self.assertFalse(config["m3_training_allowed"])
        self.assertFalse(config["engine"]["m3_training_allowed"])


if __name__ == "__main__":
    unittest.main()
