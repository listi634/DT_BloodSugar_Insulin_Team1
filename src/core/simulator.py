"""Simulation orchestration for deterministic event/controller/model flow."""

from dataclasses import dataclass
from dataclasses import replace

import numpy as np

from src.core.controller import ProportionalController
from src.core.model import PhysiologyModel
from src.core.estimator import EstimatorTraceStep
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.state import ControllerConfig
from src.core.state import EstimatorConfig
from src.core.state import IntegratorConfig
from src.core.state import ModelConfig
from src.core.state import PendingEvents
from src.core.state import SimulationSnapshot
from src.core.state import SimulationState
from src.core.state import BolusEvent
from src.core.state import SportEvent


class GlucoseSimulator:
    """Coordinates events, control decisions, integration, and history."""

    def __init__(
        self,
        model: PhysiologyModel,
        controller: ProportionalController,
        model_config: ModelConfig,
        controller_config: ControllerConfig,
        initial_state: SimulationState,
        estimator: ExtendedKalmanFilterEstimator | None = None,
        integrator_config: IntegratorConfig | None = None,
    ) -> None:
        """Create simulator with explicit dependencies and typed state."""
        model_config.validate()
        controller_config.validate()
        if initial_state.glucose < 0.0:
            raise ValueError("initial_state.glucose must be non-negative")
        if initial_state.insulin < 0.0:
            raise ValueError("initial_state.insulin must be non-negative")
        if initial_state.basal_insulin_rate < 0.0:
            raise ValueError(
                "initial_state.basal_insulin_rate must be non-negative"
            )

        self._model = model
        if integrator_config is not None:
            self._model.set_integrator_config(integrator_config)
        self._controller = controller
        self._model_config = model_config
        self._controller_config = controller_config
        self._initial_state = replace(initial_state)
        self._state = replace(initial_state)
        self._estimator = estimator or ExtendedKalmanFilterEstimator(
            model=self._model,
            model_config=self._model_config,
            initial_state=self._state,
            estimator_config=EstimatorConfig(),
        )
        self._pending = PendingEvents()
        self._history: list[SimulationSnapshot] = [
            self._to_snapshot(self._state)
        ]
        self._estimator_trace: list[EstimatorTraceStep] = []

    @property
    def current_state(self) -> SimulationState:
        """Current mutable state (returned as a copy-like dataclass value)."""
        return replace(self._state)

    @property
    def model_config(self) -> ModelConfig:
        """Return the active model configuration."""
        return self._model_config

    @property
    def history(self) -> list[SimulationSnapshot]:
        """Simulation history as immutable snapshots."""
        return list(self._history)

    def get_estimator_trace(self) -> list[EstimatorTraceStep]:
        """Return recorded EKF prediction/update trace steps."""
        return list(self._estimator_trace)

    def export_snapshot(
        self,
        mode: str = "standard",
        bolus_description: str = "none",
    ) -> "SimulatorSnapshot":
        """Capture simulator state and covariance for later restore.

        Args:
            mode: Short label describing replay/prediction intent.
            bolus_description: Human-readable description of bolus inputs.
        """
        return SimulatorSnapshot(
            state=replace(self._state),
            estimator_covariance=self._estimator.covariance,
            history=list(self._history),
            mode=mode,
            bolus_description=bolus_description,
        )

    def restore_snapshot(self, snapshot: "SimulatorSnapshot") -> None:
        """Restore simulator state, estimator covariance, and history."""
        self._state = replace(snapshot.state)
        self._estimator.set_state(self._state)
        self._estimator.set_covariance(snapshot.estimator_covariance)
        self._pending.clear()
        self._history = list(snapshot.history)
        self._estimator_trace = []

    def queue_meal(self, carbs: float) -> None:
        """Queue meal carbohydrates to be applied at next step.

        Args:
            carbs: Carbohydrates in grams.

        Raises:
            ValueError: If carbs is not positive.
        """
        if carbs <= 0.0:
            raise ValueError("Meal carbs must be positive")
        self._pending.meal_carbs += carbs

    def queue_bolus(
        self, units: float, over_minutes: float | None = None
    ) -> None:
        """Queue an insulin bolus to be applied at the next step.

        Args:
            units: Insulin amount to administer (same units as state.insulin).
            over_minutes: If provided, distribute units as an infusion over
                this many minutes; if None apply as an instantaneous bolus.
        """
        bolus = BolusEvent(units=units, over_minutes=over_minutes)
        bolus.validate()
        self._pending.bolus_event = bolus

    def set_basal_rate(self, units_per_hour: float) -> None:
        """Store the active basal rate after converting from U/h.

        Args:
            units_per_hour: Basal delivery rate in pump units per hour.

        Raises:
            ValueError: If units_per_hour is negative.
        """
        if units_per_hour < 0.0:
            raise ValueError("units_per_hour must be non-negative")

        concentration_rate = (
            units_per_hour
            * self._model_config.unit_to_uu_per_ml
            / 60.0
        )
        self._state.basal_insulin_rate = concentration_rate

    def queue_sport(self, multiplier: float, duration_minutes: float) -> None:
        """Queue a temporary insulin-sensitivity boost event."""
        sport_event = SportEvent(
            multiplier=multiplier,
            duration_minutes=duration_minutes,
        )
        sport_event.validate()
        self._pending.sport_event = sport_event

    def reset(self) -> None:
        """Reset to initial state and clear pending events/history."""
        self._state = replace(self._initial_state)
        self._estimator.set_state(self._state)
        self._pending.clear()
        self._history = [self._to_snapshot(self._state)]
        self._estimator_trace = []

    def step(
        self,
        measured_interstitium: float | None = None,
        use_controller: bool = True,
    ) -> SimulationSnapshot:
        """Execute one deterministic step of the simulation pipeline."""
        return self._step(
            measured_interstitium=measured_interstitium,
            use_controller=use_controller,
            assimilate_measurement=True,
        )

    def step_replay(self, measured_interstitium: float) -> SimulationSnapshot:
        """Execute one replay step using an external CGM measurement."""
        return self._step(
            measured_interstitium=measured_interstitium,
            use_controller=False,
            assimilate_measurement=True,
        )

    def step_prediction(self) -> SimulationSnapshot:
        """Execute one open-loop prediction step without measurement data."""
        return self._step(
            measured_interstitium=None,
            use_controller=False,
            assimilate_measurement=False,
        )

    def _step(
        self,
        measured_interstitium: float | None,
        use_controller: bool,
        assimilate_measurement: bool,
    ) -> SimulationSnapshot:
        """Execute one deterministic step of the simulation pipeline."""
        self._apply_pending_events()
        self._estimator.set_state(self._state)
        predicted_state, transition, predicted_covariance = (
            self._estimator.predict_with_details(
                dt_minutes=self._model_config.dt_minutes,
                control_input=self._state.insulin_rate,
            )
        )
        if assimilate_measurement:
            if measured_interstitium is None:
                measured_interstitium = self._state.interstitium
            updated_state = self._estimator.update(measured_interstitium)
        else:
            updated_state = predicted_state
        updated_covariance = self._estimator.covariance

        estimate = self._estimator.current_state
        if use_controller:
            self._state.insulin_rate = self._controller.compute_insulin_rate(
                glucose=estimate.interstitium,
                current_rate=self._state.insulin_rate,
                config=self._controller_config,
            )
        # Merge estimator state but preserve any insulin_rate set by controller
        self._state = replace(estimate, insulin_rate=self._state.insulin_rate)
        self._estimator.set_state(self._state)

        self._estimator_trace.append(
            EstimatorTraceStep(
                predicted_state=predicted_state,
                predicted_covariance=predicted_covariance,
                updated_state=updated_state,
                updated_covariance=updated_covariance,
                transition=transition,
            )
        )

        snapshot = self._to_snapshot(self._state)
        self._history.append(snapshot)
        return snapshot

    def get_history_arrays(
        self,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """Return time series arrays for plotting."""
        time = [snapshot.time_minutes for snapshot in self._history]
        glucose = [snapshot.glucose for snapshot in self._history]
        insulin = [snapshot.insulin for snapshot in self._history]
        insulin_rate = [snapshot.insulin_rate for snapshot in self._history]
        return time, glucose, insulin, insulin_rate

    def _apply_pending_events(self) -> None:
        """Apply user events before controller and model integration."""
        if self._pending.meal_carbs > 0.0:
            self._state.carb_stomach += self._pending.meal_carbs

        if self._pending.sport_event is not None:
            sport_event = self._pending.sport_event
            self._state.sport_multiplier = max(
                self._state.sport_multiplier,
                sport_event.multiplier,
            )
            self._state.sport_minutes_remaining += sport_event.duration_minutes

        if self._pending.bolus_event is not None:
            bolus = self._pending.bolus_event
            unit_to_concentration = self._model_config.unit_to_uu_per_ml
            if bolus.over_minutes is None:
                frac = getattr(
                    self._model_config, "insulin_subq_fraction", 1.0
                )
                self._state.insulin_subcutaneous += (
                    bolus.units * unit_to_concentration * frac
                )
            else:
                # Short infusion: convert units over minutes to per-minute
                # input and keep a finite remaining duration so the rate
                # expires when the requested window ends.
                rate = (
                    bolus.units
                    * unit_to_concentration
                    / bolus.over_minutes
                )
                self._state.insulin_subq_rate += rate
                self._state.insulin_subq_minutes_remaining = max(
                    self._state.insulin_subq_minutes_remaining,
                    bolus.over_minutes,
                )

        # If there's an active short infusion rate, transfer the per-minute
        # delivered units into the subcutaneous depot over this dt, and
        # decrement the remaining infusion window.
        dt = self._model_config.dt_minutes
        if getattr(self._state, "insulin_subq_rate", 0.0) > 0.0:
            transfer = self._state.insulin_subq_rate * dt
            self._state.insulin_subcutaneous += transfer
            if getattr(self._state, "insulin_subq_minutes_remaining", 0.0) > 0.0:
                self._state.insulin_subq_minutes_remaining = max(
                    0.0, self._state.insulin_subq_minutes_remaining - dt
                )
            if self._state.insulin_subq_minutes_remaining <= 0.0:
                self._state.insulin_subq_rate = 0.0

        self._pending.clear()

    @staticmethod
    def _to_snapshot(state: SimulationState) -> SimulationSnapshot:
        """Convert mutable state to immutable history snapshot."""
        return SimulationSnapshot(
            time_minutes=state.time_minutes,
            glucose=state.glucose,
            insulin=state.insulin,
            insulin_subcutaneous=getattr(state, "insulin_subcutaneous", 0.0),
            insulin_subq_rate=getattr(state, "insulin_subq_rate", 0.0),
            insulin_subq_minutes_remaining=getattr(
                state, "insulin_subq_minutes_remaining", 0.0
            ),
            carb_stomach=state.carb_stomach,
            carb_intestine=state.carb_intestine,
            interstitium=state.interstitium,
            insulin_rate=state.insulin_rate,
            basal_insulin_rate=getattr(state, "basal_insulin_rate", 0.0),
            sport_multiplier=state.sport_multiplier,
            sport_minutes_remaining=state.sport_minutes_remaining,
        )


@dataclass(frozen=True)
class SimulatorSnapshot:
    """Exported runtime snapshot for restore after prediction runs."""

    state: SimulationState
    estimator_covariance: np.ndarray
    history: list[SimulationSnapshot]
    mode: str = "standard"
    bolus_description: str = "none"
