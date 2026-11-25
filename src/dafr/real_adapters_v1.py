"""Registered M3B-2 real backends. No fitting occurs inside an adapter."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import xgboost as xgb
from statsmodels.tsa.statespace.sarimax import SARIMAX

from .adapters_v1 import origin_features_v1
from .contracts import finite_number, identifier, past_cutoff
from .contracts_v2 import CausalContextV2, TickEventV2, grid_timestamp

TOKEN = object()
IDENTITY = {"kind": "identity", "fitted": False, "scaling_cutoff": None}
FEATURE_SPEC = {"origin_offsets": [0, 1, 2, 5, 11, 23], "genuine_window": 24, "horizons": [1, 12]}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value):
    return digest_bytes(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def sarimax_model(values, order):
    return SARIMAX(np.asarray(values, dtype=float), order=tuple(order),
        trend="c" if order[1] == 0 else "n", simple_differencing=False,
        enforce_stationarity=True, enforce_invertibility=True,
        initialization="approximate_diffuse", loglikelihood_burn=24)


@dataclass(frozen=True, slots=True)
class RealVersion:
    expert_id: str
    version: str
    family: str
    machine_id: str
    training_cutoff: datetime
    available_at: datetime
    scaling_cutoff: None = None
    provenance_kind: str = "development_prefit_v1"

    def __post_init__(self):
        for name in (self.expert_id, self.version, self.machine_id):
            identifier(name)
        if self.family not in ("arima", "xgboost") or self.expert_id != self.family:
            raise ValueError("Unregistered real expert family.")
        grid_timestamp(self.training_cutoff)
        grid_timestamp(self.available_at)
        past_cutoff(self.training_cutoff, self.available_at)
        if self.scaling_cutoff is not None or self.provenance_kind != "development_prefit_v1":
            raise ValueError("Only declared identity transforms are authorized.")

    def validate_origin(self, origin, *, first_tick=False):
        past_cutoff(self.training_cutoff, origin)
        past_cutoff(self.available_at, origin)
        if first_tick and self.training_cutoff >= origin:
            raise ValueError("Do not assimilate fitted observations twice.")


@dataclass(frozen=True, slots=True)
class RealOperation:
    expert_id: str
    version: str
    operation: str
    origin: datetime
    context_sha256: str
    observation_cutoff: datetime
    model_state_cutoff: datetime
    status: str
    reason: str
    state_sha256: str
    horizon: int | None = None
    target: datetime | None = None
    value: float | None = None

    def __post_init__(self):
        if self.status not in ("ok", "unavailable", "numerical_failure") or self.observation_cutoff != self.origin:
            raise ValueError("Invalid real backend response.")
        past_cutoff(self.model_state_cutoff, self.origin)
        if self.status == "ok" and self.model_state_cutoff != self.origin:
            raise ValueError("A successful response requires current model state.")
        if self.operation == "forecast":
            if type(self.horizon) is not int or self.horizon not in (1, 12) or self.target != self.origin + timedelta(minutes=5*self.horizon):
                raise ValueError("Invalid exact forecast target.")
            if self.status == "ok":
                finite_number(self.value)
            elif self.value is not None:
                raise ValueError("Failure cannot contain a prediction.")
        elif self.operation != "update" or any(x is not None for x in (self.value, self.horizon, self.target)):
            raise ValueError("Invalid operation.")


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    directory: Path
    metadata_sha256: str
    source_sha256: str
    fit_values_sha256: str
    machine_id: str


class RealAdapter:
    def __init__(self, token, metadata, artifact, result, boosters):
        if token is not TOKEN:
            raise ValueError("Use the validated artifact factory.")
        self.metadata, self.artifact = metadata, artifact
        self.result, self.boosters = result, boosters
        self._cutoff = metadata.available_at
        self._state_cutoff = self._cutoff
        self._history = deque(maxlen=24)
        self._context = None
        self._invalid = artifact["status"] != "accepted"
        self._updates = self._measurements = self._steps = 0
        self._update_seconds = 0.0
        self._forecast_seconds = []

    @property
    def parameter_sha256(self):
        if self._invalid and self.result is None and not self.boosters:
            return canonical_hash([self.artifact["version"], "rejected_fit"])
        if self.metadata.family == "arima":
            return digest_bytes(np.asarray(self.result.params, dtype=np.float64).tobytes())
        return canonical_hash({str(h): digest_bytes(bytes(b.save_raw(raw_format="json"))) for h,b in sorted(self.boosters.items())})

    @property
    def state_sha256(self):
        state = [self.parameter_sha256, self._cutoff.isoformat(), self._state_cutoff.isoformat(), self._invalid,
                 [[t.timestamp.isoformat(), t.value, t.missing_reason] for t in self._history]]
        if self.result is not None:
            f=self.result.filter_results
            state += [digest_bytes(np.ascontiguousarray(a).tobytes()) for a in (
                f.filtered_state[:,-1],f.filtered_state_cov[:,:,-1],
                f.predicted_state[:,-1],f.predicted_state_cov[:,:,-1])]
        return canonical_hash(state)

    def bootstrap(self, history):
        if self._history or not isinstance(history,tuple) or len(history)!=23 or history[-1].timestamp!=self._cutoff:
            raise ValueError("Bootstrap exactly the preceding 23 fit slots once, without updating the model.")
        if any(b.timestamp-a.timestamp!=timedelta(minutes=5) for a,b in zip(history,history[1:])):
            raise ValueError("Do not compress bootstrap gaps.")
        self._history.extend(history)

    def _response(self, context, operation, status, reason, horizon=None, value=None):
        return RealOperation(self.metadata.expert_id,self.metadata.version,operation,context.origin,
            context.context_sha256,self._cutoff,self._state_cutoff,status,reason,self.state_sha256,
            horizon,context.origin+timedelta(minutes=5*horizon) if horizon is not None else None,value)

    def update(self,tick,context):
        if type(tick) is not TickEventV2 or type(context) is not CausalContextV2:
            raise ValueError("Validated events/context required.")
        if tick.timestamp-self._cutoff!=timedelta(minutes=5) or context.history!=(tuple(self._history)+(tick,))[-24:]:
            raise ValueError("Duplicate, skipped or inconsistent state update.")
        self.metadata.validate_origin(tick.timestamp)
        self._cutoff=tick.timestamp
        self._context=context
        self._history.append(tick)
        self._updates+=1
        start=perf_counter()
        try:
            if self._invalid:
                return self._response(context,"update","unavailable","state_unavailable")
            if self.metadata.family=="arima":
                new=self.result.extend(np.asarray([tick.value if tick.genuine else np.nan]))
                if not np.all(np.isfinite(new.filter_results.filtered_state)) or not np.all(np.isfinite(new.filter_results.filtered_state_cov)):
                    raise FloatingPointError("Invalid filtered state")
                if not np.array_equal(new.params,self.result.params):
                    raise ValueError("Fixed parameters changed")
                self.result=new
            self._state_cutoff=tick.timestamp
            self._steps+=1
            self._measurements+=int(tick.genuine)
            return self._response(context,"update","ok","genuine_update" if tick.genuine else "missing_transition")
        except MemoryError:
            raise
        except (ValueError,ArithmeticError,RuntimeError,np.linalg.LinAlgError,xgb.core.XGBoostError):
            self._invalid=True
            return self._response(context,"update","numerical_failure","update_failed")
        finally:
            self._update_seconds+=perf_counter()-start

    def forecast(self,context,horizon):
        if type(horizon) is not int or horizon not in (1,12) or not context.learned_eligible or context!=self._context:
            raise ValueError("Shared genuine gate/current causal context required.")
        self.metadata.validate_origin(context.origin)
        start=perf_counter()
        try:
            if self._invalid:
                return self._response(context,"forecast","unavailable","state_unavailable",horizon)
            before=self.state_sha256
            if self.metadata.family=="arima":
                raw=np.asarray(self.result.forecast(steps=horizon))
                if raw.shape!=(horizon,):raise ValueError("Wrong ARIMA shape")
                value=float(raw[-1])
            else:
                row=np.asarray([origin_features_v1(context)],dtype=np.float32)
                if row.shape!=(1,6):raise ValueError("Wrong feature shape")
                raw=np.asarray(self.boosters[horizon].inplace_predict(row,strict_shape=True))
                if raw.shape!=(1,1):raise ValueError("Wrong XGBoost shape")
                value=float(raw[0,0])
            finite_number(value)
            if self.state_sha256!=before:raise ValueError("Forecast mutated state")
            return self._response(context,"forecast","ok","real_forecast",horizon,value)
        except MemoryError:
            raise
        except (ValueError,ArithmeticError,RuntimeError,np.linalg.LinAlgError,xgb.core.XGBoostError):
            return self._response(context,"forecast","numerical_failure","forecast_failed",horizon)
        finally:
            self._forecast_seconds.append(perf_counter()-start)

    def resources(self):
        return {"expert_id":self.metadata.expert_id,"update_calls":self._updates,"state_steps":self._steps,
            "genuine_measurement_updates":self._measurements,"buffered_grid_slots":len(self._history),
            "update_seconds":self._update_seconds,"forecast_calls":len(self._forecast_seconds),
            "forecast_seconds":sum(self._forecast_seconds),
            "forecast_p95_seconds":float(np.quantile(self._forecast_seconds,.95)) if self._forecast_seconds else None,
            "state_invalid":self._invalid}


def load_registered_adapter(reference, fit_values):
    """Load only exact registered types from fingerprinted local artifacts."""
    if type(reference) is not ArtifactReference:
        raise ValueError("Expected a validated artifact reference, never an arbitrary model.")
    directory=Path(reference.directory)
    if directory.resolve()!=directory:raise ValueError("Symlink artifact redirection forbidden")
    payload=(directory/"metadata.json").read_bytes()
    if digest_bytes(payload)!=reference.metadata_sha256:raise ValueError("Metadata fingerprint mismatch")
    m=json.loads(payload)
    if (m["machine_id"],m["source_sha256"],m["fit_values_sha256"])!=(reference.machine_id,reference.source_sha256,reference.fit_values_sha256):
        raise ValueError("Artifact/source/fit provenance mismatch")
    if canonical_hash(list(fit_values))!=reference.fit_values_sha256:
        raise ValueError("Fitted observations differ from the checkpoint source")
    if len(fit_values)!=m["fit_grid_size"] or not 24<=len(fit_values)<=864:
        raise ValueError("Invalid fitted grid length")
    if m["scope"] not in ("selected_development_inner_pilot","synthetic_backend_test"):
        raise ValueError("Unregistered data scope")
    if m["scope"]=="selected_development_inner_pilot" and m["machine_id"] not in ("m_505","m_1426","m_3028"):
        raise ValueError("Only selected development machines are admitted")
    if m["scope"]=="selected_development_inner_pilot" and len(fit_values)!=864:
        raise ValueError("Real fitting must end at index 863")
    for name,expected in m["hashes"].items():
        if Path(name).name!=name or (directory/name).resolve()!=directory/name:
            raise ValueError("Invalid artifact file path")
        if digest_bytes((directory/name).read_bytes())!=expected:raise ValueError("Artifact fingerprint mismatch")
    if json.loads((directory/"scaler.json").read_text())!=IDENTITY or json.loads((directory/"features.json").read_text())!=FEATURE_SPEC:
        raise ValueError("Unapproved scaler or feature specification")
    metadata=RealVersion(m["family"],m["version"],m["family"],m["machine_id"],
        datetime.fromisoformat(m["training_cutoff"]),datetime.fromisoformat(m["checkpoint_cutoff"]))
    result=None; boosters={}
    if m["status"]=="accepted":
        if m["family"]=="arima":
            params=np.asarray(json.loads((directory/"params.json").read_text()),dtype=float)
            if not np.all(np.isfinite(params)):raise ValueError("Nonfinite model parameters")
            result=sarimax_model([np.nan if v is None else v for v in fit_values],m["order"]).filter(params)
            if digest_bytes(params.astype(np.float64).tobytes())!=m["parameter_sha256"]:
                raise ValueError("Parameter fingerprint mismatch")
        elif m["family"]=="xgboost":
            for h in (1,12):
                booster=xgb.Booster(); booster.load_model(directory/f"model_h{h}.json"); booster.set_param({"nthread":1})
                if digest_bytes(bytes(booster.save_raw(raw_format="json")))!=m["weight_sha256"][str(h)]:
                    raise ValueError("Loaded booster fingerprint mismatch")
                boosters[h]=booster
    elif m["status"]!="rejected":raise ValueError("Unknown fit status")
    return RealAdapter(TOKEN,metadata,m,result,boosters)
