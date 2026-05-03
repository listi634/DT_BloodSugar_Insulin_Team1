"""Simulation orchestration for deterministic event/controller/model flow."""

from dataclasses import replace

from src.core.controller import ProportionalController
from src.core.model import PhysiologyModel
from src.core.state import ControllerConfig
from src.core.state import IntegratorConfig
from src.core.state import ModelConfig
from src.core.state import PendingEvents
from src.core.state import SimulationSnapshot
from src.core.state import SimulationState
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
        integrator_config: IntegratorConfig | None = None,
    ) -> None:
        """Create simulator with explicit dependencies and typed state."""
        model_config.validate()
        controller_config.validate()
        if initial_state.glucose < 0.0:
            raise ValueError("initial_state.glucose must be non-negative")
        if initial_state.insulin < 0.0:
            raise ValueError("initial_state.insulin must be non-negative")

        self._model = model
        if integrator_config is not None:
            self._model.set_integrator_config(integrator_config)
        self._controller = controller
        self._model_config = model_config
        self._controller_config = controller_config
        self._initial_state = replace(initial_state)
        self._state = replace(initial_state)
        self._pending = PendingEvents()
        self._history: list[SimulationSnapshot] = [
            self._to_snapshot(self._state)
        ]

    @property
    def current_state(self) -> SimulationState:
        """Current mutable state (returned as a copy-like dataclass value)."""
        return replace(self._state)

    @property
    def history(self) -> list[SimulationSnapshot]:
        """Simulation history as immutable snapshots."""
        return list(self._history)

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
        self._pending.clear()
        self._history = [self._to_snapshot(self._state)]

    def step(self) -> SimulationSnapshot:
        """Execute one deterministic step of the simulation pipeline."""
        self._apply_pending_events()
        self._state.insulin_rate = self._controller.compute_insulin_rate(
            glucose=self._state.interstitium,
            current_rate=self._state.insulin_rate,
            config=self._controller_config,
        )
        self._state = self._model.integrate(self._state, self._model_config)

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
            self._state.carb_pool += self._pending.meal_carbs

        if self._pending.sport_event is not None:
            sport_event = self._pending.sport_event
            self._state.sport_multiplier = max(
                self._state.sport_multiplier,
                sport_event.multiplier,
            )
            self._state.sport_minutes_remaining += sport_event.duration_minutes

        self._pending.clear()

    @staticmethod
    def _to_snapshot(state: SimulationState) -> SimulationSnapshot:
        """Convert mutable state to immutable history snapshot."""
        return SimulationSnapshot(
            time_minutes=state.time_minutes,
            glucose=state.glucose,
            insulin=state.insulin,
            interstitium=state.interstitium,
            insulin_rate=state.insulin_rate,
            carb_pool=state.carb_pool,
            sport_multiplier=state.sport_multiplier,
            sport_minutes_remaining=state.sport_minutes_remaining,
        )
