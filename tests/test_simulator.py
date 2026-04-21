"""Tests for simulation orchestration and event flow."""

from src.core.controller import ProportionalController
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def _build_simulator() -> GlucoseSimulator:
    """Create a simulator fixture with deterministic defaults."""
    model_config = ModelConfig()
    controller_config = ControllerConfig(
        target_glucose=5.5,
        proportional_gain=0.8,
        max_insulin_rate=2.0,
        max_rate_delta_per_step=0.3,
    )
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=model_config.glucose_basal,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    return GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
    )


def test_event_then_control_then_integrate_order() -> None:
    """First step should apply meal before integration but after control decision."""
    simulator = _build_simulator()
    simulator.queue_meal(60.0)

    first = simulator.step()
    second = simulator.step()

    assert first.glucose > 5.0
    assert first.insulin_rate == 0.0
    assert second.insulin_rate > 0.0


def test_sport_event_applies_temporary_sensitivity_boost() -> None:
    """Sport event should set multiplier and count down each step."""
    simulator = _build_simulator()
    simulator.queue_sport(multiplier=1.5, duration_minutes=30.0)

    snapshot = simulator.step()

    assert snapshot.sport_multiplier == 1.5
    assert snapshot.sport_minutes_remaining == 29.0


def test_reset_restores_initial_state_and_history() -> None:
    """Reset should clear progress while preserving initial snapshot."""
    simulator = _build_simulator()
    simulator.queue_meal(50.0)
    simulator.step()
    simulator.step()

    simulator.reset()

    assert len(simulator.history) == 1
    assert simulator.current_state.time_minutes == 0.0
    assert simulator.current_state.carb_pool == 0.0
