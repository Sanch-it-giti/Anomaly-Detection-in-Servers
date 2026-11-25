"""Immutable M2D contracts. Missing CPU is explicit; it is never zero CPU.

V1 contracts remain unchanged. This pilot implements no learned models,
adaptive selection, drift detection, or prediction interval construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isclose

from .contracts import finite_number, identifier, past_cutoff, positive_integer, utc_timestamp


def grid_timestamp(value: datetime) -> None:
    utc_timestamp(value)
    if value.minute % 5 or value.second or value.microsecond:
        raise ValueError("V2 requires UTC timestamps on the five-minute grid.")


def nonnegative_integer(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("Expected a nonnegative integer.")


@dataclass(frozen=True, slots=True)
class TickEventV2:
    run_id: str
    dataset_id: str
    machine_id: str
    event_id: str
    sequence: int
    timestamp: datetime
    value: float | None
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        for value in (self.run_id, self.dataset_id, self.machine_id, self.event_id):
            identifier(value)
        positive_integer(self.sequence)
        grid_timestamp(self.timestamp)
        if self.value is None:
            identifier(self.missing_reason)
        else:
            finite_number(self.value)
            if not 0 <= self.value <= 100 or self.missing_reason is not None:
                raise ValueError("Genuine CPU must be in [0,100] with no missing reason.")

    @property
    def genuine(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class CausalContextV2:
    """The identical immutable revealed window supplied to every eligible stub."""

    origin: datetime
    history: tuple[TickEventV2, ...]
    era: int
    genuine_streak: int
    missing_streak: int
    last_genuine_cutoff: datetime | None
    last_genuine_age_ticks: int | None
    context_sha256: str

    def __post_init__(self) -> None:
        grid_timestamp(self.origin)
        for value in (self.era, self.genuine_streak, self.missing_streak):
            nonnegative_integer(value)
        if not isinstance(self.history, tuple) or not 1 <= len(self.history) <= 24:
            raise ValueError("Context requires an immutable trailing window of at most 24 slots.")
        if any(type(t) is not TickEventV2 for t in self.history):
            raise ValueError("Context contains an invalid tick.")
        if self.history[-1].timestamp != self.origin:
            raise ValueError("Context must end at its origin.")
        first = self.history[0]
        for previous, current in zip(self.history, self.history[1:]):
            if current.timestamp - previous.timestamp != timedelta(minutes=5):
                raise ValueError("Context must retain every grid position.")
            if (current.run_id, current.dataset_id, current.machine_id) != (
                first.run_id, first.dataset_id, first.machine_id
            ) or current.sequence <= previous.sequence:
                raise ValueError("Context identity/order mismatch.")
        past_cutoff(self.last_genuine_cutoff, self.origin)
        if (self.last_genuine_cutoff is None) != (self.last_genuine_age_ticks is None):
            raise ValueError("Last genuine cutoff and age must agree.")
        if self.last_genuine_cutoff is not None:
            nonnegative_integer(self.last_genuine_age_ticks)
            if self.origin - self.last_genuine_cutoff != timedelta(minutes=5 * self.last_genuine_age_ticks):
                raise ValueError("Last genuine age must use the original grid.")
        if not isinstance(self.context_sha256, str) or len(self.context_sha256) != 64:
            raise ValueError("Context digest must be SHA-256.")

    @property
    def learned_eligible(self) -> bool:
        return len(self.history) == 24 and all(t.genuine for t in self.history)


@dataclass(frozen=True, slots=True)
class ForecastRecordV2:
    """One immutable policy decision; abstention is not an issued prediction."""

    forecast_id: str
    run_id: str
    dataset_id: str
    machine_id: str
    policy_id: str
    policy_version: str
    origin: datetime
    target: datetime
    horizon: int
    sequence: int
    origin_tick_id: str
    origin_tick_sequence: int
    era: int
    context_sha256: str
    learned_eligible: bool
    availability: str
    selected_expert: str | None
    source_version: str | None
    predicted_value: float | None
    reason: str
    last_genuine_cutoff: datetime | None
    last_genuine_age_ticks: int | None
    support_count: int = 0
    support_latest_target: datetime | None = None
    support_ready: bool = False
    training_cutoff: datetime | None = None
    scaling_cutoff: datetime | None = None
    version_available_at: datetime | None = None
    protocol_id: str = "dafr_engineering_pilot_v2"
    interval_status: str = "not_implemented"
    lower: float | None = None
    upper: float | None = None
    detector_status: str = "disabled_m2d"
    selection_status: str = "fixed_policy_no_switching"

    def __post_init__(self) -> None:
        for value in (self.forecast_id, self.run_id, self.dataset_id, self.machine_id,
                      self.policy_id, self.policy_version, self.origin_tick_id, self.reason):
            identifier(value)
        grid_timestamp(self.origin)
        grid_timestamp(self.target)
        if type(self.horizon) is not int or self.horizon not in (1, 12):
            raise ValueError("V2 horizons are integer ticks 1 and 12.")
        if self.target != self.origin + timedelta(minutes=5 * self.horizon):
            raise ValueError("Forecast target must match its exact grid horizon.")
        positive_integer(self.sequence)
        positive_integer(self.origin_tick_sequence)
        if self.sequence <= self.origin_tick_sequence:
            raise ValueError("Issuance must follow the revealed origin tick.")
        nonnegative_integer(self.era)
        if type(self.learned_eligible) is not bool or type(self.support_ready) is not bool:
            raise ValueError("Eligibility/support flags must be booleans.")
        if not isinstance(self.context_sha256, str) or len(self.context_sha256) != 64:
            raise ValueError("Forecast requires a context digest.")
        for cutoff in (self.last_genuine_cutoff, self.training_cutoff,
                       self.scaling_cutoff, self.version_available_at, self.support_latest_target):
            past_cutoff(cutoff, self.origin)
        if self.version_available_at is not None and any(
            c is not None and c > self.version_available_at for c in (self.training_cutoff, self.scaling_cutoff)
        ):
            raise ValueError("Model availability cannot precede its fitting/scaling data.")
        if (self.last_genuine_cutoff is None) != (self.last_genuine_age_ticks is None):
            raise ValueError("Last genuine input metadata disagrees.")
        if self.last_genuine_cutoff is not None:
            nonnegative_integer(self.last_genuine_age_ticks)
            if self.origin - self.last_genuine_cutoff != timedelta(minutes=5 * self.last_genuine_age_ticks):
                raise ValueError("Input age does not match its cutoff.")
        nonnegative_integer(self.support_count)
        if self.support_count > 288 or (self.support_count == 0) != (self.support_latest_target is None):
            raise ValueError("Support count/cutoff mismatch.")
        if self.support_ready != (self.support_count >= 100):
            raise ValueError("Support readiness means at least 100 genuine matured scores.")
        if self.support_latest_target is not None and self.origin - self.support_latest_target >= timedelta(minutes=5 * 288):
            raise ValueError("Support is older than the 288-tick bound.")
        if self.availability not in ("expert", "baseline", "fallback", "abstained"):
            raise ValueError("Unknown decision availability.")
        if self.availability == "abstained":
            if any(v is not None for v in (self.predicted_value, self.selected_expert, self.source_version)):
                raise ValueError("Abstention cannot contain a prediction or source expert.")
        else:
            finite_number(self.predicted_value)
            identifier(self.selected_expert)
            identifier(self.source_version)
            if self.last_genuine_cutoff is None:
                raise ValueError("A prediction requires a genuine source measurement.")
            if self.availability in ("baseline", "fallback") and (
                self.selected_expert != "persistence" or self.source_version != "rule_v2"
                or self.last_genuine_age_ticks > 3
            ):
                raise ValueError("Persistence is available for at most three grid ticks.")
            if (self.availability == "baseline") != (self.policy_id == "persistence"):
                raise ValueError("Baseline attribution is reserved for the persistence policy.")
            if self.availability == "expert" and (
                not self.learned_eligible or self.last_genuine_age_ticks != 0
                or self.selected_expert != self.policy_id
            ):
                raise ValueError("Stub issuance requires the common genuine-history gate.")
        if (self.protocol_id, self.interval_status, self.detector_status, self.selection_status) != (
            "dafr_engineering_pilot_v2", "not_implemented", "disabled_m2d", "fixed_policy_no_switching"
        ) or self.lower is not None or self.upper is not None:
            raise ValueError("M2D cannot enable intervals, drift or adaptive selection.")

    @property
    def issued(self) -> bool:
        return self.availability != "abstained"

    @property
    def key(self) -> tuple:
        return (self.run_id, self.dataset_id, self.machine_id, self.policy_id, self.origin, self.horizon)


@dataclass(frozen=True, slots=True)
class TargetOutcomeV2:
    event_id: str
    sequence: int
    forecast_id: str
    tick_id: str
    run_id: str
    dataset_id: str
    machine_id: str
    policy_id: str
    policy_version: str
    horizon: int
    origin: datetime
    target: datetime
    issued_sequence: int
    arrival_sequence: int
    forecast_era: int
    status: str
    predicted_value: float
    actual: float | None
    signed_error: float | None
    absolute_error: float | None
    squared_error: float | None
    interval_hit: bool | None = None

    def __post_init__(self) -> None:
        for value in (self.event_id, self.forecast_id, self.tick_id, self.run_id,
                      self.dataset_id, self.machine_id, self.policy_id, self.policy_version):
            identifier(value)
        grid_timestamp(self.origin)
        grid_timestamp(self.target)
        if type(self.horizon) is not int or self.horizon not in (1, 12) or self.target != self.origin + timedelta(minutes=5 * self.horizon):
            raise ValueError("Target outcome horizon/timestamps disagree.")
        for value in (self.sequence, self.issued_sequence, self.arrival_sequence):
            positive_integer(value)
        if not self.issued_sequence < self.arrival_sequence < self.sequence:
            raise ValueError("Required event order: issue < arrival < outcome.")
        nonnegative_integer(self.forecast_era)
        finite_number(self.predicted_value)
        if self.status == "target_unavailable":
            if any(v is not None for v in (self.actual, self.signed_error, self.absolute_error, self.squared_error)):
                raise ValueError("Missing targets have no invented errors.")
        elif self.status == "scored":
            for value in (self.actual, self.signed_error, self.absolute_error, self.squared_error):
                finite_number(value)
            if not 0 <= self.actual <= 100:
                raise ValueError("Actual CPU must be genuine [0,100] data.")
            error = self.actual - self.predicted_value
            for actual, expected in ((self.signed_error, error), (self.absolute_error, abs(error)), (self.squared_error, error * error)):
                if not isclose(actual, expected, abs_tol=1e-12, rel_tol=1e-12):
                    raise ValueError("Outcome errors disagree with the original prediction.")
        else:
            raise ValueError("Unknown target outcome status.")
        if self.interval_hit is not None:
            raise ValueError("No interval outcomes exist in M2D.")


def resolve_target_v2(forecast: ForecastRecordV2, tick: TickEventV2, sequence: int) -> TargetOutcomeV2:
    if not forecast.issued:
        raise ValueError("An abstention is not a pending forecast.")
    if (forecast.run_id, forecast.dataset_id, forecast.machine_id, forecast.target) != (
        tick.run_id, tick.dataset_id, tick.machine_id, tick.timestamp
    ):
        raise ValueError("Only the genuine or missing event at the exact target can resolve a forecast.")
    error = tick.value - forecast.predicted_value if tick.genuine else None
    return TargetOutcomeV2(
        event_id=f"outcome-{sequence}", sequence=sequence, forecast_id=forecast.forecast_id,
        tick_id=tick.event_id, run_id=forecast.run_id, dataset_id=forecast.dataset_id,
        machine_id=forecast.machine_id, policy_id=forecast.policy_id, policy_version=forecast.policy_version,
        horizon=forecast.horizon, origin=forecast.origin, target=forecast.target,
        issued_sequence=forecast.sequence, arrival_sequence=tick.sequence, forecast_era=forecast.era,
        status="scored" if tick.genuine else "target_unavailable", predicted_value=forecast.predicted_value,
        actual=tick.value, signed_error=error, absolute_error=abs(error) if error is not None else None,
        squared_error=error * error if error is not None else None,
    )


@dataclass(frozen=True, slots=True)
class SupportSnapshotV2:
    policy_id: str
    policy_version: str
    horizon: int
    era: int
    count: int
    latest_target: datetime | None
    earliest_target: datetime | None
    ready: bool
    total_genuine_scored: int


@dataclass(frozen=True, slots=True)
class TelemetryResetV2:
    event_id: str
    sequence: int
    timestamp: datetime
    trigger_tick_id: str
    previous_era: int
    new_era: int
    missing_streak: int = 4
    reason: str = "fourth_consecutive_missing_tick"


@dataclass(frozen=True, slots=True)
class StateEventV2:
    event_id: str
    sequence: int
    timestamp: datetime
    tick_id: str
    grid_ticks: int
    genuine_ticks: int
    era: int
    genuine_streak: int
    missing_streak: int
    learned_eligible: bool
    last_genuine_age_ticks: int | None
    context_sha256: str
    support: tuple[SupportSnapshotV2, ...]


@dataclass(frozen=True, slots=True)
class StepEventsV2:
    tick: TickEventV2
    outcomes: tuple[TargetOutcomeV2, ...]
    reset: TelemetryResetV2 | None
    state: StateEventV2
    decisions: tuple[ForecastRecordV2, ...]

    def ordered(self) -> tuple[tuple[str, object], ...]:
        events = [("tick", self.tick)]
        events.extend((outcome.status, outcome) for outcome in self.outcomes)
        if self.reset is not None:
            events.append(("telemetry_reset", self.reset))
        events.append(("state", self.state))
        events.extend(("forecast" if f.issued else "abstention", f) for f in self.decisions)
        return tuple(events)
