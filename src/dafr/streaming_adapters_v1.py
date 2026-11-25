"""M3A mock adapter driver over the preserved M2D chronology primitives.

No old source/configuration is edited, no arbitrary model is accepted, and no
forecast is replaced after issuance. This separate driver adds update hooks
before forecast calls; the original StreamingSimulatorV2 stays stub-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

from .adapters_v1 import (
    AdapterResultV1, MockAdapterSpec, MockAdapterV1, ModelVersionV1, default_mock_specs_v1,
)
from .contracts_v2 import (
    ForecastRecordV2, StateEventV2, SupportSnapshotV2, TelemetryResetV2, TickEventV2,
)
from .streaming_v2 import (
    PilotProtocolV2, StreamingSimulatorV2, StubExpertV2, _write_json,
    load_pilot_protocol_v2, PROJECT_ROOT, synthetic_missing_series_v2,
)


@dataclass(frozen=True, slots=True)
class AdapterCallEventV1:
    event_id: str
    sequence: int
    operation: str
    metadata: ModelVersionV1
    origin: datetime
    context_sha256: str
    status: str
    reason: str
    result: AdapterResultV1 | None
    horizon: int | None = None


@dataclass(frozen=True, slots=True)
class AdapterStepV1:
    tick: TickEventV2
    outcomes: tuple
    reset: TelemetryResetV2 | None
    updates: tuple[AdapterCallEventV1, ...]
    state: StateEventV2
    attempts: tuple[AdapterCallEventV1, ...]
    decisions: tuple[ForecastRecordV2, ...]

    def ordered(self) -> tuple[tuple[str, object], ...]:
        events = [("tick", self.tick)]
        events.extend((o.status, o) for o in self.outcomes)
        if self.reset is not None:
            events.append(("telemetry_reset", self.reset))
        events.extend(("adapter_update", u) for u in self.updates)
        events.append(("state", self.state))
        events.extend(("adapter_attempt", a) for a in self.attempts)
        events.extend(("forecast" if f.issued else "abstention", f) for f in self.decisions)
        return tuple(sorted(events, key=lambda e: e[1].sequence))


class AdapterStreamingSimulatorV1(StreamingSimulatorV2):
    """A separate driver reusing V2 validation, context, ledger and buffers.

    The small chronology orchestration is explicit here because M2D has no
    observation hook. It is checked against M2D by parity/ordering tests.
    Inherited initialization uses fixed stubs only as policy registry entries;
    their predict methods are never called. Only internally constructed,
    exact-type deterministic mocks perform adapter operations.
    """

    def __init__(self, run_id: str, dataset_id: str, machine_id: str = "synthetic_machine",
                 specs: tuple[MockAdapterSpec, ...] | None = None,
                 protocol: PilotProtocolV2 = PilotProtocolV2()):
        specs = default_mock_specs_v1() if specs is None else specs
        if not isinstance(specs, tuple) or not 1 <= len(specs) <= 7 or any(type(s) is not MockAdapterSpec for s in specs):
            raise ValueError("M3A accepts 1–7 frozen mock specs only; no model objects or subclasses.")
        if len({s.metadata.expert_id for s in specs}) != len(specs):
            raise ValueError("Duplicate adapter identifiers.")
        policies = (StubExpertV2(),) + tuple(StubExpertV2(s.metadata.expert_id, s.metadata.version) for s in specs)
        super().__init__(run_id, dataset_id, machine_id, policies, protocol)
        self._adapters = {s.metadata.expert_id: MockAdapterV1(s) for s in specs}
        self._versions = {name: adapter.metadata for name, adapter in self._adapters.items()}
        self._parameters = {name: adapter.parameter_sha256 for name, adapter in self._adapters.items()}

    def _validate_adapter(self, name: str) -> None:
        adapter = self._adapters[name]
        if type(adapter) is not MockAdapterV1 or adapter.metadata != self._versions[name] or adapter.parameter_sha256 != self._parameters[name]:
            raise ValueError("Adapter type, version or fixed parameters changed during replay.")

    def _validate_result(self, name, result, context, operation, horizon=None):
        self._validate_adapter(name)
        metadata = self._versions[name]
        if type(result) is not AdapterResultV1 or (
            result.expert_id, result.version, result.origin, result.observation_cutoff,
            result.context_sha256, result.operation, result.horizon
        ) != (name, metadata.version, context.origin, context.origin,
              context.context_sha256, operation, horizon):
            raise ValueError("Adapter response identity/context/cutoff mismatch.")
        if result.state_sha256 != self._adapters[name].state_sha256:
            raise ValueError("Adapter response state digest mismatch.")

    def advance(self, timestamp: datetime, value: float | None, missing_reason: str | None = None) -> AdapterStepV1:
        tick = TickEventV2(self.run_id, self.dataset_id, self.machine_id,
                           f"tick-{self._ticks + 1}", self._sequence + 1, timestamp, value, missing_reason)
        if self._ticks >= self.protocol.max_grid_ticks:
            raise ValueError("Engineering pilot exceeded its tick memory guard.")
        if self._history and timestamp - self._history[-1].timestamp != timedelta(minutes=5):
            raise ValueError("An explicit event is required at every five-minute grid tick.")
        # Validate every adapter's metadata before changing any causal state.
        for name in self._adapters:
            self._validate_adapter(name)
            self._versions[name].validate_origin(timestamp, first_tick=self._ticks == 0)
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
        outcomes = tuple(self.ledger.resolve(f, tick, self._next_sequence())
                         for f in self.ledger.pending_at(timestamp))
        reset = None
        if self._missing_streak == 4:
            previous = self._era
            self._era += 1
            reset = TelemetryResetV2(f"reset-{self._era}", self._next_sequence(), timestamp,
                                      tick.event_id, previous, self._era)
            for buffer in self._support.values():
                buffer.clear()
        for outcome in outcomes:
            if outcome.status == "scored":
                key = (outcome.policy_id, outcome.policy_version, outcome.horizon)
                self._total_scored[key] += 1
                if outcome.forecast_era == self._era:
                    self._support[key].append(outcome)
        oldest = timestamp - timedelta(minutes=5 * 287)
        for buffer in self._support.values():
            while buffer and buffer[0].target < oldest:
                buffer.popleft()

        context = self._context(tick)
        updates = []
        # All adapters consume the same genuine/missing event, even while gated.
        for name, adapter in self._adapters.items():
            result = adapter.update(tick, context)
            self._validate_result(name, result, context, "update")
            sequence = self._next_sequence()
            updates.append(AdapterCallEventV1(f"adapter-update-{sequence}", sequence, "update",
                self._versions[name], timestamp, context.context_sha256, result.status, result.reason, result))
        update_status = {e.metadata.expert_id: e.status for e in updates}
        snapshots = tuple(SupportSnapshotV2(key[0], key[1], key[2], self._era, len(buffer),
            buffer[-1].target if buffer else None, buffer[0].target if buffer else None,
            len(buffer) >= 100, self._total_scored[key]) for key, buffer in self._support.items())
        state = StateEventV2(f"state-{self._ticks}", self._next_sequence(), timestamp, tick.event_id,
            self._ticks, self._genuine, self._era, self._genuine_streak, self._missing_streak,
            context.learned_eligible, context.last_genuine_age_ticks, context.context_sha256, snapshots)
        decisions, attempts = [], []
        for policy in self.experts:
            name = policy.policy_id
            for horizon in self.protocol.horizons:
                prediction = source = version = None
                provenance = {}
                if name == "persistence":
                    reason = "persistence_reference"
                else:
                    result = None
                    if update_status[name] != "ok":
                        status, reason = "unavailable", "adapter_update_failed"
                    elif not context.learned_eligible:
                        status, reason = "gated", "history_gate"
                    else:
                        adapter = self._adapters[name]
                        before = adapter.state_sha256
                        result = adapter.forecast(context, horizon)
                        self._validate_result(name, result, context, "forecast", horizon)
                        if adapter.state_sha256 != before:
                            raise ValueError("Forecast mutated assimilated state; replay is invalid.")
                        status, reason = result.status, result.reason
                        if status == "ok":
                            prediction, source, version = result.value, name, self._versions[name].version
                            metadata = self._versions[name]
                            provenance = dict(training_cutoff=metadata.training_cutoff,
                                scaling_cutoff=metadata.scaling_cutoff, version_available_at=metadata.available_at)
                    sequence = self._next_sequence()
                    attempts.append(AdapterCallEventV1(f"adapter-attempt-{sequence}", sequence, "forecast",
                        self._versions[name], timestamp, context.context_sha256, status, reason, result, horizon))
                if prediction is not None:
                    availability = "expert"
                elif self._last_genuine is not None and context.last_genuine_age_ticks <= 3:
                    prediction, source, version = self._last_genuine.value, "persistence", "rule_v2"
                    availability = "baseline" if name == "persistence" else "fallback"
                else:
                    availability = "abstained"
                    reason = "no_genuine_history" if self._last_genuine is None else "fallback_stale"
                buffer = self._support[(name, policy.version, horizon)]
                sequence = self._next_sequence()
                forecast = ForecastRecordV2(
                    forecast_id=f"decision-{sequence}", run_id=self.run_id, dataset_id=self.dataset_id,
                    machine_id=self.machine_id, policy_id=name, policy_version=policy.version,
                    origin=timestamp, target=timestamp + timedelta(minutes=5 * horizon), horizon=horizon,
                    sequence=sequence, origin_tick_id=tick.event_id, origin_tick_sequence=tick.sequence,
                    era=self._era, context_sha256=context.context_sha256, learned_eligible=context.learned_eligible,
                    availability=availability, selected_expert=source, source_version=version,
                    predicted_value=prediction, reason=reason, last_genuine_cutoff=context.last_genuine_cutoff,
                    last_genuine_age_ticks=context.last_genuine_age_ticks, support_count=len(buffer),
                    support_latest_target=buffer[-1].target if buffer else None, support_ready=len(buffer) >= 100,
                    **provenance,
                )
                self.ledger.issue(forecast, tick, context)
                decisions.append(forecast)
        return AdapterStepV1(tick, outcomes, reset, tuple(updates), state, tuple(attempts), tuple(decisions))

    def resource_reports(self) -> tuple:
        return tuple(adapter.resources() for adapter in self._adapters.values())


def run_mock_stream_v1(events, *, run_id: str, dataset_id: str = "synthetic_m3a",
                       specs: tuple[MockAdapterSpec, ...] | None = None,
                       project_root: Path = PROJECT_ROOT) -> Path:
    """Exclusive synthetic-only audit output; no external dataset reader."""
    protocol = load_pilot_protocol_v2(PROJECT_ROOT / "configs/dafr_engineering_pilot_v2.json")
    simulator = AdapterStreamingSimulatorV1(run_id, dataset_id, specs=specs, protocol=protocol)
    base = Path(project_root).resolve() / "data/processed/dafr/m3a_mock_v1"
    if base.resolve() != base:
        raise ValueError("Symlinked output ancestors are forbidden.")
    base.mkdir(parents=True, exist_ok=True)
    directory = base / run_id
    directory.mkdir(exist_ok=False)
    config_path = PROJECT_ROOT / "configs/dafr_engineering_pilot_v2.json"
    manifest = {"milestone": "M3A", "integration_version": "mock_adapters_v1", "run_id": run_id,
        "dataset_id": dataset_id, "scope": "synthetic_only", "training_performed": False,
        "confirmation_execution_allowed": False, "m3_training_allowed": False,
        "m2d_protocol_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "specs": [asdict(a._spec) for a in simulator._adapters.values()]}
    with (directory / "manifest.json").open("x") as handle:
        _write_json(handle, manifest)
    completion = {"status": "failed"}
    count = 0
    digest = hashlib.sha256()
    try:
        with (directory / "events.jsonl").open("x") as log, (directory / "forecasts.jsonl").open("x") as forecasts:
            for row in events:
                step = simulator.advance(*row)
                count += 1
                digest.update((json.dumps(asdict(step.tick), default=str, sort_keys=True) + "\n").encode())
                for kind, event in step.ordered():
                    _write_json(log, {"kind": kind, "record": asdict(event)})
                for forecast in step.decisions:
                    _write_json(forecasts, asdict(forecast))
            if not count:
                raise ValueError("Empty mock stream.")
        decisions, outcomes = simulator.ledger.decisions, simulator.ledger.outcomes
        summary = {"grid_ticks": count, "decisions": len(decisions),
            "expert_predictions": sum(f.availability == "expert" for f in decisions),
            "fallback_predictions": sum(f.availability == "fallback" for f in decisions),
            "baseline_predictions": sum(f.availability == "baseline" for f in decisions),
            "abstentions": sum(not f.issued for f in decisions),
            "genuine_scores": sum(o.status == "scored" for o in outcomes),
            "unavailable_targets": sum(o.status == "target_unavailable" for o in outcomes),
            "pending": len(simulator.ledger.pending_ids),
            "resources": [asdict(r) for r in simulator.resource_reports()],
            "note": "Mock arithmetic tests lifecycle only; no real-model forecast or performance claim."}
        with (directory / "summary.json").open("x") as handle:
            _write_json(handle, summary)
        completion = {"status": "completed", "input_sha256": digest.hexdigest(), "grid_ticks": count}
    except Exception as error:
        completion.update(error_type=type(error).__name__, error=str(error), grid_ticks=count)
        raise
    finally:
        with (directory / "completion.json").open("x") as handle:
            _write_json(handle, completion)
    return directory


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    output = run_mock_stream_v1(synthetic_missing_series_v2(), run_id=args.run_id)
    print(output)
    print((output / "summary.json").read_text())
