"""Physiology model for glucose-insulin dynamics."""

from src.core.state import ModelConfig
from src.core.state import SimulationState


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a scalar value to inclusive bounds."""
    return max(lower, min(value, upper))


class PhysiologyModel:
    """Low-order grey-box model with stable glucose-insulin coupling."""

    def integrate(
        self, state: SimulationState, config: ModelConfig
    ) -> SimulationState:
        """Integrate one simulation step using Euler forward integration.

        Args:
            state: Current physiological state.
            config: Model parameters and limits.

        Returns:
            The updated state after one time step.
        """
        config.validate()
        if state.glucose < 0.0:
            raise ValueError("state.glucose must be non-negative")
        if state.insulin < 0.0:
            raise ValueError("state.insulin must be non-negative")
        if state.carb_pool < 0.0:
            raise ValueError("state.carb_pool must be non-negative")
        if state.insulin_rate < 0.0:
            raise ValueError("state.insulin_rate must be non-negative")
        if state.sport_multiplier < 1.0:
            raise ValueError("state.sport_multiplier must be at least 1.0")
        if state.sport_minutes_remaining < 0.0:
            raise ValueError(
                "state.sport_minutes_remaining must be non-negative"
            )

        dt_minutes = config.dt_minutes
        insulin_effect = max(0.0, state.insulin - config.insulin_basal)
        glucose_effect = max(0.0, state.glucose - config.glucose_basal)

        sensitivity_multiplier = 1.0
        if state.sport_minutes_remaining > 0.0:
            sensitivity_multiplier = state.sport_multiplier

        effective_sensitivity = (
            config.insulin_sensitivity * sensitivity_multiplier
        )

        d_glucose = (
            -config.glucose_decay * (state.glucose - config.glucose_basal)
            - effective_sensitivity * insulin_effect
            + config.carb_to_glucose_gain * state.carb_pool
        )

        d_insulin = (
            -config.insulin_decay * (state.insulin - config.insulin_basal)
            + config.insulin_response_gain * glucose_effect
            + state.insulin_rate
        )

        d_carb_pool = -config.meal_absorption_rate * state.carb_pool

        next_glucose = _clamp(
            state.glucose + d_glucose * dt_minutes,
            config.min_glucose,
            config.max_glucose,
        )
        next_insulin = _clamp(
            state.insulin + d_insulin * dt_minutes,
            config.min_insulin,
            config.max_insulin,
        )
        next_carb_pool = max(0.0, state.carb_pool + d_carb_pool * dt_minutes)

        next_sport_remaining = max(
            0.0,
            state.sport_minutes_remaining - dt_minutes,
        )
        next_sport_multiplier = state.sport_multiplier
        if not next_sport_remaining:
            next_sport_multiplier = 1.0

        return SimulationState(
            time_minutes=state.time_minutes + dt_minutes,
            glucose=next_glucose,
            insulin=next_insulin,
            carb_pool=next_carb_pool,
            insulin_rate=state.insulin_rate,
            sport_multiplier=next_sport_multiplier,
            sport_minutes_remaining=next_sport_remaining,
        )
