"""Tests for the EKF state estimator scaffold."""

import pytest

from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.state import EstimatorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def _build_estimator() -> ExtendedKalmanFilterEstimator:
    """Create an estimator fixture with deterministic defaults."""
    model_config = ModelConfig()
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=7.0,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        interstitium=7.0,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    return ExtendedKalmanFilterEstimator(
        model=PhysiologyModel(),
        model_config=model_config,
        initial_state=initial_state,
        estimator_config=EstimatorConfig(
            initial_covariance=1.0,
            process_noise_scale=0.01,
            measurement_noise_variance=0.04,
        ),
    )


def test_predict_advances_state_and_covariance() -> None:
    """Prediction should move the estimate forward and stay finite."""
    estimator = _build_estimator()

    next_state = estimator.predict(dt_minutes=1.0, control_input=0.2)

    assert next_state.time_minutes == pytest.approx(1.0)
    assert next_state.interstitium != pytest.approx(7.0)
    covariance = estimator.covariance
    assert covariance.shape == (4, 4)
    assert covariance[0, 0] > 0.0


def test_update_moves_interstitium_toward_measurement() -> None:
    """Measurement correction should pull the estimate toward data."""
    estimator = _build_estimator()
    estimator.predict(dt_minutes=1.0, control_input=0.0)

    before = estimator.current_state.interstitium
    corrected = estimator.update(measured_interstitium=9.0)

    assert corrected.interstitium > before
    assert corrected.interstitium == pytest.approx(
        estimator.current_state.interstitium
    )
    assert estimator.covariance[3, 3] < 1.0


def test_update_rejects_negative_measurements() -> None:
    """Filter inputs should reject invalid measured glucose values."""
    estimator = _build_estimator()

    with pytest.raises(ValueError, match="measured_interstitium"):
        estimator.update(measured_interstitium=-1.0)