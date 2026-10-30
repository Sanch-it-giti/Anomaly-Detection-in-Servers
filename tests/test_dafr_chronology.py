"""Causal, provenance and artifact-preservation tests for DAF-R M1.

These tests use deterministic synthetic data only. No forecasting model is
trained and no historical forecasting script is executed.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dafr.contracts import (  # noqa: E402
    ForecastRecord, Provenance, score_forecast, validate_lags,
)
from dafr.streaming import (  # noqa: E402
    ForecastLedger, Protocol, StreamingSimulator, StubExpert, load_protocol,
    metric_summary, run_stream, synthetic_series,
)


EXPERTS = (StubExpert(), StubExpert("offset_stub", mode="offset", offset_per_step=0.5))
HISTORICAL_HASHES = {
    "data/processed/arima_212_holdout_forecast.csv":
        "3cbf0922294bcd0206b1e1ab6d6d22f404c69c3807da8c7f919d7ee0506c669b",
    "data/processed/xgboost_holdout_forecast.csv":
        "83296f5e23265ff0e3f1bbf8d66cd45ceb3839601b0647b1444943c0f8ce884d",
}


def engine(**kwargs) -> StreamingSimulator:
    return StreamingSimulator("test_run", "synthetic_dataset", "machine_1", **kwargs)


def replay(samples, **kwargs):
    simulator = engine(**kwargs)
    return simulator, tuple(simulator.advance(t, value) for t, value in samples)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


class ChronologyTests(unittest.TestCase):
    def test_future_perturbation_and_appended_suffix_leave_prefix_identical(self):
        samples = synthetic_series(24)
        changed = samples[:15] + tuple((t, value + 500) for t, value in samples[15:])
        _, original = replay(samples, experts=EXPERTS)
        _, perturbed = replay(changed, experts=EXPERTS)
        _, prefix_only = replay(samples[:15], experts=EXPERTS)
        # Entire event bundles include predictions, intervals, selected expert,
        # detector placeholders, matured-error counts and calibration metadata.
        self.assertEqual(original[:15], perturbed[:15])
        self.assertEqual(original[:15], prefix_only)
        self.assertNotEqual(original[15].forecasts, perturbed[15].forecasts)

    def test_h12_errors_arrive_only_at_target_including_warmup_boundary(self):
        simulator, steps = replay(synthetic_series(14))
        for step in steps[:12]:
            h12 = next(s for s in step.state.error_histories if s.horizon == 12)
            self.assertEqual(h12.total_matured, 0)
            self.assertIsNone(h12.latest_target)
            self.assertTrue(all(s.horizon == 1 for s in step.scores))
        arrival = steps[12]
        self.assertEqual(arrival.observation.phase, "evaluation")
        matured = [s for s in arrival.scores if s.horizon == 12]
        self.assertEqual(len(matured), 1)
        self.assertEqual(matured[0].origin, steps[0].observation.timestamp)
        self.assertEqual(matured[0].absolute_error, 12.0)
        future_record = next(f for f in arrival.forecasts if f.horizon == 12)
        self.assertEqual(future_record.provenance.matured_error_count, 1)
        self.assertEqual(future_record.provenance.error_history_latest_target, arrival.observation.timestamp)
        self.assertTrue(all(s.target <= arrival.observation.timestamp for s in simulator.ledger.scores[:13]))

    def test_sequence_is_arrival_then_scores_then_state_then_future_issues(self):
        simulator, steps = replay(synthetic_series(16), experts=EXPERTS)
        issued = {f.forecast_id: f for f in simulator.ledger.forecasts}
        sequence_numbers = []
        for step in steps:
            events = [step.observation.sequence] + [s.sequence for s in step.scores]
            events += [step.state.sequence] + [f.issued_sequence for f in step.forecasts]
            self.assertEqual(events, sorted(events))
            self.assertEqual(len(events), len(set(events)))
            sequence_numbers.extend(events)
            for score in step.scores:
                forecast = issued[score.forecast_id]
                self.assertLess(forecast.issued_sequence, step.observation.sequence)
                self.assertLess(step.observation.sequence, score.sequence)
                self.assertEqual(score.target, step.observation.timestamp)
                self.assertLess(score.origin, score.target)
            for forecast in step.forecasts:
                self.assertGreater(forecast.target, step.observation.timestamp)
                self.assertLess(step.state.sequence, forecast.issued_sequence)
        self.assertEqual(sequence_numbers, list(range(1, len(sequence_numbers) + 1)))

    def test_scoring_joins_shuffled_forecasts_by_target_and_preserves_horizon(self):
        _, steps = replay(synthetic_series(14), experts=EXPERTS)
        target_observation = steps[12].observation
        due = [f for step in steps for f in step.forecasts if f.target == target_observation.timestamp]
        self.assertEqual(len(due), 4)  # Two experts times two distinct horizons.
        scores = [score_forecast(f, target_observation, target_observation.sequence + index + 1)
                  for index, f in enumerate(reversed(due))]
        self.assertEqual({s.horizon for s in scores}, {1, 12})
        by_id = {f.forecast_id: f for f in due}
        for score in scores:
            self.assertEqual(score.predicted_value, by_id[score.forecast_id].predicted_value)
            self.assertEqual(score.absolute_error, abs(target_observation.value - score.predicted_value))
        with self.assertRaises(ValueError):
            score_forecast(due[0], steps[11].observation, target_observation.sequence + 1)
        with self.assertRaises(ValueError):
            score_forecast(due[0], replace(target_observation, dataset_id="wrong_dataset"), target_observation.sequence + 1)

    def test_unarrived_tail_is_retained_and_unscored(self):
        simulator, _ = replay(synthetic_series(18), experts=EXPERTS)
        self.assertEqual(len(simulator.ledger.forecasts), 72)
        self.assertEqual(len(simulator.ledger.scores), 46)
        self.assertEqual(len(simulator.ledger.unscored), 26)
        last = synthetic_series(18)[-1][0]
        pending_ids = set(simulator.ledger.unscored)
        self.assertTrue(all(f.target > last for f in simulator.ledger.forecasts if f.forecast_id in pending_ids))

    def test_stub_unavailability_uses_logged_persistence_without_dropping_targets(self):
        experts = (StubExpert(), StubExpert("offline_stub", mode="unavailable"))
        simulator, steps = replay(synthetic_series(18), experts=experts)
        for step in steps:
            for forecast in step.forecasts:
                self.assertEqual(forecast.predicted_value, step.observation.value)
                if forecast.expert_id == "offline_stub":
                    self.assertEqual(forecast.model_id, "persistence")
                    self.assertEqual(forecast.selected_expert, "persistence")
                    self.assertEqual(forecast.fallback_reason, "stub_unavailable")
        for horizon in (1, 12):
            keys = [{(s.origin, s.target, s.horizon) for s in simulator.ledger.scores
                     if s.expert_id == expert and s.horizon == horizon}
                    for expert in ("persistence", "offline_stub")]
            self.assertEqual(*keys)

    def test_records_and_nested_provenance_are_immutable(self):
        simulator = engine()
        step = simulator.advance(*synthetic_series(1)[0])
        forecast = step.forecasts[0]
        before = asdict(forecast)
        with self.assertRaises(FrozenInstanceError):
            forecast.predicted_value = 999.0
        with self.assertRaises(FrozenInstanceError):
            forecast.provenance.matured_error_count = 99
        for sample in synthetic_series(15)[1:]:
            simulator.advance(*sample)
        self.assertEqual(before, asdict(simulator.ledger.forecasts[0]))

    def test_observation_and_error_buffers_are_bounded(self):
        simulator, steps = replay(synthetic_series(30), protocol=Protocol(history_limit=2, error_history_limit=3))
        self.assertEqual(len(simulator._history), 2)
        for snapshot in steps[-1].state.error_histories:
            self.assertEqual(snapshot.buffered_count, 3)
            self.assertGreater(snapshot.total_matured, snapshot.buffered_count)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.simulator = engine()
        self.step = self.simulator.advance(*synthetic_series(1)[0])
        self.forecast = self.step.forecasts[0]

    def test_training_scaling_and_version_cutoffs_cannot_exceed_origin(self):
        for name in ("training_cutoff", "scaling_cutoff", "version_available_at"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                replace(self.forecast, **{name: self.forecast.origin + timedelta(minutes=5)})
        with self.assertRaises(ValueError):
            replace(self.forecast, training_cutoff=self.forecast.origin,
                    version_available_at=self.forecast.origin - timedelta(minutes=5))

    def test_future_selection_detector_calibration_and_error_provenance_rejected(self):
        future = self.forecast.origin + timedelta(minutes=5)
        for changes in ({"selection_cutoff": future}, {"detector_cutoff": future},
                        {"calibration_score_count": 1, "calibration_latest_target": future},
                        {"matured_error_count": 1, "error_history_latest_target": future}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.forecast.provenance, **changes)
        with self.assertRaises(ValueError):
            replace(self.forecast.provenance, calibration_score_count=1)
        with self.assertRaises(ValueError):
            replace(self.forecast.provenance, matured_error_count=True)

    def test_bad_forecast_values_timestamps_horizons_ids_and_sequence_rejected(self):
        for changes in (
            {"predicted_value": float("nan")}, {"predicted_value": float("inf")},
            {"predicted_value": True}, {"predicted_value": "42"},
            {"horizon": 1.5}, {"horizon": True}, {"horizon": 0}, {"horizon": 2},
            {"target": self.forecast.origin}, {"cadence_seconds": 60},
            {"origin": self.forecast.origin.replace(tzinfo=None)},
            {"issued_sequence": self.step.observation.sequence},
            {"run_id": "../escape"}, {"model_version": ""},
            {"provenance": None}, {"selected_expert": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.forecast, **changes)

    def test_intervals_and_immutable_weights_are_validated(self):
        valid = replace(self.forecast, interval_status="available", lower=39.0, upper=41.0, nominal_coverage=0.9)
        self.assertEqual(valid.interval_status, "available")
        weighted = replace(self.forecast, selected_expert=None, weights=(("a", 0.4), ("b", 0.6)))
        self.assertEqual(len(weighted.weights), 2)
        for changes in (
            {"interval_status": "available"}, {"lower": 39.0},
            {"interval_status": "unknown"},
            {"interval_status": "available", "lower": 50., "upper": 40., "nominal_coverage": 0.9},
            {"interval_status": "available", "lower": 39., "upper": float("inf"), "nominal_coverage": 0.9},
            {"selected_expert": None, "weights": (("a", 0.2),)},
            {"selected_expert": None, "weights": (("a", 0.5), ("a", 0.5))},
            {"selected_expert": None, "weights": (("a", -1.), ("b", 2.))},
            {"selected_expert": None, "weights": [["a", 1.0]]},
            {"weights": (("a", 1.0),)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.forecast, **changes)

    def test_duplicate_forecast_ids_keys_and_scores_rejected(self):
        with self.assertRaises(ValueError):
            self.simulator.ledger.issue(self.forecast, self.step.observation)
        with self.assertRaises(ValueError):
            self.simulator.ledger.issue(replace(self.forecast, forecast_id="different_id"), self.step.observation)
        later = self.simulator.advance(*synthetic_series(2)[1])
        with self.assertRaises(ValueError):
            self.simulator.ledger.score(self.forecast, later.observation, later.state.sequence + 100)
        with self.assertRaises(ValueError):
            self.simulator.ledger.score(replace(self.forecast, predicted_value=999.), later.observation, later.state.sequence + 100)

    def test_origin_observation_identity_must_match(self):
        ledger = ForecastLedger()
        with self.assertRaises(ValueError):
            ledger.issue(replace(self.forecast, origin_observation_id="unrevealed"), self.step.observation)

    def test_duplicate_event_sequences_rejected_even_for_distinct_experts(self):
        with self.assertRaises(ValueError):
            self.simulator.ledger.issue(
                replace(self.forecast, forecast_id="new_id", expert_id="another_expert"),
                self.step.observation,
            )

    def test_score_cannot_precede_arrival_and_cannot_invent_error(self):
        later = self.simulator.advance(*synthetic_series(2)[1])
        with self.assertRaises(ValueError):
            score_forecast(self.forecast, later.observation, later.observation.sequence)
        with self.assertRaises(ValueError):
            score_forecast(self.forecast, replace(later.observation, sequence=1), 2)
        with self.assertRaises(ValueError):
            replace(later.scores[0], absolute_error=999.)
        with self.assertRaises(ValueError):
            replace(later.scores[0], actual=float("nan"))

    def test_invalid_observations_are_rejected_before_state_changes(self):
        timestamp = self.step.observation.timestamp
        for sample in (
            (timestamp, 42.), (timestamp - timedelta(minutes=5), 42.),
            (timestamp + timedelta(minutes=10), 42.),
            (timestamp.replace(tzinfo=None) + timedelta(minutes=5), 42.),
            ("not-a-datetime", 42.), (None, 42.),
            (timestamp + timedelta(minutes=5), float("nan")),
            (timestamp + timedelta(minutes=5), float("inf")),
            (timestamp + timedelta(minutes=5), True),
            (timestamp + timedelta(minutes=5), "42"),
        ):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                self.simulator.advance(*sample)
        self.assertEqual(self.simulator._observation_count, 1)
        self.assertEqual(len(self.simulator.ledger.forecasts), 2)
        self.simulator.advance(*synthetic_series(2)[1])  # Still usable after rejected input.

    def test_fractional_nonpositive_duplicate_and_boolean_lags_rejected(self):
        for lags in ((1.2,), (0,), (-1,), (True,), (1, 1), (), [1]):
            with self.subTest(lags=lags), self.assertRaises(ValueError):
                validate_lags(lags)

    def test_protocol_rejects_unsupported_settings(self):
        for changes in ({"detector": "adwin"}, {"calibration": "aci"},
                        {"horizons": (True, 12)}, {"warmup_observations": -1},
                        {"history_limit": 0}, {"lags": (1.5,)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Protocol(**changes)
        protocol = load_protocol(PROJECT_ROOT / "configs/dafr_protocol_v1.json")
        self.assertEqual(protocol.horizons, (1, 12))

    def test_expert_contract_rejects_missing_baseline_and_duplicate_experts(self):
        for experts in ((), (StubExpert("other"),), (StubExpert(), StubExpert()), [StubExpert()]):
            with self.subTest(experts=experts), self.assertRaises(ValueError):
                engine(experts=experts)


class RunArtifactTests(unittest.TestCase):
    def test_run_creates_versioned_ledger_and_linked_events_and_refuses_overwrite(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = run_stream(iter(synthetic_series()), run_id="artifact_test", dataset_id="synthetic",
                              experts=EXPERTS, project_root=root)
            self.assertEqual(path, root.resolve() / "data/processed/dafr/v1/artifact_test")
            manifest = json.loads((path / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(len(manifest["input_sha256"]), 64)
            forecasts = read_jsonl(path / "forecasts.jsonl")
            scores = read_jsonl(path / "scores.jsonl")
            states = read_jsonl(path / "states.jsonl")
            self.assertEqual((len(forecasts), len(scores), len(states)), (72, 46, 18))
            lookup = {f["forecast_id"]: f for f in forecasts}
            for score in scores:
                original = lookup[score["forecast_id"]]
                self.assertEqual((score["target"], score["horizon"], score["predicted_value"]),
                                 (original["target"], original["horizon"], original["predicted_value"]))
            events = read_jsonl(path / "events.jsonl")
            sequences = [event["record"].get("sequence", event["record"].get("issued_sequence")) for event in events]
            self.assertEqual(sequences, list(range(1, len(events) + 1)))
            summary = json.loads((path / "summary.json").read_text())
            self.assertEqual(len(summary["pending_forecast_ids"]), 26)
            self.assertEqual({m["horizon"] for m in summary["evaluation_metrics"]}, {1, 12})
            before = {p.name: p.read_bytes() for p in path.iterdir()}
            with self.assertRaises(FileExistsError):
                run_stream(synthetic_series(), run_id="artifact_test", dataset_id="synthetic", project_root=root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in path.iterdir()})

    def test_empty_or_gapped_stream_fails_with_explicit_manifest(self):
        with TemporaryDirectory() as directory:
            for name, samples in (("empty", ()), ("gap", synthetic_series()[::2])):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    run_stream(samples, run_id=name, dataset_id="synthetic", project_root=Path(directory))
                manifest_path = Path(directory) / f"data/processed/dafr/v1/{name}/manifest.json"
                self.assertEqual(json.loads(manifest_path.read_text())["status"], "failed")

    def test_run_id_traversal_and_symlink_escape_rejected(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as outside:
            root = Path(directory)
            for run_id in ("../arima_212_holdout_forecast.csv", "", "a/b", ".."):
                with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                    run_stream(synthetic_series(), run_id=run_id, dataset_id="synthetic", project_root=root)
            (root / "data/processed").mkdir(parents=True)
            (root / "data/processed/dafr").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                run_stream(synthetic_series(), run_id="escape", dataset_id="synthetic", project_root=root)

    def test_in_project_symlink_cannot_redirect_versioned_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/processed").mkdir(parents=True)
            (root / "historical").mkdir()
            (root / "data/processed/dafr").symlink_to(root / "historical", target_is_directory=True)
            with self.assertRaises(ValueError):
                run_stream(synthetic_series(), run_id="redirect", dataset_id="synthetic", project_root=root)
            self.assertEqual(list((root / "historical").iterdir()), [])

    def test_metric_summary_rejects_duplicate_scores_and_is_order_independent(self):
        simulator, _ = replay(synthetic_series(18), experts=EXPERTS)
        scores = simulator.ledger.scores
        self.assertEqual(metric_summary(scores), metric_summary(reversed(scores)))
        with self.assertRaises(ValueError):
            metric_summary(scores + scores[:1])

    def test_historical_artifacts_unchanged_even_when_new_run_is_saved(self):
        before = {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                  for name in HISTORICAL_HASHES}
        self.assertEqual(before, HISTORICAL_HASHES)
        with TemporaryDirectory() as directory:
            run_stream(synthetic_series(), run_id="history_guard", dataset_id="synthetic", project_root=Path(directory))
        after = {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                 for name in HISTORICAL_HASHES}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
