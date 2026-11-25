"""Gap-aware M2D pilot, standard library only; V1 is untouched.

Synthetic demonstration (from the project root):
    PYTHONPATH=src .venv/bin/python -m dafr.streaming_v2 --demo --run-id UNIQUE_ID

Each tick reveals a genuine CPU value or explicit missing event. Exact-target
resolution precedes support updates and future issuance. Only fixed stubs run.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .contracts import finite_number, identifier
from .contracts_v2 import (
    CausalContextV2, ForecastRecordV2, StateEventV2, StepEventsV2,
    SupportSnapshotV2, TargetOutcomeV2, TelemetryResetV2, TickEventV2,
    resolve_target_v2,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class PilotProtocolV2:
    """Only this frozen engineering protocol is supported; research stays off."""

    protocol_id: str = "dafr_engineering_pilot_v2"
    cadence_seconds: int = 300
    horizons: tuple[int, ...] = (1, 12)
    genuine_history_slots: int = 24
    fallback_max_age_ticks: int = 3
    era_reset_missing_tick: int = 4
    support_max_scores: int = 288
    support_min_scores: int = 100
    support_recency_ticks: int = 288
    max_grid_ticks: int = 2304
    max_policies: int = 8
    option: str = "B"
    option_c_enabled: bool = False
    confirmation_execution_allowed: bool = False
    m3_training_allowed: bool = False
    parameters_fixed: bool = True
    drift: str = "disabled_m2d"
    selection: str = "fixed_policy_no_switching"
    intervals: str = "not_implemented"
    data_scope: str = "synthetic_only"

    def __post_init__(self) -> None:
        # Fixed settings fail closed, including bool/int coercion and new features.
        for name, field in self.__dataclass_fields__.items():
            actual, expected = getattr(self, name), field.default
            if type(actual) is not type(expected) or actual != expected:
                raise ValueError(f"Unsupported frozen M2D setting: {name}")
        if any(type(h) is not int for h in self.horizons):
            raise ValueError("Horizons must be integer grid ticks.")


def load_pilot_protocol_v2(path: Path) -> PilotProtocolV2:
    values = json.loads(Path(path).read_text())
    if not isinstance(values, dict) or values.get("schema_version") != "dafr_engineering_pilot_v2":
        raise ValueError("Expected the finalized M2D engineering-pilot configuration.")
    if values.get("status") != "FROZEN_ENGINEERING_PILOT_NOT_RESEARCH_APPROVAL":
        raise ValueError("Draft or research-enabled configurations cannot execute M2D.")
    if values.get("confirmation_execution_allowed") is not False or values.get("m3_training_allowed") is not False:
        raise ValueError("Confirmation and M3 must remain disabled.")
    engine = values.get("engine")
    if not isinstance(engine, dict) or set(engine) != set(PilotProtocolV2.__dataclass_fields__):
        raise ValueError("Engine settings must be complete, without unknown fields.")
    engine = dict(engine)
    if not isinstance(engine["horizons"], list):
        raise ValueError("Horizons must be a JSON array.")
    engine["horizons"] = tuple(engine["horizons"])
    return PilotProtocolV2(**engine)


@dataclass(frozen=True, slots=True)
class StubExpertV2:
    """A fixed policy, not a learned forecast model or adaptive selector."""

    policy_id: str = "persistence"
    version: str = "rule_v2"
    mode: str = "last"
    offset_per_step: float = 0.0

    def __post_init__(self) -> None:
        identifier(self.policy_id)
        identifier(self.version)
        finite_number(self.offset_per_step)
        if abs(self.offset_per_step) > 100 or self.mode not in ("last", "offset", "unavailable"):
            raise ValueError("Only bounded deterministic stub modes are permitted.")
        if self.policy_id == "persistence" and (
            self.version != "rule_v2" or self.mode != "last" or self.offset_per_step != 0
        ):
            raise ValueError("Persistence is the unmodified required baseline.")

    def predict(self, context: CausalContextV2, horizon: int) -> float | None:
        if not context.learned_eligible:
            raise ValueError("Learned-style stubs require the shared 24-genuine-bin gate.")
        if type(horizon) is not int or horizon not in (1, 12):
            raise ValueError("Unknown horizon.")
        if self.mode == "unavailable":
            return None
        value = context.history[-1].value
        return value + horizon * self.offset_per_step if self.mode == "offset" else value


class ForecastLedgerV2:
    """Write-once decisions and outcomes, keyed by exact timestamps/horizons."""

    def __init__(self) -> None:
        self._decisions: dict[str, ForecastRecordV2] = {}
        self._keys: set[tuple] = set()
        self._pending: dict[datetime, list[str]] = defaultdict(list)
        self._outcomes: dict[str, TargetOutcomeV2] = {}
        self._last_sequence = 0

    @property
    def decisions(self) -> tuple[ForecastRecordV2, ...]:
        return tuple(self._decisions.values())

    @property
    def forecasts(self) -> tuple[ForecastRecordV2, ...]:
        return tuple(f for f in self._decisions.values() if f.issued)

    @property
    def outcomes(self) -> tuple[TargetOutcomeV2, ...]:
        return tuple(self._outcomes.values())

    @property
    def pending_ids(self) -> tuple[str, ...]:
        return tuple(f.forecast_id for f in self._decisions.values()
                     if f.issued and f.forecast_id not in self._outcomes)

    def pending_at(self, timestamp: datetime) -> tuple[ForecastRecordV2, ...]:
        return tuple(self._decisions[key] for key in self._pending.get(timestamp, ()))

    def issue(self, forecast: ForecastRecordV2, tick: TickEventV2, context: CausalContextV2) -> None:
        if type(forecast) is not ForecastRecordV2:
            raise ValueError("Expected a validated V2 decision.")
        if forecast.forecast_id in self._decisions or forecast.key in self._keys:
            raise ValueError("Duplicate decision ID or semantic policy/origin/horizon key.")
        if forecast.sequence <= self._last_sequence:
            raise ValueError("Ledger event sequences must strictly increase.")
        if (forecast.run_id, forecast.dataset_id, forecast.machine_id, forecast.origin,
            forecast.origin_tick_id, forecast.origin_tick_sequence) != (
            tick.run_id, tick.dataset_id, tick.machine_id, tick.timestamp, tick.event_id, tick.sequence
        ):
            raise ValueError("Decision does not match its revealed origin.")
        if (context.history[-1] != tick or context.origin != forecast.origin
            or context.era != forecast.era or context.context_sha256 != forecast.context_sha256
            or context.learned_eligible != forecast.learned_eligible
            or context.last_genuine_cutoff != forecast.last_genuine_cutoff
            or context.last_genuine_age_ticks != forecast.last_genuine_age_ticks):
            raise ValueError("Decision context/provenance mismatch.")
        self._decisions[forecast.forecast_id] = forecast
        self._keys.add(forecast.key)
        if forecast.issued:
            self._pending[forecast.target].append(forecast.forecast_id)
        self._last_sequence = forecast.sequence

    def resolve(self, forecast: ForecastRecordV2, tick: TickEventV2, sequence: int) -> TargetOutcomeV2:
        if self._decisions.get(forecast.forecast_id) != forecast or forecast.forecast_id in self._outcomes:
            raise ValueError("Unknown, revised or already resolved forecast.")
        if sequence <= self._last_sequence:
            raise ValueError("Ledger event sequences must strictly increase.")
        outcome = resolve_target_v2(forecast, tick, sequence)
        self._outcomes[forecast.forecast_id] = outcome
        pending = self._pending[forecast.target]
        pending.remove(forecast.forecast_id)
        if not pending:
            del self._pending[forecast.target]
        self._last_sequence = sequence
        return outcome


class StreamingSimulatorV2:
    """Reveal one explicit grid event per advance; never inspect future input.

    Working histories/support/pending targets are bounded. The small pilot's
    immutable audit ledger is retained in memory, with a 2,304-tick safety cap.
    Future production adapters need a disk-backed ledger, not a larger cap.
    """

    def __init__(self, run_id: str, dataset_id: str, machine_id: str = "synthetic_machine",
                 experts: tuple[StubExpertV2, ...] = (StubExpertV2(),),
                 protocol: PilotProtocolV2 = PilotProtocolV2()):
        for value in (run_id, dataset_id, machine_id):
            identifier(value)
        if type(protocol) is not PilotProtocolV2:
            raise ValueError("Expected a frozen V2 engineering-pilot protocol.")
        if not isinstance(experts, tuple) or not 1 <= len(experts) <= protocol.max_policies or any(type(e) is not StubExpertV2 for e in experts):
            raise ValueError("M2D accepts only an immutable tuple of deterministic stub policies.")
        if len({e.policy_id for e in experts}) != len(experts) or not any(e.policy_id == "persistence" for e in experts):
            raise ValueError("Distinct policy IDs and a persistence baseline are required.")
        self.run_id, self.dataset_id, self.machine_id = run_id, dataset_id, machine_id
        self.experts, self.protocol = experts, protocol
        self.ledger = ForecastLedgerV2()
        self._history: deque[TickEventV2] = deque(maxlen=24)
        self._last_genuine: TickEventV2 | None = None
        self._sequence = self._ticks = self._genuine = self._era = 0
        self._genuine_streak = self._missing_streak = 0
        self._support = {(e.policy_id, e.version, h): deque(maxlen=288)
                         for e in experts for h in protocol.horizons}
        self._total_scored = Counter()

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _context(self, tick: TickEventV2) -> CausalContextV2:
        cutoff = self._last_genuine.timestamp if self._last_genuine else None
        age = int((tick.timestamp - cutoff).total_seconds() // 300) if cutoff is not None else None
        payload = [self._era, self._genuine_streak, self._missing_streak,
                   cutoff.isoformat() if cutoff else None,
                   [[t.timestamp.isoformat(), t.value, t.missing_reason] for t in self._history]]
        digest = hashlib.sha256(json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
        return CausalContextV2(tick.timestamp, tuple(self._history), self._era,
                               self._genuine_streak, self._missing_streak, cutoff, age, digest)

    def advance(self, timestamp: datetime, value: float | None,
                missing_reason: str | None = None) -> StepEventsV2:
        # All external input validation precedes any state mutation.
        tick = TickEventV2(self.run_id, self.dataset_id, self.machine_id,
                           f"tick-{self._ticks + 1}", self._sequence + 1, timestamp, value, missing_reason)
        if self._ticks >= self.protocol.max_grid_ticks:
            raise ValueError("Engineering pilot exceeded its 2,304-tick memory guard.")
        if self._history and timestamp - self._history[-1].timestamp != timedelta(minutes=5):
            raise ValueError("Supply exactly one genuine or explicit missing event per grid tick.")
        self._next_sequence()
        self._ticks += 1
        self._history.append(tick)
        if tick.genuine:
            self._last_genuine = tick
            self._genuine += 1
            self._genuine_streak += 1
            self._missing_streak = 0
        else:
            self._genuine_streak = 0
            self._missing_streak += 1

        # Exact-target feedback is resolved before any state/era update.
        outcomes = tuple(self.ledger.resolve(f, tick, self._next_sequence())
                         for f in self.ledger.pending_at(timestamp))
        reset = None
        if self._missing_streak == 4:
            previous = self._era
            self._era += 1
            reset = TelemetryResetV2(f"reset-{self._era}", self._next_sequence(),
                                      timestamp, tick.event_id, previous, self._era)
            for buffer in self._support.values():
                buffer.clear()

        for outcome in outcomes:
            if outcome.status == "scored":
                key = (outcome.policy_id, outcome.policy_version, outcome.horizon)
                self._total_scored[key] += 1
                # An old-era forecast remains in evaluation, never seeds new support.
                if outcome.forecast_era == self._era:
                    self._support[key].append(outcome)
        oldest = timestamp - timedelta(minutes=5 * (self.protocol.support_recency_ticks - 1))
        for buffer in self._support.values():
            while buffer and buffer[0].target < oldest:
                buffer.popleft()
        snapshots = tuple(SupportSnapshotV2(
            key[0], key[1], key[2], self._era, len(buffer),
            buffer[-1].target if buffer else None, buffer[0].target if buffer else None,
            len(buffer) >= 100, self._total_scored[key],
        ) for key, buffer in self._support.items())
        context = self._context(tick)
        state = StateEventV2(f"state-{self._ticks}", self._next_sequence(), timestamp,
                             tick.event_id, self._ticks, self._genuine, self._era,
                             self._genuine_streak, self._missing_streak, context.learned_eligible,
                             context.last_genuine_age_ticks, context.context_sha256, snapshots)

        decisions = []
        for expert in self.experts:
            for horizon in self.protocol.horizons:
                prediction = None
                source = version = None
                if expert.policy_id == "persistence":
                    reason = "persistence_reference"
                elif not context.learned_eligible:
                    reason = "history_gate"
                else:
                    prediction = expert.predict(context, horizon)
                    reason = "stub_unavailable" if prediction is None else "fixed_stub"
                    if prediction is not None:
                        finite_number(prediction)
                        source, version = expert.policy_id, expert.version
                if prediction is not None:
                    availability = "expert"
                elif self._last_genuine is not None and context.last_genuine_age_ticks <= 3:
                    prediction = self._last_genuine.value
                    source, version = "persistence", "rule_v2"
                    availability = "baseline" if expert.policy_id == "persistence" else "fallback"
                else:
                    availability = "abstained"
                    reason = "no_genuine_history" if self._last_genuine is None else "fallback_stale"
                buffer = self._support[(expert.policy_id, expert.version, horizon)]
                sequence = self._next_sequence()
                record = ForecastRecordV2(
                    forecast_id=f"decision-{sequence}", run_id=self.run_id, dataset_id=self.dataset_id,
                    machine_id=self.machine_id, policy_id=expert.policy_id, policy_version=expert.version,
                    origin=timestamp, target=timestamp + timedelta(minutes=5 * horizon), horizon=horizon,
                    sequence=sequence, origin_tick_id=tick.event_id, origin_tick_sequence=tick.sequence,
                    era=self._era, context_sha256=context.context_sha256, learned_eligible=context.learned_eligible,
                    availability=availability, selected_expert=source, source_version=version,
                    predicted_value=prediction, reason=reason, last_genuine_cutoff=context.last_genuine_cutoff,
                    last_genuine_age_ticks=context.last_genuine_age_ticks,
                    support_count=len(buffer), support_latest_target=buffer[-1].target if buffer else None,
                    support_ready=len(buffer) >= 100,
                )
                self.ledger.issue(record, tick, context)
                decisions.append(record)
        return StepEventsV2(tick, outcomes, reset, state, tuple(decisions))


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(handle, value) -> None:
    handle.write(json.dumps(value, default=_json_default, sort_keys=True, allow_nan=False) + "\n")


def run_stream_v2(events: Iterable[tuple[datetime, float | None, str | None]], *,
                  run_id: str, dataset_id: str, machine_id: str = "synthetic_machine",
                  experts: tuple[StubExpertV2, ...] = (StubExpertV2(),),
                  protocol: PilotProtocolV2 = PilotProtocolV2(),
                  project_root: Path = PROJECT_ROOT) -> Path:
    """Reserve a new V2 run exclusively; all files use exclusive creation.

    A failed attempt retains a failure receipt and its reserved ID. No external
    dataset loader exists here, and confirmation use remains unauthorized.
    """
    simulator = StreamingSimulatorV2(run_id, dataset_id, machine_id, experts, protocol)
    root = Path(project_root).resolve()
    base = root / "data" / "processed" / "dafr" / "missing_data_v2"
    if base.resolve() != base:
        raise ValueError("V2 output ancestors must not be redirected by symlinks.")
    base.mkdir(parents=True, exist_ok=True)
    directory = base / run_id
    directory.mkdir(exist_ok=False)
    manifest = {"run_id": run_id, "dataset_id": dataset_id, "machine_id": machine_id,
                "milestone": "M2D", "protocol": asdict(protocol),
                "protocol_engine_sha256": hashlib.sha256(json.dumps(asdict(protocol), sort_keys=True).encode()).hexdigest(),
                "experts": [asdict(e) for e in experts], "status": "reserved",
                "training_performed": False, "confirmation_execution_allowed": False,
                "m3_training_allowed": False, "input_scope": "synthetic_only",
                "status_receipt": "completion.json"}
    with (directory / "manifest.json").open("x") as handle:
        _write_json(handle, manifest)
    digest = hashlib.sha256()
    counts = Counter()
    per_policy = defaultdict(Counter)
    completion = {"status": "failed"}
    try:
        with ExitStack() as stack:
            outputs = {name: stack.enter_context((directory / f"{name}.jsonl").open("x"))
                       for name in ("ticks", "forecasts", "abstentions", "outcomes", "states", "resets", "events")}
            for timestamp, value, reason in events:
                step = simulator.advance(timestamp, value, reason)
                raw = [timestamp.isoformat(), float(value) if value is not None else None, reason]
                digest.update((json.dumps(raw, allow_nan=False) + "\n").encode())
                counts["grid_ticks"] += 1
                counts["genuine_ticks" if step.tick.genuine else "missing_ticks"] += 1
                counts["learned_eligible_origins"] += step.state.learned_eligible
                counts["telemetry_resets"] += step.reset is not None
                for decision in step.decisions:
                    key = (decision.policy_id, decision.horizon)
                    per_policy[key][decision.availability] += 1
                for outcome in step.outcomes:
                    per_policy[(outcome.policy_id, outcome.horizon)][outcome.status] += 1
                for kind, event in step.ordered():
                    output = {"tick": "ticks", "forecast": "forecasts", "abstention": "abstentions",
                              "scored": "outcomes", "target_unavailable": "outcomes",
                              "state": "states", "telemetry_reset": "resets"}[kind]
                    data = asdict(event)
                    _write_json(outputs[output], data)
                    _write_json(outputs["events"], {"kind": kind, "record": data})
            if not counts["grid_ticks"]:
                raise ValueError("The stream cannot be empty.")
        pending_ids = set(simulator.ledger.pending_ids)
        for forecast in simulator.ledger.forecasts:
            if forecast.forecast_id in pending_ids:
                per_policy[(forecast.policy_id, forecast.horizon)]["boundary_pending"] += 1
        summary = {**{name: counts[name] for name in ("grid_ticks", "genuine_ticks", "missing_ticks",
                   "learned_eligible_origins", "telemetry_resets")},
                   "decisions": len(simulator.ledger.decisions), "issued_forecasts": len(simulator.ledger.forecasts),
                   "abstentions": sum(not d.issued for d in simulator.ledger.decisions),
                   "scored_targets": sum(o.status == "scored" for o in simulator.ledger.outcomes),
                   "unavailable_targets": sum(o.status == "target_unavailable" for o in simulator.ledger.outcomes),
                   "boundary_pending": len(simulator.ledger.pending_ids),
                   "per_policy_horizon": [{"policy_id": p, "horizon": h, **dict(c)}
                                          for (p, h), c in sorted(per_policy.items())],
                   "final_support": [asdict(s) for s in step.state.support],
                   "note": "Synthetic engineering demonstration only; no learned-model performance or interval coverage claim."}
        with (directory / "summary.json").open("x") as handle:
            _write_json(handle, summary)
        completion = {"status": "completed", "input_sha256": digest.hexdigest(), "grid_ticks": counts["grid_ticks"]}
    except Exception as error:
        completion.update(error_type=type(error).__name__, error=str(error), grid_ticks=counts["grid_ticks"])
        raise
    finally:
        with (directory / "completion.json").open("x") as handle:
            _write_json(handle, completion)
    return directory


def synthetic_missing_series_v2() -> tuple[tuple[datetime, float | None, str | None], ...]:
    """180 synthetic slots: leading, 1-/3-/6-tick gaps, then trailing 4-tick gap."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    missing = {0, 1, 28, 56, 57, 58, *range(88, 94), *range(176, 180)}
    return tuple((start + timedelta(minutes=5 * i), None if i in missing else 40.0 + i % 9,
                  "synthetic_gap" if i in missing else None) for i in range(180))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    protocol = load_pilot_protocol_v2(PROJECT_ROOT / "configs" / "dafr_engineering_pilot_v2.json")
    result = run_stream_v2(
        synthetic_missing_series_v2(), run_id=args.run_id, dataset_id="synthetic_m2d_gaps",
        experts=(StubExpertV2(), StubExpertV2("stub_last"),
                 StubExpertV2("stub_offset", mode="offset", offset_per_step=0.25)), protocol=protocol)
    print(f"Saved synthetic V2 demonstration: {result}")
    print((result / "summary.json").read_text())


if __name__ == "__main__":
    main()
