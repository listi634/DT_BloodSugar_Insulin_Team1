"""Tests for proportional insulin controller behavior."""

from src.core.controller import ProportionalController
from src.core.state import ControllerConfig


def test_controller_returns_zero_near_target() -> None:
    """Controller should not dose when glucose is inside deadband."""
    controller = ProportionalController()
    config = ControllerConfig(target_glucose=5.5, deadband=0.2)

    rate = controller.compute_insulin_rate(
        glucose=5.6,
        current_rate=0.0,
        config=config,
    )

    assert rate == 0.0


def test_controller_clamps_to_max_rate() -> None:
    """Controller output should respect max insulin rate."""
    controller = ProportionalController()
    config = ControllerConfig(
        target_glucose=5.0,
        proportional_gain=5.0,
        max_insulin_rate=1.0,
        max_rate_delta_per_step=5.0,
    )

    rate = controller.compute_insulin_rate(
        glucose=20.0,
        current_rate=0.0,
        config=config,
    )

    assert rate == 1.0


def test_controller_rate_change_is_limited() -> None:
    """Controller should limit per-step command jumps."""
    controller = ProportionalController()
    config = ControllerConfig(
        target_glucose=5.0,
        proportional_gain=2.0,
        max_insulin_rate=5.0,
        max_rate_delta_per_step=0.25,
    )

    rate = controller.compute_insulin_rate(
        glucose=12.0,
        current_rate=0.0,
        config=config,
    )

    assert rate == 0.25
