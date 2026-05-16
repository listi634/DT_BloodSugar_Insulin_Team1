"""Typed state and configuration objects for the digital twin."""

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

IntegratorMethod = Literal["RK45", "DOP853", "BDF"]
IntegratorEvent = Callable[[float, object], float]


@dataclass(frozen=True)
class ModelConfig:
    """Physiology model parameters and safety bounds."""

    dt_minutes: float = 1.0
    plasma_volume_ml: float = 12000.0
    glucose_basal: float = 5.0
    insulin_basal: float = 0.0
    glucose_decay: float = 0.015
    insulin_decay: float = 0.1
    insulin_sensitivity: float = 0.0006
    insulin_response_gain: float = 0.32
    stomach_tau_minutes: float = 18.0
    intestine_tau_minutes: float = 40.0
    carb_to_glucose_gain: float = 0.0015
    interstitium_tau_minutes: float = 8.0
    insulin_subq_fraction: float = 1.0
    insulin_subq_absorption_tau_minutes: float = 30.0
    min_glucose: float = 1.0
    max_glucose: float = 20.0
    min_insulin: float = 0.0
    max_insulin: float = 300.0

    def validate(self) -> None:
        """Validate model parameters for physically meaningful values."""
        if self.dt_minutes <= 0.0:
            raise ValueError("dt_minutes must be positive")
        if self.plasma_volume_ml <= 0.0:
            raise ValueError("plasma_volume_ml must be positive")
        if self.glucose_basal <= 0.0:
            raise ValueError("glucose_basal must be positive")
        if self.insulin_basal < 0.0:
            raise ValueError("insulin_basal must be non-negative")
        if self.stomach_tau_minutes <= 0.0:
            raise ValueError("stomach_tau_minutes must be positive")
        if self.intestine_tau_minutes <= 0.0:
            raise ValueError("intestine_tau_minutes must be positive")
        if self.interstitium_tau_minutes <= 0.0:
            raise ValueError("interstitium_tau_minutes must be positive")
        if self.insulin_subq_absorption_tau_minutes <= 0.0:
            raise ValueError(
                "insulin_subq_absorption_tau_minutes must be positive"
            )
        if self.min_glucose >= self.max_glucose:
            raise ValueError("min_glucose must be lower than max_glucose")
        if self.min_insulin >= self.max_insulin:
            raise ValueError("min_insulin must be lower than max_insulin")

    @property
    def unit_to_uu_per_ml(self) -> float:
        """Return the plasma-concentration scaling for one insulin unit."""
        return 1_000_000.0 / self.plasma_volume_ml


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration for proportional insulin automation."""

    target_glucose: float = 5.5
    proportional_gain: float = 0.5
    deadband: float = 0.15
    max_insulin_rate: float = 2.0
    max_rate_delta_per_step: float = 0.15

    def validate(self) -> None:
        """Validate controller tuning and safety limits."""
        if self.target_glucose <= 0.0:
            raise ValueError("target_glucose must be positive")
        if self.proportional_gain < 0.0:
            raise ValueError("proportional_gain must be non-negative")
        if self.deadband < 0.0:
            raise ValueError("deadband must be non-negative")
        if self.max_insulin_rate <= 0.0:
            raise ValueError("max_insulin_rate must be positive")
        if self.max_rate_delta_per_step <= 0.0:
            raise ValueError("max_rate_delta_per_step must be positive")


@dataclass(frozen=True)
class EstimatorConfig:
    """Configuration for the EKF state estimator scaffold."""

    initial_covariance: float = 1.0
    process_noise_scale: float = 0.02
    insulin_process_noise: float | None = None
    measurement_noise_variance: float = 0.09
    finite_difference_step: float = 1e-4
    minimum_covariance: float = 1e-6

    def validate(self) -> None:
        """Validate covariance and noise settings."""
        if self.initial_covariance <= 0.0:
            raise ValueError("initial_covariance must be positive")
        if self.process_noise_scale < 0.0:
            raise ValueError("process_noise_scale must be non-negative")
        if (
            self.insulin_process_noise is not None
            and self.insulin_process_noise < 0.0
        ):
            raise ValueError("insulin_process_noise must be non-negative")
        if self.measurement_noise_variance <= 0.0:
            raise ValueError("measurement_noise_variance must be positive")
        if self.finite_difference_step <= 0.0:
            raise ValueError("finite_difference_step must be positive")
        if self.minimum_covariance <= 0.0:
            raise ValueError("minimum_covariance must be positive")


@dataclass(frozen=True)
class IntegratorConfig:
    """Configuration for one-step ODE integration with solve_ivp."""

    method: IntegratorMethod = "RK45"
    rtol: float = 1e-6
    atol: float = 1e-8
    max_step: float | None = None
    dense_output: bool = False
    events: Sequence[IntegratorEvent] | None = None

    def validate(self) -> None:
        """Validate solver configuration and supported methods."""
        supported_methods = {"RK45", "DOP853", "BDF"}
        if self.method not in supported_methods:
            raise ValueError("method must be one of RK45, DOP853, or BDF")
        if self.rtol <= 0.0:
            raise ValueError("rtol must be positive")
        if self.atol <= 0.0:
            raise ValueError("atol must be positive")
        if self.max_step is not None and self.max_step <= 0.0:
            raise ValueError("max_step must be positive when provided")


@dataclass(frozen=True)
class BolusEvent:
    """Discrete or short infusion insulin administration request.

    Attributes:
        units: Insulin amount in pump units (U).
        over_minutes: If provided, distribute `units` as a continuous
            infusion over this many minutes; if `None` treat as an
            instantaneous subcutaneous bolus.
    """

    units: float
    over_minutes: float | None = None

    def validate(self) -> None:
        """Validate bolus values."""
        if self.units <= 0.0:
            raise ValueError("bolus units must be positive")
        if self.over_minutes is not None and self.over_minutes <= 0.0:
            raise ValueError("over_minutes must be positive when provided")


@dataclass
class PendingEvents:
    """Buffered user events to apply at the next simulation step."""

    meal_carbs: float = 0.0
    bolus_event: BolusEvent | None = None

    def clear(self) -> None:
        """Clear all pending inputs after event application."""
        self.meal_carbs = 0.0
        self.bolus_event = None


@dataclass
class SimulationState:
    """Continuous system state used by the model integrator."""

    time_minutes: float
    glucose: float
    insulin: float
    carb_stomach: float
    carb_intestine: float
    interstitium: float
    insulin_rate: float
    insulin_subcutaneous: float = 0.0
    insulin_subq_rate: float = 0.0
    insulin_subq_minutes_remaining: float = 0.0
    basal_insulin_rate: float = 0.0


@dataclass(frozen=True)
class SimulationSnapshot:
    """Immutable history row for plotting and analysis."""

    time_minutes: float
    glucose: float
    insulin: float
    carb_stomach: float
    carb_intestine: float
    interstitium: float
    insulin_rate: float
    insulin_subcutaneous: float = 0.0
    insulin_subq_rate: float = 0.0
    insulin_subq_minutes_remaining: float = 0.0
    basal_insulin_rate: float = 0.0
