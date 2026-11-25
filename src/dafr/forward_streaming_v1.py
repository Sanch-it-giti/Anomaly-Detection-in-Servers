"""M4A fixed selected-policy forward driver; no model fitting or reselection."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from time import perf_counter
from .contracts_v2 import (TickEventV2,ForecastRecordV2,StateEventV2,SupportSnapshotV2,TelemetryResetV2)
from .streaming_v2 import StreamingSimulatorV2,StubExpertV2
from .real_streaming_v1 import RealStep,RealCallEvent,RealStreamingSimulator
from .real_adapters_v1 import ArtifactReference,load_registered_adapter,RealAdapter,digest_bytes
from .development_qualification_v1 import EPOCH
from pathlib import Path
import json


@dataclass(frozen=True,slots=True)
class ForwardPrediction:
    forecast: ForecastRecordV2
    policy_selection_cutoff: object
    execution_sha256: str
    requested_checkpoint_sha256: str | None

    def __post_init__(self):
        if not EPOCH+timedelta(seconds=1153*300)<=self.forecast.origin<=EPOCH+timedelta(seconds=1612*300):
            raise ValueError("Forward issuance outside authorized block")
        if self.policy_selection_cutoff is not None and self.policy_selection_cutoff>=self.forecast.origin:
            raise ValueError("Policy selection must precede its forward origin")

    def payload(self):
        from dataclasses import asdict
        return {**asdict(self.forecast),"schema_version":"m4a_prediction_v1",
                "policy_selection_cutoff":self.policy_selection_cutoff,
                "execution_sha256":self.execution_sha256,
                "requested_checkpoint_sha256":self.requested_checkpoint_sha256}


class ForwardSimulator(StreamingSimulatorV2):
    _validate_adapter=RealStreamingSimulator._validate_adapter
    _validate_result=RealStreamingSimulator._validate_result

    def __init__(self,run_id,machine,config,prefix_values,execution_sha256,root):
        if machine not in ("m_505","m_1426","m_3028") or len(prefix_values)!=1152:
            raise ValueError("Only selected historical prefixes can reconstruct state")
        self._config=config;self.execution_sha256=execution_sha256
        self.envelopes={};self.tick_seconds=[];self.policy_seconds={}
        adapters={};self.references={}
        for family in ("arima","xgboost"):
            spec=config["models"][machine][family]
            directory=Path(root).resolve()/spec["directory"]
            if directory.resolve()!=directory:raise ValueError("Artifact redirection")
            for name,sha in spec["artifact_sha256"].items():
                if Path(name).name!=name or digest_bytes((directory/name).read_bytes())!=sha:
                    raise ValueError("Selected checkpoint fingerprint mismatch")
            meta=json.loads((directory/"metadata.json").read_text())
            if meta["status"]!="accepted" or meta["family"]!=family:
                raise ValueError("Invalid selected artifact")
            if family=="arima" and meta["order"]!=[1,1,1]:raise ValueError("ARIMA reselection prohibited")
            if family=="xgboost" and any(meta["configuration"][k]!=v for k,v in
                    {"max_depth":2,"n_estimators":100,"learning_rate":.05}.items()):
                raise ValueError("XGBoost reselection prohibited")
            reference=ArtifactReference(directory,spec["metadata_sha256"],
                config["sources"][machine]["historical_prefix"]["sha256"],meta["fit_values_sha256"],machine)
            adapters[family]=load_registered_adapter(reference,prefix_values[:864])
            self.references[family]=reference
        policies=(StubExpertV2(),)+tuple(StubExpertV2(f,"m4a_"+adapters[f].metadata.version) for f in adapters)
        super().__init__(run_id,"alibaba_forward_development",machine,policies)
        self._adapters=adapters
        self._versions={f:a.metadata for f,a in adapters.items()}
        self._parameters={f:a.parameter_sha256 for f,a in adapters.items()}
        history=tuple(TickEventV2(run_id,self.dataset_id,machine,f"fit-history-{i}",i+1,
            EPOCH+timedelta(seconds=300*(i+1)),prefix_values[i],
            "fit_missing" if prefix_values[i] is None else None) for i in range(841,864))
        self._history.extend(history);self._sequence=864
        for i,value in enumerate(prefix_values[:864]):
            self._reveal_quality(i,value,fit=True)
        for adapter in adapters.values():adapter.bootstrap(history)
        self.reconstruction_events=[]
        for i in range(864,1152):
            value=prefix_values[i]
            tick=TickEventV2(run_id,self.dataset_id,machine,f"reconstruct-{i}",self._next_sequence(),
                EPOCH+timedelta(seconds=300*(i+1)),value,"quality_failed" if value is None else None)
            self._history.append(tick);self._reveal_quality(i,value,tick=tick)
            context=self._context(tick)
            self.reconstruction_events.append(("reconstruction_tick",tick))
            for name,adapter in adapters.items():
                result=adapter.update(tick,context)
                self._validate_result(name,result,context,"update")
                if result.status!="ok":raise ValueError("Historical state reconstruction failed")
                event=RealCallEvent(f"reconstruct-update-{self._sequence+1}",self._next_sequence(),
                    "update",adapter.metadata,tick.timestamp,context.context_sha256,result.status,result.reason,result)
                self.reconstruction_events.append(("reconstruction_update",event))
        self.reconstructed_hashes={f:a.state_sha256 for f,a in adapters.items()}
        for family,sha in self.reconstructed_hashes.items():
            if sha!=config["models"][machine][family]["reconstructed_end_1151_state_sha256"]:
                raise ValueError("Reconstruction differs from completed M3B-2 state")
        if self.ledger.decisions or self.ledger.outcomes:raise ValueError("No hindsight issuance during reconstruction")
        self.reconstruction_era=self._era
        self._genuine=0

    def _reveal_quality(self,i,value,tick=None,fit=False):
        if value is None:
            self._genuine_streak=0;self._missing_streak+=1
            if self._missing_streak==4:self._era+=1
        else:
            self._missing_streak=0;self._genuine_streak+=1
            self._last_genuine=tick or TickEventV2(self.run_id,self.dataset_id,self.machine_id,
                f"fit-history-{i}",i+1,EPOCH+timedelta(seconds=300*(i+1)),value)

    def advance(self,timestamp,value,missing_reason=None):
        start=perf_counter()
        step=self._advance(timestamp,value,missing_reason)
        for forecast in step.decisions:
            reference=self.references.get(forecast.policy_id)
            envelope=ForwardPrediction(forecast,
                EPOCH+timedelta(seconds=1152*300) if reference else None,
                self.execution_sha256,reference.metadata_sha256 if reference else None)
            self.envelopes[forecast.forecast_id]=envelope
        self.tick_seconds.append(perf_counter()-start)
        return step

    def _advance(self, timestamp: datetime, value: float | None, missing_reason: str | None = None) -> RealStep:
        if self._ticks>=460 or timestamp!=EPOCH+timedelta(seconds=300*(1153+self._ticks)):
            raise ValueError("Only exact forward ticks [1152,1612) are authorized.")
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
                policy_start=perf_counter()
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
                self.policy_seconds.setdefault((name,horizon),[]).append(perf_counter()-policy_start)
        return RealStep(tick, outcomes, reset, tuple(updates), state, tuple(attempts), tuple(decisions))

    def resource_reports(self):
        return {name:adapter.resources() for name,adapter in self._adapters.items()}

