"""Physiology model for glucose-insulin dynamics."""

import numpy as np

from src.core.integrator import SolveIvPIntegrator
from src.core.state import IntegratorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a scalar value to inclusive bounds."""
    return max(lower, min(value, upper))


class PhysiologyModel:
    """Low-order grey-box model with stable glucose-insulin coupling."""

    def __init__(
        self,
        integrator: SolveIvPIntegrator | None = None,
        integrator_config: IntegratorConfig | None = None,
    ) -> None:
        """Create model with configurable continuous-time integrator."""
        self._integrator = integrator or SolveIvPIntegrator()
        self._integrator_config = integrator_config or IntegratorConfig()
        self._integrator_config.validate()

    def set_integrator_config(
        self,
        integrator_config: IntegratorConfig,
    ) -> None:
        """Replace integrator settings used for subsequent model steps."""
        integrator_config.validate()
        self._integrator_config = integrator_config

    def _derivative(
        self,
        _time_minutes: float,
        values: np.ndarray,
        config: ModelConfig,
        sensitivity_multiplier: float,
        insulin_rate: float,
    ) -> np.ndarray:
        """Compute continuous-time state derivatives for solve_ivp.

        State vector: [glucose, insulin, carb_stomach, carb_intestine,
                       interstitium, insulin_subcutaneous]
        """
        glucose = float(values[0])
        insulin = float(values[1])
        carb_stomach = float(values[2])
        carb_intestine = float(values[3])
        interstitium = float(values[4])
        insulin_subcutaneous = float(values[5])

        insulin_effect = max(0.0, insulin - config.insulin_basal)
        glucose_effect = max(0.0, glucose - config.glucose_basal)
        effective_sensitivity = (
            config.insulin_sensitivity * sensitivity_multiplier
        )

        # Glucose dynamics: decay, insulin suppression, carb absorption
        d_glucose = (
            -config.glucose_decay * (glucose - config.glucose_basal)
            - effective_sensitivity * insulin_effect
            + config.carb_to_glucose_gain * carb_intestine
        )

        # Insulin dynamics: decay, pancreatic response, exogenous infusion
        d_insulin = (
            -config.insulin_decay * (insulin - config.insulin_basal)
            + config.insulin_response_gain * glucose_effect
            + insulin_rate
        )

        # Absorption from subcutaneous depot into plasma insulin
        absorption_rate = (
            insulin_subcutaneous / config.insulin_subq_absorption_tau_minutes
        )
        d_insulin += absorption_rate

        # Two-compartment meal absorption: stomach -> intestine -> glucose
        d_carb_stomach = -(1.0 / config.stomach_tau_minutes) * carb_stomach
        d_carb_intestine = (
            1.0 / config.stomach_tau_minutes
        ) * carb_stomach - (
            1.0 / config.intestine_tau_minutes
        ) * carb_intestine

        # Interstitium dynamics: diffusion from blood glucose
        d_interstitium = (
            glucose - interstitium
        ) / config.interstitium_tau_minutes

        d_insulin_subcutaneous = -absorption_rate

        return np.array(
            [
                d_glucose,
                d_insulin,
                d_carb_stomach,
                d_carb_intestine,
                d_interstitium,
                d_insulin_subcutaneous,
            ],
            dtype=float,
        )

    def integrate(
        self, state: SimulationState, config: ModelConfig
    ) -> SimulationState:
        """Integrate one simulation step using solve_ivp over [t, t+dt].

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
        if state.carb_stomach < 0.0:
            raise ValueError("state.carb_stomach must be non-negative")
        if state.carb_intestine < 0.0:
            raise ValueError("state.carb_intestine must be non-negative")
        if state.interstitium < 0.0:
            raise ValueError("state.interstitium must be non-negative")
        if state.insulin_rate < 0.0:
            raise ValueError("state.insulin_rate must be non-negative")
        if state.sport_multiplier < 1.0:
            raise ValueError("state.sport_multiplier must be at least 1.0")
        if state.sport_minutes_remaining < 0.0:
            raise ValueError(
                "state.sport_minutes_remaining must be non-negative"
            )

        dt_minutes = config.dt_minutes

        sensitivity_multiplier = 1.0
        if state.sport_minutes_remaining > 0.0:
            sensitivity_multiplier = state.sport_multiplier

        initial_values = np.array(
            [
                state.glucose,
                state.insulin,
                state.carb_stomach,
                state.carb_intestine,
                state.interstitium,
                state.insulin_subcutaneous,
            ],
            dtype=float,
        )
        next_values, _ = self._integrator.integrate_step(
            derivative=lambda time_minutes, values: self._derivative(
                time_minutes,
                values,
                config,
                sensitivity_multiplier,
                state.insulin_rate,
            ),
            y0=initial_values,
            t0=state.time_minutes,
            dt=dt_minutes,
            config=self._integrator_config,
        )

        next_glucose = _clamp(
            float(next_values[0]),
            config.min_glucose,
            config.max_glucose,
        )
        next_insulin = _clamp(
            float(next_values[1]),
            config.min_insulin,
            config.max_insulin,
        )
        next_carb_stomach = max(0.0, float(next_values[2]))
        next_carb_intestine = max(0.0, float(next_values[3]))
        next_interstitium = _clamp(
            float(next_values[4]),
            config.min_glucose,
            config.max_glucose,
        )
        next_insulin_subcutaneous = max(0.0, float(next_values[5]))

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
            insulin_subcutaneous=next_insulin_subcutaneous,
            carb_stomach=next_carb_stomach,
            carb_intestine=next_carb_intestine,
            interstitium=next_interstitium,
            insulin_rate=state.insulin_rate,
            insulin_subq_rate=state.insulin_subq_rate,
            insulin_subq_minutes_remaining=state.insulin_subq_minutes_remaining,
            sport_multiplier=next_sport_multiplier,
            sport_minutes_remaining=next_sport_remaining,
        )
