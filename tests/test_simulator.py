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
        carb_stomach=0.0,
        carb_intestine=0.0,
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
    assert final.carb_stomach + final.carb_intestine > 0.0


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
    assert simulator.current_state.carb_stomach == 0.0
    assert simulator.current_state.carb_intestine == 0.0


def test_simulator_accepts_explicit_integrator_config() -> None:
    """Simulator should pass chosen integrator settings into model."""
    model_config = ModelConfig()
    controller_config = ControllerConfig()
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=model_config.glucose_basal,
        insulin=model_config.insulin_basal,
        carb_stomach=0.0,
        carb_intestine=0.0,
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
        carb_stomach=0.0,
        carb_intestine=0.0,
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
    assert snapshot.carb_stomach + snapshot.carb_intestine > 0.0


def test_step_without_controller_keeps_insulin_rate() -> None:
    """Controller can be disabled for replay/inference steps."""
    simulator = _build_simulator()

    snapshot = simulator.step(measured_interstitium=5.0, use_controller=False)

    assert snapshot.insulin_rate == 0.0


def test_bolus_event_increases_insulin_state() -> None:
    """Queued bolus should raise insulin state or infusion rate."""
    simulator = _build_simulator()
    baseline = simulator.current_state.insulin

    simulator.queue_bolus(units=5.0)
    snapshot = simulator.step()

    assert snapshot.insulin > baseline


def test_bolus_is_subcutaneous_not_instant_plasma() -> None:
    """Bolus should be stored subcutaneously and not instantly spike plasma.

    This guards against applying bolus units directly to `insulin`.
    """
    simulator_no_bolus = _build_simulator()
    simulator_bolus = _build_simulator()

    # Apply meal only to both
    simulator_no_bolus.queue_meal(45.0)
    simulator_bolus.queue_meal(45.0)

    # Baseline insulin values
    baseline = simulator_bolus.current_state.insulin

    # Apply bolus to the second simulator
    simulator_bolus.queue_bolus(units=3.4)

    snap_no = simulator_no_bolus.step(measured_interstitium=5.0, use_controller=False)
    snap_b = simulator_bolus.step(measured_interstitium=5.0, use_controller=False)

    # The immediate plasma insulin increase should be much smaller than the
    # direct plasma-equivalent injection that the bolus would imply.
    increase = snap_b.insulin - baseline
    expected_direct = (
        3.4 * simulator_bolus.model_config.unit_to_uu_per_ml
    )
    assert increase < 0.1 * expected_direct
    # The subcutaneous depot should contain the bolus (or infusion transferred)
    assert getattr(simulator_bolus.current_state, "insulin_subcutaneous", 0.0) > 0.0


def test_basal_rate_is_converted_into_model_input() -> None:
    """Basal delivery should act as a persistent rate, not an impulse."""
    simulator = _build_simulator()
    baseline = simulator.current_state.insulin

    simulator.set_basal_rate(1.2)
    snapshot = simulator.step(measured_interstitium=5.0, use_controller=False)

    assert snapshot.basal_insulin_rate > 0.0
    assert snapshot.insulin > baseline
