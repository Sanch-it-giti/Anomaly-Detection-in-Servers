"""M2D tests: synthetic events only, no model fitting or sealed data reads."""

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

from dafr.contracts_v2 import resolve_target_v2  # noqa: E402
from dafr.streaming_v2 import (  # noqa: E402
    PilotProtocolV2, StreamingSimulatorV2, StubExpertV2, load_pilot_protocol_v2,
    run_stream_v2, synthetic_missing_series_v2,
)


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
EXPERTS = (StubExpertV2(), StubExpertV2("stub_last"),
           StubExpertV2("stub_offset", mode="offset", offset_per_step=0.25))


def rows(count, missing=()):
    return tuple((START + timedelta(minutes=5 * i), None if i in missing else 40.0 + i % 9,
                  "test_gap" if i in missing else None) for i in range(count))


def replay(samples, experts=EXPERTS):
    simulator = StreamingSimulatorV2("test_run", "synthetic", experts=experts)
    return simulator, tuple(simulator.advance(*r) for r in samples)


def decision(step, policy="stub_last", horizon=1):
    return next(d for d in step.decisions if d.policy_id == policy and d.horizon == horizon)


def support(step, policy="stub_last", horizon=1):
    return next(s for s in step.state.support if s.policy_id == policy and s.horizon == horizon)


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


