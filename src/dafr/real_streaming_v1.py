"""M3B-2 real-driver chronology. Previous mock admission remains unchanged."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from .contracts_v2 import (TickEventV2,ForecastRecordV2,StateEventV2,SupportSnapshotV2,TelemetryResetV2)
from .streaming_v2 import StreamingSimulatorV2,StubExpertV2
from .development_qualification_v1 import EPOCH
from .real_adapters_v1 import (ArtifactReference,RealAdapter,RealVersion,RealOperation,load_registered_adapter)


@dataclass(frozen=True,slots=True)
class RealCallEvent:
    event_id: str
    sequence: int
    operation: str
    metadata: RealVersion
    origin: datetime
    context_sha256: str
    status: str
    reason: str
    result: RealOperation | None
    horizon: int | None = None


@dataclass(frozen=True,slots=True)
class RealStep:
    tick: TickEventV2
    outcomes: tuple
    reset: TelemetryResetV2 | None
    updates: tuple
    state: StateEventV2
    attempts: tuple
    decisions: tuple

    def ordered(self):
        events=[("tick",self.tick)]
        events.extend((o.status,o) for o in self.outcomes)
        if self.reset:events.append(("telemetry_reset",self.reset))
        events.extend(("adapter_update",u) for u in self.updates)
        events.append(("state",self.state))
        events.extend(("adapter_attempt",a) for a in self.attempts)
        events.extend(("forecast" if f.issued else "abstention",f) for f in self.decisions)
        return tuple(sorted(events,key=lambda e:e[1].sequence))


class RealStreamingSimulator(StreamingSimulatorV2):
    """Registered artifact-only construction; shared 24-bin gate and V2 ledger.

    Core initialization reuses immutable chronology constants, not the old
    synthetic configuration as execution authorization. The new runner alone
    validates its separately scoped training/execution authorization.
    """
    def __init__(self,run_id,dataset_id,reference,fit_values):
        if type(reference) is not ArtifactReference:
            raise ValueError("Only registered artifact references accepted.")
        adapter=load_registered_adapter(reference,fit_values)
        meta=adapter.metadata
        policies=(StubExpertV2(),StubExpertV2(meta.expert_id,meta.version))
        super().__init__(run_id,dataset_id,meta.machine_id,policies)
        self._adapters={meta.expert_id:adapter}
        self._versions={meta.expert_id:meta}
        self._parameters={meta.expert_id:adapter.parameter_sha256}
        history=[]
        for i in range(len(fit_values)-23,len(fit_values)):
            value=fit_values[i]
            history.append(TickEventV2(run_id,dataset_id,meta.machine_id,f"fit-history-{i}",i+1,
                EPOCH+timedelta(seconds=300*(i+1)),value,"fit_missing" if value is None else None))
        if history[-1].timestamp!=meta.available_at:
            raise ValueError("Checkpoint/history cutoff mismatch.")
        self._history.extend(history)
        self._sequence=len(fit_values)
        # Reconstruct telemetry state from fit masks only; no fitted observation
        # is passed through a numerical update a second time.
        for i,value in enumerate(fit_values):
            if value is None:
                self._genuine_streak=0; self._missing_streak+=1
                if self._missing_streak==4:self._era+=1
            else:
                self._missing_streak=0; self._genuine_streak+=1
                self._last_genuine=TickEventV2(run_id,dataset_id,meta.machine_id,f"fit-history-{i}",i+1,
                    EPOCH+timedelta(seconds=300*(i+1)),value)
        adapter.bootstrap(tuple(history))
        self.bootstrap_era=self._era

    def _validate_adapter(self,name):
        adapter=self._adapters[name]
        if type(adapter) is not RealAdapter or adapter.metadata!=self._versions[name] or adapter.parameter_sha256!=self._parameters[name]:
            raise ValueError("Registered model identity or parameters changed.")

    def _validate_result(self,name,result,context,operation,horizon=None):
        self._validate_adapter(name)
        m=self._versions[name]
        if type(result) is not RealOperation or (
            result.expert_id,result.version,result.origin,result.observation_cutoff,result.context_sha256,result.operation,result.horizon
        )!=(name,m.version,context.origin,context.origin,context.context_sha256,operation,horizon):
            raise ValueError("Real adapter provenance mismatch.")
        if result.state_sha256!=self._adapters[name].state_sha256:
            raise ValueError("Real adapter state fingerprint mismatch.")

    def advance(self, timestamp: datetime, value: float | None, missing_reason: str | None = None) -> RealStep:
        if self._ticks >= 288:
            raise ValueError("Inner validation only: later blocks are unauthorized.")
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
            updates.append(RealCallEvent(f"adapter-update-{sequence}", sequence, "update",
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
                    attempts.append(RealCallEvent(f"adapter-attempt-{sequence}", sequence, "forecast",
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
        return RealStep(tick, outcomes, reset, tuple(updates), state, tuple(attempts), tuple(decisions))

    def resource_reports(self):
        return tuple(a.resources() for a in self._adapters.values())

