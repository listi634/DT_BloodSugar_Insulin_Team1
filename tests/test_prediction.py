"""Tests for open-loop forecast behavior."""

from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.prediction import PredictionScenario
from src.core.prediction import run_open_loop_prediction
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import EstimatorConfig
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


def test_prediction_restores_live_simulator_state() -> None:
    """Forecasting should not mutate the live simulator state."""
    simulator = _build_simulator()
    before_state = simulator.current_state
    before_history_len = len(simulator.history)

    result = run_open_loop_prediction(
        simulator,
        PredictionScenario(horizon_minutes=30.0),
    )

    assert result.time_minutes[0] == before_state.time_minutes
    assert simulator.current_state == before_state
    assert len(simulator.history) == before_history_len


def test_prediction_reflects_meal_and_bolus_inputs() -> None:
    """Scenario inputs should change the forecast trajectory."""
    baseline_simulator = _build_simulator()
    scenario = PredictionScenario(horizon_minutes=60.0)
    baseline = run_open_loop_prediction(baseline_simulator, scenario)

    scenario_simulator = _build_simulator()
    with_inputs = run_open_loop_prediction(
        scenario_simulator,
        PredictionScenario(
            horizon_minutes=60.0,
            meal_carbs=45.0,
            bolus_units=2.0,
        ),
    )

    assert len(with_inputs.time_minutes) == len(baseline.time_minutes)
    assert with_inputs.glucose != baseline.glucose
    assert with_inputs.insulin != baseline.insulin


def test_prediction_horizon_scales_with_time_step() -> None:
    """Forecast length should follow the configured horizon."""
    simulator = _build_simulator()

    result = run_open_loop_prediction(
        simulator,
        PredictionScenario(horizon_minutes=15.0),
    )

    assert result.time_minutes[0] == 0.0
    assert result.time_minutes[-1] >= 15.0
    assert len(result.time_minutes) == 16