class MissingChronologyV2Tests(unittest.TestCase):
    def test_leading_missing_ticks_are_honest_abstentions(self):
        simulator, steps = replay(rows(30, {0, 1, 2}))
        for step in steps[:3]:
            self.assertTrue(all(d.availability == "abstained" and d.predicted_value is None for d in step.decisions))
            self.assertEqual(step.outcomes, ())
            self.assertIsNone(step.state.last_genuine_age_ticks)
        self.assertEqual(decision(steps[3]).availability, "fallback")
        self.assertFalse(steps[25].state.learned_eligible)
        self.assertTrue(steps[26].state.learned_eligible)
        self.assertEqual(decision(steps[26]).availability, "expert")
        self.assertEqual(steps[-1].state.grid_ticks, 30)
        self.assertEqual(steps[-1].state.genuine_ticks, 27)

    def test_all_missing_stream_has_no_predictions_errors_or_fake_support(self):
        simulator, steps = replay(rows(15, set(range(15))))
        self.assertEqual(simulator.ledger.forecasts, ())
        self.assertEqual(simulator.ledger.outcomes, ())
        self.assertEqual(simulator.ledger.pending_ids, ())
        self.assertEqual(len(simulator.ledger.decisions), 15 * 6)
        self.assertEqual(sum(s.reset is not None for s in steps), 1)
        self.assertIsNotNone(steps[3].reset)
        self.assertTrue(all(s.count == 0 and not s.ready for s in steps[-1].state.support))

    def test_zero_cpu_is_genuine_not_missing_or_abstention(self):
        samples = tuple((START + timedelta(minutes=5 * i), 0.0, None) for i in range(26))
        simulator, steps = replay(samples)
        self.assertTrue(all(s.tick.genuine for s in steps))
        self.assertEqual(decision(steps[23]).availability, "expert")
        self.assertTrue(all(o.status == "scored" and o.actual == 0.0 for o in simulator.ledger.outcomes))

    def test_pilot_memory_guard_rejects_additional_ticks_without_mutation(self):
        simulator = StreamingSimulatorV2("guard", "synthetic")
        simulator.advance(START, 40)
        # Exercise the cap directly without manufacturing 2,304 audit ticks.
        simulator._ticks = 2304
        previous = simulator._sequence
        with self.assertRaises(ValueError):
            simulator.advance(START + timedelta(minutes=5), 40)
        self.assertEqual(simulator._sequence, previous)

    def test_one_three_four_tick_gaps_and_24_genuine_recovery(self):
        for gap_length in (1, 3, 4):
            with self.subTest(gap_length=gap_length):
                _, steps = replay(rows(24 + gap_length + 24, set(range(24, 24 + gap_length))))
                self.assertEqual(decision(steps[23]).availability, "expert")
                for age in range(1, gap_length + 1):
                    d = decision(steps[23 + age])
                    self.assertEqual(d.last_genuine_age_ticks, age)
                    self.assertEqual(d.availability, "fallback" if age <= 3 else "abstained")
                    self.assertEqual(d.predicted_value, steps[23].tick.value if age <= 3 else None)
                recovery = 24 + gap_length
                self.assertEqual(decision(steps[recovery]).availability, "fallback")
                self.assertFalse(steps[recovery + 22].state.learned_eligible)
                self.assertTrue(steps[recovery + 23].state.learned_eligible)
                self.assertEqual(sum(s.reset is not None for s in steps), int(gap_length == 4))

    def test_trailing_gap_expiration_and_pending_boundary(self):
        simulator, steps = replay(rows(30, set(range(24, 30))))
        self.assertEqual([decision(s).availability for s in steps[24:]],
                         ["fallback"] * 3 + ["abstained"] * 3)
        self.assertTrue(all(not d.issued for s in steps[27:] for d in s.decisions))
        self.assertTrue(simulator.ledger.pending_ids)
        pending = set(simulator.ledger.pending_ids)
        self.assertTrue(all(f.target > steps[-1].tick.timestamp for f in simulator.ledger.forecasts if f.forecast_id in pending))

    def test_missing_exact_targets_h1_h12_never_shift_to_next_genuine(self):
        simulator, steps = replay(rows(42, {28}))
        for horizon, origin in ((1, 27), (12, 16)):
            forecast = decision(steps[origin], horizon=horizon)
            resolved = [o for o in simulator.ledger.outcomes if o.forecast_id == forecast.forecast_id]
            self.assertEqual(len(resolved), 1)
            outcome = resolved[0]
            self.assertEqual(outcome.status, "target_unavailable")
            self.assertEqual(outcome.target, steps[28].tick.timestamp)
            self.assertEqual(outcome.horizon, horizon)
            for field in ("actual", "signed_error", "absolute_error", "squared_error", "interval_hit"):
                self.assertIsNone(getattr(outcome, field))
            self.assertTrue(all(o.forecast_id != forecast.forecast_id for o in steps[29].outcomes))

    def test_h12_errors_wait_for_exact_genuine_arrival(self):
        _, steps = replay(rows(15, {5, 6, 7}))
        for step in steps[:12]:
            self.assertEqual(support(step, horizon=12).total_genuine_scored, 0)
            self.assertTrue(all(o.horizon != 12 for o in step.outcomes))
        first = [o for o in steps[12].outcomes if o.policy_id == "stub_last" and o.horizon == 12]
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].origin, START)
        self.assertEqual(first[0].target, steps[12].tick.timestamp)
        self.assertEqual(support(steps[12], horizon=12).total_genuine_scored, 1)

    def test_era_reset_once_per_long_gap_and_again_only_for_new_gap(self):
        missing = {*range(24, 33), *range(65, 70)}
        _, steps = replay(rows(100, missing))
        reset_indices = [i for i, s in enumerate(steps) if s.reset is not None]
        self.assertEqual(reset_indices, [27, 68])
        self.assertEqual((steps[27].reset.previous_era, steps[27].reset.new_era), (0, 1))
        self.assertEqual((steps[68].reset.previous_era, steps[68].reset.new_era), (1, 2))
        self.assertEqual(steps[33].state.era, 1)
        self.assertEqual(steps[69].state.era, 2)
        self.assertTrue(all(s.count == 0 for s in steps[27].state.support))

    def test_old_era_forecast_is_scored_but_cannot_seed_new_support(self):
        simulator, steps = replay(rows(44, set(range(24, 30))))
        forecast = decision(steps[23], horizon=12)
        outcome = next(o for o in steps[35].outcomes if o.forecast_id == forecast.forecast_id)
        self.assertEqual(outcome.status, "scored")
        self.assertEqual(outcome.forecast_era, 0)
        self.assertEqual(steps[35].state.era, 1)
        self.assertEqual(support(steps[35], horizon=12).count, 0)
        self.assertGreater(support(steps[35], horizon=12).total_genuine_scored, 0)
        self.assertEqual(support(steps[42], horizon=12).count, 1)
        self.assertIn(outcome, simulator.ledger.outcomes)

    def test_future_value_mask_and_length_changes_preserve_entire_prefix(self):
        original = rows(100, {28, 70, 71, 72, 73})
        changed = original[:60] + tuple((t, None if i % 2 else 99.0, "changed_gap" if i % 2 else None)
                                             for i, (t, _, _) in enumerate(original[60:]))
        _, a = replay(original)
        _, b = replay(changed)
        _, c = replay(original[:60])
        self.assertEqual(a[:60], b[:60])
        self.assertEqual(a[:60], c)
        self.assertNotEqual(a[60:], b[60:])

    def test_identical_causal_context_object_across_eligible_experts(self):
        calls = []
        original = StubExpertV2.predict

        def record(expert, context, horizon):
            calls.append((expert.policy_id, horizon, context))
            return original(expert, context, horizon)

        with patch.object(StubExpertV2, "predict", record):
            _, steps = replay(rows(30))
        for step in steps[23:]:
            contexts = [c for _, _, c in calls if c.origin == step.tick.timestamp]
            self.assertEqual(len(contexts), 4)
            self.assertTrue(all(c is contexts[0] for c in contexts))
            self.assertEqual(len(contexts[0].history), 24)
            self.assertTrue(all(t.timestamp <= step.tick.timestamp for t in contexts[0].history))
            self.assertEqual({d.context_sha256 for d in step.decisions}, {contexts[0].context_sha256})
            self.assertEqual(contexts[0].history[-1], step.tick)

    def test_event_order_is_reveal_outcomes_reset_state_then_issue(self):
        _, steps = replay(rows(50, set(range(24, 30))))
        all_sequences = []
        for step in steps:
            ordered = step.ordered()
            sequences = [record.sequence for _, record in ordered]
            self.assertEqual(sequences, sorted(sequences))
            self.assertEqual(ordered[0][0], "tick")
            self.assertTrue(all(o.issued_sequence < step.tick.sequence < o.sequence < step.state.sequence for o in step.outcomes))
            self.assertTrue(all(f.sequence > step.state.sequence for f in step.decisions))
            if step.reset:
                self.assertLess(step.tick.sequence, step.reset.sequence)
                self.assertLess(step.reset.sequence, step.state.sequence)
            all_sequences.extend(sequences)
        self.assertEqual(all_sequences, list(range(1, len(all_sequences) + 1)))

    def test_support_is_policy_specific_and_keeps_own_fallback_errors(self):
        _, steps = replay(rows(50))
        for horizon in (1, 12):
            a, b = support(steps[40], "persistence", horizon), support(steps[40], "stub_offset", horizon)
            self.assertEqual(a.count, b.count)
            self.assertEqual(a.count, 40 - horizon + 1)
        forecast = decision(steps[22], "stub_offset")
        self.assertEqual(forecast.availability, "fallback")
        outcome = next(o for o in steps[23].outcomes if o.forecast_id == forecast.forecast_id)
        self.assertEqual(outcome.policy_id, "stub_offset")
        self.assertEqual(support(steps[23], "stub_offset").count, 23)
        self.assertEqual(decision(steps[23], "stub_offset").availability, "expert")
        self.assertEqual(support(steps[24], "stub_offset").count, 24)

    def test_support_minimum_capacity_and_no_intervals_even_when_ready(self):
        _, steps = replay(rows(350))
        self.assertEqual(support(steps[99]).count, 99)
        self.assertFalse(support(steps[99]).ready)
        self.assertTrue(support(steps[100]).ready)
        for snapshot in steps[-1].state.support:
            self.assertEqual(snapshot.count, 288)
            self.assertEqual(snapshot.earliest_target, steps[-288].tick.timestamp)
            self.assertTrue(snapshot.ready)
        for record in steps[-1].decisions:
            self.assertEqual(record.interval_status, "not_implemented")
            self.assertIsNone(record.lower)
            self.assertIsNone(record.upper)

    def test_support_ages_by_elapsed_ticks_not_observed_sample_count(self):
        missing = {i for i in range(40, 350) if i % 4 != 0}
        simulator, steps = replay(rows(350, missing))
        self.assertTrue(all(s.reset is None for s in steps))
        oldest = steps[-1].tick.timestamp - timedelta(minutes=5 * 287)
        actual = support(steps[-1], "stub_last", 12)
        genuine_recent = [o for o in simulator.ledger.outcomes if o.policy_id == "stub_last" and o.horizon == 12
                          and o.status == "scored" and o.target >= oldest]
        self.assertEqual(actual.count, len(genuine_recent))
        self.assertLess(actual.count, 100)
        self.assertFalse(actual.ready)
        self.assertGreaterEqual(actual.earliest_target, oldest)
        self.assertGreater(actual.total_genuine_scored, actual.count)

    def test_unavailable_stub_uses_logged_fallback_without_dropping_targets(self):
        experts = (StubExpertV2(), StubExpertV2("offline_stub", mode="unavailable"))
        simulator, steps = replay(rows(35), experts)
        for step in steps[23:]:
            d = decision(step, "offline_stub")
            self.assertEqual(d.availability, "fallback")
            self.assertEqual(d.reason, "stub_unavailable")
            self.assertEqual(d.selected_expert, "persistence")
        self.assertEqual({o.target for o in simulator.ledger.outcomes if o.policy_id == "persistence"},
                         {o.target for o in simulator.ledger.outcomes if o.policy_id == "offline_stub"})


