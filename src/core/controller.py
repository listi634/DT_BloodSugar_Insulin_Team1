"""Controller logic for automated insulin dosing."""

from src.core.state import ControllerConfig


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a scalar value to inclusive bounds."""
    return max(lower, min(value, upper))


class ProportionalController:
    """Simple proportional controller with anti-overreaction limits."""

    def compute_insulin_rate(
        self,
        glucose: float,
        current_rate: float,
        config: ControllerConfig,
    ) -> float:
        """Compute the next insulin command from current glucose.

        Args:
            glucose: Current glucose concentration in mmol/L.
            current_rate: Previous insulin infusion rate.
            config: Controller tuning and safety parameters.

        Returns:
            Next insulin infusion rate.
        """
        config.validate()
        if glucose < 0.0:
            raise ValueError("glucose must be non-negative")
        if current_rate < 0.0:
            raise ValueError("current_rate must be non-negative")

        error = glucose - config.target_glucose
        if error <= config.deadband:
            desired_rate = 0.0
        else:
            desired_rate = config.proportional_gain * error

        desired_rate = _clamp(desired_rate, 0.0, config.max_insulin_rate)
        lower = max(0.0, current_rate - config.max_rate_delta_per_step)
        upper = min(
            config.max_insulin_rate,
            current_rate + config.max_rate_delta_per_step,
        )
        return _clamp(desired_rate, lower, upper)
