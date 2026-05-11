"""Tests for simulation orchestration and event flow."""

from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import EstimatorConfig
from src.core.state import ControllerConfig
from src.core.state import IntegratorConfig
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
        interstitium=model_config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    estimator = ExtendedKalmanFilterEstimator(
        model=PhysiologyModel(),
        model_config=model_config,
        initial_state=initial_state,
        estimator_config=EstimatorConfig(),
    )
    return GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
        estimator=estimator,
    )


def test_event_then_control_then_integrate_order() -> None:
    """Meal input should affect the next step before control reacts."""
    simulator = _build_simulator()
    simulator.queue_meal(120.0)

    first = simulator.step(measured_interstitium=5.0)
    assert first.glucose > 5.0
    assert first.insulin_rate == 0.0

    for _ in range(10):
        simulator.step(measured_interstitium=5.0)

    final = simulator.history[-1]
    assert final.glucose > first.glucose
    assert final.carb_pool > 0.0


def test_sport_event_applies_temporary_sensitivity_boost() -> None:
    """Sport event should set multiplier and count down each step."""
    simulator = _build_simulator()
    simulator.queue_sport(multiplier=1.5, duration_minutes=30.0)

    snapshot = simulator.step(measured_interstitium=5.0)

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


def test_simulator_accepts_explicit_integrator_config() -> None:
    """Simulator should pass chosen integrator settings into model."""
    model_config = ModelConfig()
    controller_config = ControllerConfig()
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=model_config.glucose_basal,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        interstitium=model_config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    simulator = GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
        integrator_config=IntegratorConfig(method="DOP853"),
    )

    snapshot = simulator.step()

    assert snapshot.time_minutes == model_config.dt_minutes


def test_controller_reads_interstitium_not_plasma_glucose() -> None:
    """Controller should base insulin decisions on interstitial glucose."""
    model_config = ModelConfig()
    controller_config = ControllerConfig(
        target_glucose=5.5,
        proportional_gain=1.0,
        deadband=0.0,
        max_insulin_rate=5.0,
    )
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=10.0,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        interstitium=5.5,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    simulator = GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
    )

    snapshot = simulator.step(measured_interstitium=5.5)

    assert snapshot.insulin_rate < 0.1


def test_measurement_input_keeps_meal_replay_available() -> None:
    """Explicit measurements should not interfere with queued meal replay."""
    simulator = _build_simulator()
    simulator.queue_meal(20.0)

    snapshot = simulator.step(measured_interstitium=6.0)

    assert snapshot.time_minutes == ModelConfig().dt_minutes
    assert snapshot.carb_pool > 0.0


def test_validation_mode_accepts_step_local_external_insulin() -> None:
    """Replay insulin input should apply only to the current validation step."""
    validation_simulator = GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=ModelConfig(),
        controller_config=ControllerConfig(),
        initial_state=SimulationState(
            time_minutes=0.0,
            glucose=ModelConfig().glucose_basal,
            insulin=ModelConfig().insulin_basal,
            carb_pool=0.0,
            interstitium=ModelConfig().glucose_basal,
            insulin_rate=0.0,
            sport_multiplier=1.0,
            sport_minutes_remaining=0.0,
        ),
        validation_mode=True,
    )

    snapshot = validation_simulator.step(
        measured_interstitium=5.0,
        external_insulin_rate=1.25,
    )
    next_snapshot = validation_simulator.step(measured_interstitium=5.0)

    assert snapshot.insulin_rate == 1.25
    assert next_snapshot.insulin_rate == 0.0