class V2ContractTests(unittest.TestCase):
    def test_invalid_ticks_reject_before_state_changes(self):
        simulator = StreamingSimulatorV2("test", "synthetic")
        simulator.advance(*rows(1)[0])
        before = (simulator._sequence, simulator._ticks, simulator.ledger.decisions)
        next_tick = START + timedelta(minutes=5)
        bad = [(next_tick, None, None), (next_tick, 40, "not_missing"),
               (next_tick, float("nan"), None), (next_tick, float("inf"), None),
               (next_tick, True, None), (next_tick, -1, None), (next_tick, 101, None),
               (next_tick.replace(tzinfo=None), 40, None),
               (next_tick.astimezone(timezone(timedelta(hours=1))), 40, None),
               (next_tick + timedelta(seconds=1), 40, None),
               (next_tick + timedelta(microseconds=1), 40, None),
               (START, 40, None), (next_tick + timedelta(minutes=5), 40, None)]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    simulator.advance(*args)
                self.assertEqual(before, (simulator._sequence, simulator._ticks, simulator.ledger.decisions))
        simulator.advance(next_tick, None, "quality_failed")

    def test_cutoffs_intervals_support_and_horizons_fail_closed(self):
        _, steps = replay(rows(25))
        record = decision(steps[24])
        future = record.origin + timedelta(minutes=5)
        for changes in ({"training_cutoff": future}, {"scaling_cutoff": future},
                        {"version_available_at": future}, {"horizon": True}, {"horizon": 2},
                        {"target": future + timedelta(minutes=5)}, {"support_latest_target": future},
                        {"support_count": 0}, {"support_ready": True}, {"interval_status": "available"},
                        {"lower": 0}, {"last_genuine_age_ticks": 1}, {"learned_eligible": False},
                        {"predicted_value": float("nan")}, {"selected_expert": "wrong"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    replace(record, **changes)
        with self.assertRaises(ValueError):
            replace(record, training_cutoff=record.origin, version_available_at=record.origin - timedelta(minutes=5))

    def test_forecasts_ticks_and_contexts_are_immutable(self):
        _, steps = replay(rows(25))
        for obj, field, value in ((decision(steps[-1]), "predicted_value", 99),
                                  (steps[-1].tick, "value", 99), (steps[-1].state, "era", 5)):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)

    def test_duplicate_revised_unknown_and_wrong_target_outcomes_rejected(self):
        simulator, steps = replay(rows(25))
        record = decision(steps[0], "persistence", 12)
        with self.assertRaises(ValueError):
            simulator.ledger.resolve(record, steps[12].tick, simulator._sequence + 1)
        unresolved = decision(steps[-1], "persistence", 12)
        with self.assertRaises(ValueError):
            simulator.ledger.resolve(replace(unresolved, predicted_value=99), steps[-1].tick, simulator._sequence + 1)
        with self.assertRaises(ValueError):
            resolve_target_v2(unresolved, steps[-1].tick, simulator._sequence + 1)
        with self.assertRaises(ValueError):
            resolve_target_v2(replace(unresolved, availability="abstained", predicted_value=None,
                                      selected_expert=None, source_version=None), steps[-1].tick, simulator._sequence + 1)

    def test_ledger_rejects_duplicate_decisions_and_tampered_context(self):
        simulator, steps = replay(rows(25))
        current = steps[-1]
        context = simulator._context(current.tick)
        record = decision(current)
        with self.assertRaises(ValueError):
            simulator.ledger.issue(record, current.tick, context)
        duplicate_key = replace(record, forecast_id="different_id", sequence=simulator._sequence + 1)
        with self.assertRaises(ValueError):
            simulator.ledger.issue(duplicate_key, current.tick, context)
        new_record = replace(record, forecast_id="new", policy_id="new_policy", selected_expert="new_policy",
                             sequence=simulator._sequence + 1)
        with self.assertRaises(ValueError):
            simulator.ledger.issue(new_record, current.tick, replace(context, era=99))

    def test_missing_outcome_cannot_invent_error_or_coverage(self):
        _, steps = replay(rows(30, {28}))
        outcome = steps[28].outcomes[0]
        for changes in ({"absolute_error": 0}, {"actual": 0}, {"interval_hit": False},
                        {"arrival_sequence": outcome.issued_sequence}, {"horizon": 2}):
            with self.assertRaises(ValueError):
                replace(outcome, **changes)

    def test_protocol_and_stub_bank_reject_unsupported_features(self):
        for changes in ({"option_c_enabled": True}, {"m3_training_allowed": True},
                        {"confirmation_execution_allowed": True}, {"parameters_fixed": False},
                        {"support_min_scores": 99}, {"cadence_seconds": True}, {"horizons": (True, 12)}):
            with self.assertRaises(ValueError):
                PilotProtocolV2(**changes)
        for experts in ((), (StubExpertV2("stub"),), (StubExpertV2(), StubExpertV2()), [StubExpertV2()], (object(),)):
            with self.assertRaises(ValueError):
                StreamingSimulatorV2("test", "synthetic", experts=experts)
        with self.assertRaises(ValueError):
            StubExpertV2(mode="trained_model")
        with self.assertRaises(ValueError):
            StubExpertV2("bad", offset_per_step=float("nan"))

    def test_finalized_config_loads_and_rejects_enabling_flags_or_engine_changes(self):
        path = ROOT / "configs/dafr_engineering_pilot_v2.json"
        self.assertEqual(load_pilot_protocol_v2(path), PilotProtocolV2())
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "protocol.json"
            for change in ("confirmation_execution_allowed", "m3_training_allowed", "unknown_engine", "draft", "horizon"):
                data = json.loads(path.read_text())
                if change in ("confirmation_execution_allowed", "m3_training_allowed"):
                    data[change] = True
                elif change == "unknown_engine":
                    data["engine"]["new_feature"] = True
                elif change == "horizon":
                    data["engine"]["horizons"] = [1, 2]
                else:
                    data["status"] = "DRAFT"
                target.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load_pilot_protocol_v2(target)


class V2ArtifactTests(unittest.TestCase):
    def test_saved_ledgers_conserve_all_decisions_and_target_outcomes(self):
        with TemporaryDirectory() as tmp:
            output = run_stream_v2(synthetic_missing_series_v2(), run_id="demo", dataset_id="synthetic",
                                   experts=EXPERTS, project_root=Path(tmp))
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["grid_ticks"], 180)
            self.assertEqual(summary["missing_ticks"], 16)
            self.assertEqual(summary["genuine_ticks"], 164)
            self.assertEqual(summary["telemetry_resets"], 2)
            self.assertEqual(summary["decisions"], 180 * 6)
            self.assertEqual(summary["decisions"], summary["issued_forecasts"] + summary["abstentions"])
            self.assertEqual(summary["issued_forecasts"], summary["scored_targets"] + summary["unavailable_targets"] + summary["boundary_pending"])
            forecasts, outcomes = jsonl(output / "forecasts.jsonl"), jsonl(output / "outcomes.jsonl")
            issued = {f["forecast_id"]: f for f in forecasts}
            for outcome in outcomes:
                original = issued[outcome["forecast_id"]]
                self.assertEqual(outcome["target"], original["target"])
                self.assertEqual(outcome["predicted_value"], original["predicted_value"])
                self.assertLess(original["sequence"], outcome["arrival_sequence"])
            events = jsonl(output / "events.jsonl")
            self.assertEqual([e["record"]["sequence"] for e in events], list(range(1, len(events) + 1)))
            self.assertEqual(json.loads((output / "completion.json").read_text())["status"], "completed")
            self.assertEqual(json.loads((output / "manifest.json").read_text())["input_scope"], "synthetic_only")

    def test_existing_run_refused_and_files_unchanged(self):
        with TemporaryDirectory() as tmp:
            args = dict(run_id="same_run", dataset_id="synthetic", project_root=Path(tmp))
            directory = run_stream_v2(rows(5), **args)
            hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
            with self.assertRaises(FileExistsError):
                run_stream_v2(rows(10), **args)
            self.assertEqual(hashes, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()})

    def test_empty_or_skipped_tick_stream_reserves_failed_run(self):
        with TemporaryDirectory() as tmp:
            for name, samples in (("empty", ()), ("skipped", (rows(3)[0], rows(3)[2]))):
                with self.assertRaises(ValueError):
                    run_stream_v2(samples, run_id=name, dataset_id="synthetic", project_root=Path(tmp))
                output = Path(tmp) / "data/processed/dafr/missing_data_v2" / name
                self.assertEqual(json.loads((output / "completion.json").read_text())["status"], "failed")
                with self.assertRaises(FileExistsError):
                    run_stream_v2(rows(1), run_id=name, dataset_id="synthetic", project_root=Path(tmp))

    def test_all_missing_run_serializes_nulls_and_zero_predictions(self):
        with TemporaryDirectory() as tmp:
            output = run_stream_v2(rows(6, set(range(6))), run_id="all_missing", dataset_id="synthetic", project_root=Path(tmp))
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["issued_forecasts"], 0)
            self.assertEqual(summary["abstentions"], 12)
            self.assertEqual(jsonl(output / "outcomes.jsonl"), [])
            self.assertTrue(all(d["predicted_value"] is None for d in jsonl(output / "abstentions.jsonl")))

    def test_run_traversal_and_output_symlinks_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                run_stream_v2(rows(1), run_id="../escape", dataset_id="synthetic", project_root=root)
            outside = root / "outside"
            outside.mkdir()
            (root / "data").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                run_stream_v2(rows(1), run_id="redirected", dataset_id="synthetic", project_root=root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_all_69_m1_m2_m2b_m2c_baseline_hashes_preserved(self):
        receipt = json.loads((ROOT / "reports/dafr/m2d_preservation_v1.json").read_text())
        self.assertEqual(receipt["file_count"], 69)
        for relative, expected in receipt["protected_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        with TemporaryDirectory() as tmp:
            run_stream_v2(rows(6, {3}), run_id="preserve", dataset_id="synthetic", project_root=Path(tmp))
        for relative, expected in receipt["protected_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)


if __name__ == "__main__":
    unittest.main()
