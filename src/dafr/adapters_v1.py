"""M3A causal adapter interface and deterministic mocks; no fitting API.

Family names describe lifecycle tests, not implementations of ARIMA, XGBoost
or LSTM. Only MockAdapterSpec instances may enter the integration runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from time import perf_counter_ns

from .contracts import finite_number, identifier, past_cutoff
from .contracts_v2 import CausalContextV2, TickEventV2, grid_timestamp, nonnegative_integer


DEFAULT_AVAILABLE = datetime(2025, 12, 31, 23, 55, tzinfo=timezone.utc)
ORIGIN_OFFSETS = (0, 1, 2, 5, 11, 23)


@dataclass(frozen=True, slots=True)
class ModelVersionV1:
    expert_id: str
    version: str
    family: str
    available_at: datetime = DEFAULT_AVAILABLE
    training_cutoff: datetime | None = None
    scaling_cutoff: datetime | None = None
    provenance_kind: str = "synthetic_mock_no_fit"

    def __post_init__(self) -> None:
        for name in (self.expert_id, self.version):
            identifier(name)
        if self.expert_id == "persistence" or self.family not in ("arima", "xgboost", "lstm"):
            raise ValueError("Mocks need a distinct expert ID and declared lifecycle family.")
        grid_timestamp(self.available_at)
        for cutoff in (self.training_cutoff, self.scaling_cutoff):
            if cutoff is not None:
                grid_timestamp(cutoff)
                past_cutoff(cutoff, self.available_at)
        if self.provenance_kind != "synthetic_mock_no_fit":
            raise ValueError("M3A accepts synthetic metadata only, never a fitted artifact.")

    def validate_origin(self, origin: datetime, *, first_tick: bool = False) -> None:
        for cutoff in (self.training_cutoff, self.scaling_cutoff, self.available_at):
            past_cutoff(cutoff, origin)
        if first_tick and any(c is not None and c >= origin for c in (self.training_cutoff, self.scaling_cutoff)):
            raise ValueError("Replay must begin after declared fit/scaling cutoffs; do not assimilate fitting data twice.")


@dataclass(frozen=True, slots=True)
class MockAdapterSpec:
    metadata: ModelVersionV1
    offset_per_step: float = 0.25
    fault: str = "none"
    fault_ticks: tuple[int, ...] = ()
    fault_horizon: int | None = None

    def __post_init__(self) -> None:
        if type(self.metadata) is not ModelVersionV1:
            raise ValueError("Expected validated frozen mock metadata.")
        finite_number(self.offset_per_step)
        if abs(self.offset_per_step) > 100:
            raise ValueError("Mock arithmetic is bounded to avoid overflow.")
        if self.fault not in ("none", "update_error", "update_unavailable", "forecast_error",
                              "forecast_nonfinite", "forecast_unavailable"):
            raise ValueError("Unknown deterministic fault injection.")
        if not isinstance(self.fault_ticks, tuple) or tuple(sorted(set(self.fault_ticks))) != self.fault_ticks:
            raise ValueError("Fault ticks must be an immutable sorted unique tuple.")
        for tick in self.fault_ticks:
            nonnegative_integer(tick)
        if self.fault_horizon is not None and (type(self.fault_horizon) is not int or self.fault_horizon not in (1, 12)):
            raise ValueError("Fault horizon must be 1 or 12.")


@dataclass(frozen=True, slots=True)
class AdapterResultV1:
    expert_id: str
    version: str
    operation: str
    origin: datetime
    context_sha256: str
    observation_cutoff: datetime
    status: str
    reason: str
    state_sha256: str
    horizon: int | None = None
    target: datetime | None = None
    value: float | None = None
    state_steps: int = 0
    measurement_updates: int = 0

    def __post_init__(self) -> None:
        for name in (self.expert_id, self.version, self.reason):
            identifier(name)
        grid_timestamp(self.origin)
        if self.observation_cutoff != self.origin:
            raise ValueError("Adapter state must be updated through the current origin.")
        for digest in (self.context_sha256, self.state_sha256):
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Expected a hexadecimal SHA-256 digest.")
        if self.status not in ("ok", "unavailable", "numerical_failure"):
            raise ValueError("Unknown adapter status.")
        for count in (self.state_steps, self.measurement_updates):
            nonnegative_integer(count)
        if self.operation == "update":
            if any(v is not None for v in (self.horizon, self.target, self.value)):
                raise ValueError("An update receipt cannot contain a forecast.")
        elif self.operation == "forecast":
            if type(self.horizon) is not int or self.horizon not in (1, 12):
                raise ValueError("Unknown forecast horizon.")
            if self.target != self.origin + timedelta(minutes=5 * self.horizon):
                raise ValueError("Adapter target does not match the requested elapsed horizon.")
            if self.status == "ok":
                finite_number(self.value)
            elif self.value is not None:
                raise ValueError("A failed/unavailable adapter cannot invent a prediction.")
        else:
            raise ValueError("Unknown adapter operation.")


@dataclass(frozen=True, slots=True)
class RuntimeReportV1:
    expert_id: str
    update_calls: int
    forecast_calls: int
    state_steps: int
    measurement_updates: int
    buffered_grid_slots: int
    elapsed_nanoseconds: int
    state_invalid: bool


class ExpertAdapterV1(ABC):
    """Read-only metadata, causal assimilation, nonmutating forecast, resources.

    Future implementations must not expose fit/refit during replay. Implementing
    this ABC alone does not authorize entry to the mock-only runner.
    """

    @property
    @abstractmethod
    def metadata(self) -> ModelVersionV1: ...

    @abstractmethod
    def update(self, tick: TickEventV2, context: CausalContextV2) -> AdapterResultV1: ...

    @abstractmethod
    def forecast(self, context: CausalContextV2, horizon: int) -> AdapterResultV1: ...

    @abstractmethod
    def resources(self) -> RuntimeReportV1: ...


def genuine_window_v1(context: CausalContextV2) -> tuple[float, ...]:
    """Shared oldest-to-newest window; never drop nulls or compress gaps."""
    if type(context) is not CausalContextV2 or not context.learned_eligible:
        raise ValueError("The authoritative gate requires 24 consecutive genuine bins.")
    return tuple(t.value for t in context.history)


def origin_features_v1(context: CausalContextV2) -> tuple[float, ...]:
    """Origin-relative lookbacks, not target-relative lags at h=12."""
    values = genuine_window_v1(context)
    return tuple(values[-1 - offset] for offset in ORIGIN_OFFSETS)


class MockAdapterV1(ExpertAdapterV1):
    """Bounded deterministic state machine, not a real ML/statistical model.

    A failed update latches state invalid until a future separately authorized
    version replacement; no silent catch-up/refit. Forecast-only failures are
    retryable because forecasting cannot mutate assimilated model state.
    """

    def __init__(self, spec: MockAdapterSpec):
        if type(spec) is not MockAdapterSpec:
            raise ValueError("Only validated mock specs are accepted.")
        self._spec = spec
        self._history: deque[TickEventV2] = deque(maxlen=24)
        self._context_sha = None
        self._last_context: CausalContextV2 | None = None
        self._state = 40.0
        self._steps = self._measurements = self._updates = self._forecasts = self._elapsed = 0
        self._invalid = False

    @property
    def metadata(self) -> ModelVersionV1:
        return self._spec.metadata

    @property
    def parameter_sha256(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self._spec), default=str, sort_keys=True).encode()).hexdigest()

    @property
    def state_sha256(self) -> str:
        payload = [self.parameter_sha256, self._state, self._steps, self._measurements,
                   self._invalid, self._context_sha,
                   [[t.timestamp.isoformat(), t.value, t.missing_reason] for t in self._history]]
        return hashlib.sha256(json.dumps(payload, allow_nan=False).encode()).hexdigest()

    def _result(self, context, operation, status, reason, horizon=None, value=None):
        return AdapterResultV1(
            self.metadata.expert_id, self.metadata.version, operation, context.origin,
            context.context_sha256, self._history[-1].timestamp, status, reason, self.state_sha256,
            horizon, context.origin + timedelta(minutes=5 * horizon) if horizon is not None else None,
            value, self._steps, self._measurements,
        )

    def update(self, tick: TickEventV2, context: CausalContextV2) -> AdapterResultV1:
        if type(tick) is not TickEventV2 or type(context) is not CausalContextV2:
            raise ValueError("Updates require validated causal events/context.")
        if context.history[-1] != tick or context.origin != tick.timestamp:
            raise ValueError("Update cannot use a future or different tick.")
        self.metadata.validate_origin(tick.timestamp, first_tick=not self._history)
        if self._history and tick.timestamp - self._history[-1].timestamp != timedelta(minutes=5):
            raise ValueError("Adapters must consume every genuine/missing tick exactly once.")
        expected = (tuple(self._history) + (tick,))[-24:]
        if context.history != expected:
            raise ValueError("Adapter context must equal its complete revealed trailing grid.")
        start = perf_counter_ns()
        ordinal = self._updates
        self._updates += 1
        self._history.append(tick)
        self._context_sha = context.context_sha256
        self._last_context = context
        try:
            if self._invalid:
                return self._result(context, "update", "unavailable", "state_invalid")
            fault = ordinal in self._spec.fault_ticks
            if fault and self._spec.fault in ("update_error", "update_unavailable"):
                self._invalid = True
                status = "numerical_failure" if self._spec.fault == "update_error" else "unavailable"
                return self._result(context, "update", status, "update_failed")
            self._steps += 1
            # One mock transition per elapsed grid step, never an actual ARIMA fit.
            if self.metadata.family == "arima":
                self._state *= 0.99
            if tick.genuine:
                self._measurements += 1
                if self.metadata.family == "arima":
                    self._state = tick.value
            return self._result(context, "update", "ok", "genuine_update" if tick.genuine else "missing_transition")
        finally:
            self._elapsed += perf_counter_ns() - start

    def forecast(self, context: CausalContextV2, horizon: int) -> AdapterResultV1:
        values = genuine_window_v1(context)
        if type(horizon) is not int or horizon not in (1, 12):
            raise ValueError("Only h=1/h=12 are supported.")
        if (not self._history or self._history[-1].timestamp != context.origin
            or self._context_sha != context.context_sha256 or context != self._last_context):
            raise ValueError("Forecast requires its current causal update first.")
        self.metadata.validate_origin(context.origin)
        start = perf_counter_ns()
        self._forecasts += 1
        try:
            if self._invalid:
                return self._result(context, "forecast", "unavailable", "state_invalid", horizon)
            fault = self._updates - 1 in self._spec.fault_ticks and self._spec.fault_horizon in (None, horizon)
            if fault and self._spec.fault == "forecast_unavailable":
                return self._result(context, "forecast", "unavailable", "backend_unavailable", horizon)
            try:
                if fault and self._spec.fault == "forecast_error":
                    raise FloatingPointError("Synthetic numerical backend failure")
                if self.metadata.family == "arima":
                    value = self._state
                elif self.metadata.family == "xgboost":
                    features = origin_features_v1(context)
                    value = sum(features) / len(features)
                else:
                    value = sum(values) / len(values)
                value += horizon * self._spec.offset_per_step
                if fault and self._spec.fault == "forecast_nonfinite":
                    value = float("nan")
                finite_number(value)
            except (ArithmeticError, ValueError):
                return self._result(context, "forecast", "numerical_failure", "forecast_failed", horizon)
            return self._result(context, "forecast", "ok", "deterministic_mock", horizon, value)
        finally:
            self._elapsed += perf_counter_ns() - start

    def resources(self) -> RuntimeReportV1:
        return RuntimeReportV1(self.metadata.expert_id, self._updates, self._forecasts, self._steps,
                                self._measurements, len(self._history), self._elapsed, self._invalid)


def default_mock_specs_v1() -> tuple[MockAdapterSpec, ...]:
    return tuple(MockAdapterSpec(ModelVersionV1(f"mock_{family}", "mock_v1", family))
                 for family in ("arima", "xgboost", "lstm"))
