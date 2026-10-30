"""Deterministic, standard-library-only DAF-R M1 streaming simulator.

Run the synthetic demonstration from the project root:
    PYTHONPATH=src .venv/bin/python -m dafr.streaming --demo --run-id m1-demo-001

Each advance reveals one observation, scores pending targets, updates bounded
error histories, then issues forecasts. No model fitting, switching, detector,
or interval calibrator is implemented here. Records at the stream tail remain
pending; they are never given fabricated actuals.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Iterable

from .contracts import (
    ForecastRecord, ObservationEvent, Provenance, ScoreEvent, finite_number,
    identifier, positive_integer, score_forecast, validate_lags,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Protocol:
    protocol_version: str = "v1"
    milestone: str = "M1"
    cadence_seconds: int = 300
    horizons: tuple[int, ...] = (1, 12)
    history_limit: int = 24
    error_history_limit: int = 288
    warmup_observations: int = 12
    lags: tuple[int, ...] = (1,)
    invalid_observation_policy: str = "reject_stream"
    unavailable_expert_policy: str = "persistence_fallback"
    tail_policy: str = "retain_unscored"
    selection_policy: str = "fixed_expert_m1"
    detector: str = "disabled_m1"
    calibration: str = "disabled_m1"
    research_partition_fractions: tuple[float, ...] = (0.5, 0.2, 0.1, 0.2)
    partition_note: str = "Reference fractions only; M1 performs no fitting."

    def __post_init__(self) -> None:
        # Unsupported settings fail loudly instead of pretending to execute a
        # future milestone's detector, adaptive selector or calibrator.
        required = {
            "protocol_version": "v1", "milestone": "M1", "cadence_seconds": 300,
            "horizons": (1, 12), "lags": (1,), "invalid_observation_policy": "reject_stream",
            "unavailable_expert_policy": "persistence_fallback", "tail_policy": "retain_unscored",
            "selection_policy": "fixed_expert_m1", "detector": "disabled_m1", "calibration": "disabled_m1",
        }
        validate_lags(self.lags)
        for name, expected in required.items():
            if getattr(self, name) != expected:
                raise ValueError(f"Unsupported M1 setting: {name}")
        if type(self.cadence_seconds) is not int or any(type(h) is not int for h in self.horizons):
            raise ValueError("Cadence/horizons must be integers.")
        for value in (self.history_limit, self.error_history_limit):
            positive_integer(value)
        if type(self.warmup_observations) is not int or self.warmup_observations < 0:
            raise ValueError("Warm-up count must be a nonnegative integer.")
        if self.research_partition_fractions != (0.5, 0.2, 0.1, 0.2):
            raise ValueError("Research reference fractions must match the design.")


def load_protocol(path: Path) -> Protocol:
    """Read the checked-in configuration; reject unknown or unsupported fields."""
    with Path(path).open() as source:
        values = json.load(source)
    if not isinstance(values, dict):
        raise ValueError("Protocol JSON must be an object.")
    for name in ("horizons", "lags", "research_partition_fractions"):
        if name in values:
            if not isinstance(values[name], list):
                raise ValueError(f"{name} must be a JSON array.")
            values[name] = tuple(values[name])
    try:
        return Protocol(**values)
    except TypeError as error:
        raise ValueError("Unexpected protocol fields.") from error


@dataclass(frozen=True, slots=True)
class StubExpert:
    """Fixed deterministic rule; never receives unrevealed data or fits data."""
    expert_id: str = "persistence"
    version: str = "rule_v1"
    mode: str = "persistence"
    offset_per_step: float = 0.0

    def __post_init__(self) -> None:
        identifier(self.expert_id)
        identifier(self.version)
        finite_number(self.offset_per_step)
        if self.mode not in ("persistence", "offset", "unavailable"):
            raise ValueError("Only deterministic M1 stub modes are supported.")
        if self.expert_id == "persistence" and (self.mode != "persistence" or self.offset_per_step != 0):
            raise ValueError("The persistence identifier is reserved for the true baseline.")

    def predict(self, history: tuple[ObservationEvent, ...], horizon: int) -> float | None:
        if self.mode == "unavailable":
            return None
        value = history[-1].value
        if self.mode == "offset":
            value += horizon * self.offset_per_step
        finite_number(value)
        return value


class ForecastLedger:
    """Write-once forecast storage with an explicit pending-target index."""

    def __init__(self) -> None:
        self._forecasts: dict[str, ForecastRecord] = {}
        self._keys: set[tuple] = set()
        self._pending: dict[datetime, list[str]] = defaultdict(list)
        self._scores: dict[str, ScoreEvent] = {}
        self._last_sequence = 0

    @property
    def forecasts(self) -> tuple[ForecastRecord, ...]:
        return tuple(self._forecasts.values())

    @property
    def scores(self) -> tuple[ScoreEvent, ...]:
        return tuple(self._scores.values())

    @property
    def unscored(self) -> tuple[str, ...]:
        return tuple(f.forecast_id for f in self._forecasts.values() if f.forecast_id not in self._scores)

    def issue(self, forecast: ForecastRecord, observation: ObservationEvent) -> None:
        if not isinstance(forecast, ForecastRecord):
            raise ValueError("Expected a validated forecast record.")
        if forecast.forecast_id in self._forecasts or forecast.key in self._keys:
            raise ValueError("Duplicate forecast ID or semantic forecast key.")
        if forecast.issued_sequence <= self._last_sequence:
            raise ValueError("Ledger events must have strictly increasing sequence numbers.")
        if (forecast.run_id, forecast.dataset_id, forecast.machine_id, forecast.origin,
            forecast.origin_observation_id, forecast.origin_observation_sequence) != (
            observation.run_id, observation.dataset_id, observation.machine_id, observation.timestamp,
            observation.event_id, observation.sequence
        ):
            raise ValueError("Forecast provenance does not match its revealed origin.")
        self._forecasts[forecast.forecast_id] = forecast
        self._keys.add(forecast.key)
        self._pending[forecast.target].append(forecast.forecast_id)
        self._last_sequence = forecast.issued_sequence

    def pending_at(self, timestamp: datetime) -> tuple[ForecastRecord, ...]:
        return tuple(self._forecasts[key] for key in self._pending.get(timestamp, ()))

    def score(self, forecast: ForecastRecord, observation: ObservationEvent, sequence: int) -> ScoreEvent:
        if self._forecasts.get(forecast.forecast_id) != forecast:
            raise ValueError("Cannot score an unknown or altered forecast.")
        if forecast.forecast_id in self._scores:
            raise ValueError("A forecast cannot be scored twice.")
        if sequence <= self._last_sequence:
            raise ValueError("Ledger events must have strictly increasing sequence numbers.")
        score = score_forecast(forecast, observation, sequence)
        self._scores[forecast.forecast_id] = score
        pending = self._pending[forecast.target]
        pending.remove(forecast.forecast_id)
        if not pending:
            del self._pending[forecast.target]
        self._last_sequence = score.sequence
        return score


@dataclass(frozen=True, slots=True)
class ErrorSnapshot:
    expert_id: str
    horizon: int
    total_matured: int
    buffered_count: int
    latest_target: datetime | None
    mean_absolute_error: float | None


@dataclass(frozen=True, slots=True)
class StateEvent:
    event_id: str
    sequence: int
    timestamp: datetime
    observation_id: str
    observation_count: int
    error_histories: tuple[ErrorSnapshot, ...]
    detector_state: str = "disabled_m1"
    selection_policy: str = "fixed_expert_m1"
    calibration_state: str = "disabled_m1"


@dataclass(frozen=True, slots=True)
class StepEvents:
    observation: ObservationEvent
    scores: tuple[ScoreEvent, ...]
    state: StateEvent
    forecasts: tuple[ForecastRecord, ...]


class StreamingSimulator:
    """Single-run causal engine. Call advance with one newly arrived sample.

    Recent observation/error buffers are bounded. The audit ledger is retained
    in memory for this small-data M1 prototype; future large traces may stream
    it to disk instead. Expert code receives only the revealed trailing prefix.
    """

    def __init__(self, run_id: str, dataset_id: str, machine_id: str,
                 experts: tuple[StubExpert, ...] = (StubExpert(),), protocol: Protocol = Protocol()):
        for value in (run_id, dataset_id, machine_id):
            identifier(value)
        if not isinstance(protocol, Protocol):
            raise ValueError("Expected a validated M1 protocol.")
        if not isinstance(experts, tuple) or not experts or any(type(e) is not StubExpert for e in experts):
            raise ValueError("M1 accepts only a nonempty immutable tuple of deterministic stubs.")
        if len({e.expert_id for e in experts}) != len(experts):
            raise ValueError("Duplicate expert identifiers.")
        if not any(e.expert_id == "persistence" for e in experts):
            raise ValueError("The persistence baseline is required.")
        self.run_id, self.dataset_id, self.machine_id = run_id, dataset_id, machine_id
        self.experts, self.protocol = experts, protocol
        self.ledger = ForecastLedger()
        self._sequence = 0
        self._observation_count = 0
        self._history: deque[ObservationEvent] = deque(maxlen=protocol.history_limit)
        self._errors = {(e.expert_id, h): deque(maxlen=protocol.error_history_limit)
                        for e in experts for h in protocol.horizons}
        self._error_counts = {key: 0 for key in self._errors}

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def advance(self, timestamp: datetime, value: float) -> StepEvents:
        # Validate before changing any state; no sorting, interpolation or
        # lookahead to subsequent measurements is permitted.
        count = self._observation_count + 1
        observation = ObservationEvent(
            run_id=self.run_id, dataset_id=self.dataset_id, machine_id=self.machine_id,
            event_id=f"observation-{count}", sequence=self._sequence + 1,
            timestamp=timestamp, value=value,
            phase="warmup" if count <= self.protocol.warmup_observations else "evaluation",
        )
        if self._history and timestamp - self._history[-1].timestamp != timedelta(seconds=self.protocol.cadence_seconds):
            raise ValueError("Observations must arrive once in strict five-minute order; gaps are rejected.")
        self._next_sequence()
        self._observation_count = count

        # 1. Arrival; 2. score all and only pending targets at this timestamp.
        scores = tuple(self.ledger.score(f, observation, self._next_sequence())
                       for f in self.ledger.pending_at(timestamp))
        # 3. Only now do the matured errors enter causal state.
        for score in scores:
            key = (score.expert_id, score.horizon)
            self._errors[key].append(score)
            self._error_counts[key] += 1
        self._history.append(observation)
        snapshots = tuple(ErrorSnapshot(
            expert_id=key[0], horizon=key[1], total_matured=self._error_counts[key],
            buffered_count=len(buffer), latest_target=buffer[-1].target if buffer else None,
            mean_absolute_error=sum(s.absolute_error for s in buffer) / len(buffer) if buffer else None,
        ) for key, buffer in self._errors.items())
        state_sequence = self._next_sequence()
        state = StateEvent(f"state-{count}", state_sequence, timestamp, observation.event_id, count, snapshots)

        # 4. Every stub issues both horizons from identical revealed history.
        forecasts = []
        history = tuple(self._history)
        for expert in self.experts:
            for horizon in self.protocol.horizons:
                prediction = expert.predict(history, horizon)
                fallback = prediction is None
                source = next(e for e in self.experts if e.expert_id == "persistence") if fallback else expert
                if fallback:
                    prediction = source.predict(history, horizon)
                buffer = self._errors[(expert.expert_id, horizon)]
                provenance = Provenance(
                    observation_cutoff=timestamp, selection_cutoff=timestamp,
                    matured_error_count=self._error_counts[(expert.expert_id, horizon)],
                    error_history_latest_target=buffer[-1].target if buffer else None,
                )
                sequence = self._next_sequence()
                record = ForecastRecord(
                    forecast_id=f"forecast-{sequence}", run_id=self.run_id, dataset_id=self.dataset_id,
                    machine_id=self.machine_id, origin=timestamp,
                    target=timestamp + timedelta(seconds=horizon * self.protocol.cadence_seconds),
                    horizon=horizon, expert_id=expert.expert_id, model_id=source.expert_id,
                    model_version=source.version, training_cutoff=None, scaling_cutoff=None,
                    version_available_at=None, predicted_value=prediction, issued_sequence=sequence,
                    origin_observation_id=observation.event_id, origin_observation_sequence=observation.sequence,
                    provenance=provenance, selected_expert=source.expert_id,
                    fallback_reason="stub_unavailable" if fallback else None,
                )
                self.ledger.issue(record, observation)
                forecasts.append(record)
        return StepEvents(observation, scores, state, tuple(forecasts))


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(handle, value) -> None:
    handle.write(json.dumps(value, default=_json_default, sort_keys=True, allow_nan=False) + "\n")


def metric_summary(scores: Iterable[ScoreEvent]) -> list[dict]:
    """Summarize evaluation-phase scores by expert/horizon, never positional pairing."""
    groups = defaultdict(list)
    seen = set()
    for score in scores:
        key = (score.run_id, score.dataset_id, score.machine_id, score.forecast_id)
        if key in seen:
            raise ValueError("Duplicate score record.")
        seen.add(key)
        if score.phase == "evaluation":
            groups[(score.expert_id, score.horizon)].append(score)
    result = []
    for (expert, horizon), items in sorted(groups.items()):
        result.append({"expert_id": expert, "horizon": horizon, "count": len(items),
                       "mae": sum(s.absolute_error for s in items) / len(items),
                       "rmse": sqrt(sum(s.squared_error for s in items) / len(items))})
    return result


def run_stream(observations: Iterable[tuple[datetime, float]], *, run_id: str,
               dataset_id: str, machine_id: str = "synthetic_machine",
               experts: tuple[StubExpert, ...] = (StubExpert(),),
               protocol: Protocol = Protocol(), project_root: Path = PROJECT_ROOT) -> Path:
    """Save one exclusive versioned run. No caller-supplied arbitrary output path.

    Invalid observations abort the run and leave a failed manifest/partial audit
    trail. The run ID is still reserved: retry with a new ID, never overwrite.
    """
    simulator = StreamingSimulator(run_id, dataset_id, machine_id, experts, protocol)
    root = Path(project_root).resolve()
    base = root / "data" / "processed" / "dafr" / protocol.protocol_version
    if base.resolve() != base:
        raise ValueError("DAF-R output directory cannot be redirected through symlinks.")
    base.mkdir(parents=True, exist_ok=True)
    directory = base / run_id
    directory.mkdir(exist_ok=False)  # atomic exclusive reservation
    manifest = {"run_id": run_id, "dataset_id": dataset_id, "machine_id": machine_id,
                "status": "incomplete", "protocol": asdict(protocol),
                "experts": [asdict(expert) for expert in experts], "milestone": "M1",
                "training_performed": False, "timestamps": "UTC", "input_sha256": None}
    with (directory / "manifest.json").open("x") as handle:
        _write_json(handle, manifest)
    digest = hashlib.sha256()
    count = 0
    try:
        from contextlib import ExitStack
        with ExitStack() as stack:
            outputs = {name: stack.enter_context((directory / f"{name}.jsonl").open("x"))
                       for name in ("observations", "forecasts", "scores", "states", "events")}
            for timestamp, value in observations:
                step = simulator.advance(timestamp, value)
                count += 1
                raw = json.dumps([timestamp.isoformat(), float(value)], allow_nan=False)
                digest.update((raw + "\n").encode())
                ordered = [("observation", step.observation)]
                ordered.extend(("score", score) for score in step.scores)
                ordered.append(("state", step.state))
                ordered.extend(("forecast", forecast) for forecast in step.forecasts)
                for kind, event in ordered:
                    data = asdict(event)
                    _write_json(outputs[{"observation": "observations", "score": "scores",
                                         "state": "states", "forecast": "forecasts"}[kind]], data)
                    _write_json(outputs["events"], {"kind": kind, "record": data})
            if count == 0:
                raise ValueError("The observation stream cannot be empty.")
        summary = {"observations": count, "forecasts": len(simulator.ledger.forecasts),
                   "scored_forecasts": len(simulator.ledger.scores),
                   "pending_forecast_ids": simulator.ledger.unscored,
                   "evaluation_metrics": metric_summary(simulator.ledger.scores),
                   "note": "M1 deterministic demonstration only; no research performance claim."}
        with (directory / "summary.json").open("x") as handle:
            _write_json(handle, summary)
        manifest.update(status="completed", input_sha256=digest.hexdigest())
    except Exception as error:
        manifest.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        # This updates only this newly reserved run's status, never any prior run.
        with (directory / "manifest.json").open("w") as handle:
            _write_json(handle, manifest)
    return directory


def synthetic_series(count: int = 18) -> tuple[tuple[datetime, float], ...]:
    """Deterministic fixture: linear values, not measurements or research results."""
    positive_integer(count)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return tuple((start + timedelta(minutes=5 * index), 40.0 + index) for index in range(count))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True)
    parser.add_argument("--run-id", required=True)
    arguments = parser.parse_args()
    directory = run_stream(
        synthetic_series(), run_id=arguments.run_id, dataset_id="synthetic_m1_linear",
        experts=(StubExpert(), StubExpert("offset_stub", mode="offset", offset_per_step=0.5)),
        protocol=load_protocol(PROJECT_ROOT / "configs" / "dafr_protocol_v1.json"),
    )
    print(f"Saved synthetic M1 run: {directory}")
    print((directory / "summary.json").read_text())


if __name__ == "__main__":
    main()
