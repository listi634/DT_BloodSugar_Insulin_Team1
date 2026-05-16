"""Open-loop prediction utilities for the digital twin simulator."""

from dataclasses import dataclass
from dataclasses import replace
from math import ceil

from src.core.simulator import GlucoseSimulator


@dataclass(frozen=True)
class PredictionScenario:
    """Scenario inputs for a future what-if prediction."""

    horizon_minutes: float = 120.0
    meal_carbs: float = 0.0
    bolus_units: float = 0.0

    def validate(self) -> None:
        """Validate the requested what-if scenario."""
        if self.horizon_minutes <= 0.0:
            raise ValueError("horizon_minutes must be positive")
        if self.meal_carbs < 0.0:
            raise ValueError("meal_carbs must be non-negative")
        if self.bolus_units < 0.0:
            raise ValueError("bolus_units must be non-negative")


@dataclass(frozen=True)
class PredictionResult:
    """Trajectory produced by an open-loop forecast run."""

    time_minutes: list[float]
    glucose: list[float]
    insulin: list[float]
    interstitium: list[float]
    scenario: PredictionScenario


def run_open_loop_prediction(
    simulator: GlucoseSimulator,
    scenario: PredictionScenario,
) -> PredictionResult:
    """Run an open-loop forecast without changing the live simulator.

    Args:
        simulator: Active simulator instance to forecast from.
        scenario: Forecast horizon and optional scenario inputs.

    Returns:
        A typed trajectory with absolute time stamps and predicted states.

    Raises:
        ValueError: If the forecast scenario is invalid.
    """
    scenario.validate()
    snapshot = simulator.export_snapshot(mode="prediction")
    try:
        if scenario.meal_carbs > 0.0:
            simulator.queue_meal(scenario.meal_carbs)
        if scenario.bolus_units > 0.0:
            simulator.queue_bolus(scenario.bolus_units)

        current_state = simulator.current_state
        time_minutes = [current_state.time_minutes]
        glucose = [current_state.glucose]
        insulin = [current_state.insulin]
        interstitium = [current_state.interstitium]

        dt_minutes = simulator.model_config.dt_minutes
        steps = max(1, int(ceil(scenario.horizon_minutes / dt_minutes)))
        for _ in range(steps):
            simulator.step_prediction()
            predicted_state = simulator.current_state
            time_minutes.append(predicted_state.time_minutes)
            glucose.append(predicted_state.glucose)
            insulin.append(predicted_state.insulin)
            interstitium.append(predicted_state.interstitium)

        return PredictionResult(
            time_minutes=time_minutes,
            glucose=glucose,
            insulin=insulin,
            interstitium=interstitium,
            scenario=replace(scenario),
        )
    finally:
        simulator.restore_snapshot(snapshot)
