"""Immutable data contracts for DAF-R's M1 chronological simulator.

Only Python's standard library is required. Timestamps must be aware UTC
datetimes; adapters for external datasets must make their timezone explicit.
None fit/scaler cutoffs mean a deterministic rule has no fitted parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isclose, isfinite
from numbers import Real
import re


def identifier(value: str) -> None:
    """Reject empty identifiers and path separators/traversal components."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("Identifiers need 1–96 letters, digits, underscores or hyphens.")


def utc_timestamp(value: datetime) -> None:
    if not isinstance(value, datetime) or value != value:
        raise ValueError("Timestamp must be a valid datetime.")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Timestamps must explicitly use UTC.")


def finite_number(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError("Expected a finite real number.")


def positive_integer(value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError("Expected a positive integer (not a boolean or fraction).")


def validate_lags(lags: tuple[int, ...]) -> None:
    if not isinstance(lags, tuple) or not lags or len(set(lags)) != len(lags):
        raise ValueError("Lags must be a nonempty tuple of distinct positive integers.")
    for lag in lags:
        positive_integer(lag)


def past_cutoff(value: datetime | None, origin: datetime) -> None:
    if value is not None:
        utc_timestamp(value)
        if value > origin:
            raise ValueError("Provenance cutoff cannot exceed forecast origin.")


@dataclass(frozen=True, slots=True)
class Provenance:
    """Snapshot of information available to a forecast, never live mutable state."""

    observation_cutoff: datetime
    selection_cutoff: datetime
    detector_id: str = "disabled_m1"
    detector_state: str = "disabled"
    detector_cutoff: datetime | None = None
    selection_policy: str = "fixed_expert_m1"
    calibration_id: str = "disabled_m1"
    calibration_score_count: int = 0
    calibration_latest_target: datetime | None = None
    matured_error_count: int = 0
    error_history_latest_target: datetime | None = None

    def __post_init__(self) -> None:
        utc_timestamp(self.observation_cutoff)
        past_cutoff(self.selection_cutoff, self.observation_cutoff)
        if self.selection_cutoff is None:
            raise ValueError("Selection cutoff must be explicit.")
        for value in (self.detector_id, self.detector_state, self.selection_policy, self.calibration_id):
            identifier(value)
        for count in (self.calibration_score_count, self.matured_error_count):
            if type(count) is not int or count < 0:
                raise ValueError("Provenance counts must be nonnegative integers.")
        for cutoff in (self.detector_cutoff, self.calibration_latest_target, self.error_history_latest_target):
            past_cutoff(cutoff, self.observation_cutoff)
        for count, cutoff in ((self.calibration_score_count, self.calibration_latest_target),
                              (self.matured_error_count, self.error_history_latest_target)):
            if (count == 0) != (cutoff is None):
                raise ValueError("History support and latest-target metadata disagree.")


@dataclass(frozen=True, slots=True)
class ObservationEvent:
    run_id: str
    dataset_id: str
    machine_id: str
    event_id: str
    sequence: int
    timestamp: datetime
    value: float
    phase: str

    def __post_init__(self) -> None:
        for value in (self.run_id, self.dataset_id, self.machine_id, self.event_id):
            identifier(value)
        positive_integer(self.sequence)
        utc_timestamp(self.timestamp)
        finite_number(self.value)
        if self.phase not in ("warmup", "evaluation"):
            raise ValueError("Unknown observation phase.")


@dataclass(frozen=True, slots=True)
class ForecastRecord:
    forecast_id: str
    run_id: str
    dataset_id: str
    machine_id: str
    origin: datetime
    target: datetime
    horizon: int
    expert_id: str
    model_id: str
    model_version: str
    training_cutoff: datetime | None
    scaling_cutoff: datetime | None
    version_available_at: datetime | None
    predicted_value: float
    issued_sequence: int
    origin_observation_id: str
    origin_observation_sequence: int
    provenance: Provenance
    selected_expert: str | None = None
    weights: tuple[tuple[str, float], ...] = ()
    interval_status: str = "unavailable"
    lower: float | None = None
    upper: float | None = None
    nominal_coverage: float | None = None
    fallback_reason: str | None = None
    cadence_seconds: int = 300

    def __post_init__(self) -> None:
        for value in (self.forecast_id, self.run_id, self.dataset_id, self.machine_id,
                      self.expert_id, self.model_id, self.model_version, self.origin_observation_id):
            identifier(value)
        utc_timestamp(self.origin)
        utc_timestamp(self.target)
        if type(self.horizon) is not int or self.horizon not in (1, 12):
            raise ValueError("M1 supports only integer horizons 1 and 12.")
        if type(self.cadence_seconds) is not int or self.cadence_seconds != 300:
            raise ValueError("M1 requires a five-minute cadence.")
        if self.target != self.origin + timedelta(seconds=self.horizon * self.cadence_seconds):
            raise ValueError("Target must equal origin plus horizon times cadence.")
        for cutoff in (self.training_cutoff, self.scaling_cutoff, self.version_available_at):
            past_cutoff(cutoff, self.origin)
        if self.version_available_at is not None:
            if any(c is not None and c > self.version_available_at
                   for c in (self.training_cutoff, self.scaling_cutoff)):
                raise ValueError("Model version cannot be available before its fitted data.")
        finite_number(self.predicted_value)
        for sequence in (self.issued_sequence, self.origin_observation_sequence):
            positive_integer(sequence)
        if self.issued_sequence <= self.origin_observation_sequence:
            raise ValueError("Forecast issuance must follow its origin observation.")
        if not isinstance(self.provenance, Provenance) or self.provenance.observation_cutoff != self.origin:
            raise ValueError("Observation cutoff must equal origin.")
        if not isinstance(self.weights, tuple) or any(not isinstance(w, tuple) or len(w) != 2 for w in self.weights):
            raise ValueError("Weights must be immutable (expert, weight) pairs.")
        if (self.selected_expert is None) == (len(self.weights) == 0):
            raise ValueError("Provide exactly one of selected expert or weights.")
        if self.selected_expert is not None:
            identifier(self.selected_expert)
        if self.weights:
            names = []
            for name, weight in self.weights:
                identifier(name)
                finite_number(weight)
                if weight < 0:
                    raise ValueError("Weights cannot be negative.")
                names.append(name)
            if len(set(names)) != len(names) or not isclose(sum(w for _, w in self.weights), 1.0, abs_tol=1e-12):
                raise ValueError("Distinct expert weights must sum to one.")
        if self.interval_status == "available":
            for number in (self.lower, self.upper, self.nominal_coverage):
                finite_number(number)
            if self.lower > self.upper or not 0 < self.nominal_coverage < 1:
                raise ValueError("Invalid interval bounds or nominal coverage.")
        elif self.interval_status == "unavailable":
            if any(v is not None for v in (self.lower, self.upper, self.nominal_coverage)):
                raise ValueError("Unavailable intervals cannot contain bounds or coverage.")
        else:
            raise ValueError("M1 interval status must be available or unavailable.")
        if self.fallback_reason is not None:
            identifier(self.fallback_reason)

    @property
    def key(self) -> tuple:
        """Semantic identity prevents duplicate forecasts under different IDs."""
        return (self.run_id, self.dataset_id, self.machine_id, self.expert_id, self.origin, self.horizon)


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    """A later event referring to the original immutable issued forecast."""

    event_id: str
    sequence: int
    forecast_id: str
    observation_id: str
    run_id: str
    dataset_id: str
    machine_id: str
    expert_id: str
    origin: datetime
    target: datetime
    horizon: int
    arrival_sequence: int
    issued_sequence: int
    actual: float
    predicted_value: float
    signed_error: float
    absolute_error: float
    squared_error: float
    phase: str

    def __post_init__(self) -> None:
        for value in (self.event_id, self.forecast_id, self.observation_id, self.run_id,
                      self.dataset_id, self.machine_id, self.expert_id):
            identifier(value)
        utc_timestamp(self.origin)
        utc_timestamp(self.target)
        if type(self.horizon) is not int or self.horizon not in (1, 12):
            raise ValueError("Invalid score horizon.")
        if self.target != self.origin + timedelta(minutes=5 * self.horizon):
            raise ValueError("Score origin/target/horizon disagree.")
        for value in (self.sequence, self.arrival_sequence, self.issued_sequence):
            positive_integer(value)
        if not self.issued_sequence < self.arrival_sequence < self.sequence:
            raise ValueError("Required sequence: issue < arrival < score.")
        for number in (self.actual, self.predicted_value, self.signed_error, self.absolute_error, self.squared_error):
            finite_number(number)
        error = self.actual - self.predicted_value
        if not all(isclose(a, b, rel_tol=1e-12, abs_tol=1e-12) for a, b in (
            (self.signed_error, error), (self.absolute_error, abs(error)), (self.squared_error, error * error))):
            raise ValueError("Score fields disagree with actual minus prediction.")
        if self.phase not in ("warmup", "evaluation"):
            raise ValueError("Unknown score phase.")


def score_forecast(forecast: ForecastRecord, observation: ObservationEvent, sequence: int) -> ScoreEvent:
    """Join by run/dataset/machine/target; preserve the forecast's horizon.

    Position in an input array is never used. An observation can legitimately
    score multiple origins/horizons whose targets equal its timestamp.
    """
    if (forecast.run_id, forecast.dataset_id, forecast.machine_id, forecast.target) != (
        observation.run_id, observation.dataset_id, observation.machine_id, observation.timestamp
    ):
        raise ValueError("Observation does not match this forecast's target identity.")
    error = observation.value - forecast.predicted_value
    return ScoreEvent(
        event_id=f"score-{sequence}", sequence=sequence, forecast_id=forecast.forecast_id,
        observation_id=observation.event_id, run_id=forecast.run_id, dataset_id=forecast.dataset_id,
        machine_id=forecast.machine_id, expert_id=forecast.expert_id, origin=forecast.origin,
        target=forecast.target, horizon=forecast.horizon, arrival_sequence=observation.sequence,
        issued_sequence=forecast.issued_sequence, actual=observation.value,
        predicted_value=forecast.predicted_value, signed_error=error, absolute_error=abs(error),
        squared_error=error * error, phase=observation.phase,
    )
