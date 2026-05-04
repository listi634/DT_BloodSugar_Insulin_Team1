"""Extended Kalman filter scaffold for glucose state correction."""

from dataclasses import replace

import numpy as np

from src.core.model import PhysiologyModel
from src.core.state import EstimatorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


class ExtendedKalmanFilterEstimator:
    """Estimate the continuous simulator state from interstitial glucose."""

    def __init__(
        self,
        model: PhysiologyModel,
        model_config: ModelConfig,
        initial_state: SimulationState,
        estimator_config: EstimatorConfig | None = None,
    ) -> None:
        """Create estimator with validated model and initial state."""
        model_config.validate()
        config = estimator_config or EstimatorConfig()
        config.validate()
        self._validate_state(initial_state)

        self._model = model
        self._model_config = model_config
        self._config = config
        self._state = replace(initial_state)
        self._covariance = np.eye(4, dtype=float) * config.initial_covariance

    @property
    def current_state(self) -> SimulationState:
        """Return the current corrected state estimate."""
        return replace(self._state)

    @property
    def covariance(self) -> np.ndarray:
        """Return a copy of the EKF covariance matrix."""
        return self._covariance.copy()

    def set_covariance(self, covariance: np.ndarray) -> None:
        """Replace the EKF covariance matrix with validated input."""
        if covariance.shape != (4, 4):
            raise ValueError("covariance must be a 4x4 matrix")
        if not np.isfinite(covariance).all():
            raise ValueError("covariance must contain finite values")
        self._covariance = covariance.copy()

    def set_state(self, state: SimulationState) -> None:
        """Replace the internal state estimate without changing covariance."""
        self._validate_state(state)
        self._state = replace(state)

    def predict(
        self,
        dt_minutes: float,
        control_input: float,
    ) -> SimulationState:
        """Advance the state estimate with the process model."""
        if dt_minutes <= 0.0:
            raise ValueError("dt_minutes must be positive")
        if control_input < 0.0:
            raise ValueError("control_input must be non-negative")

        step_config = replace(self._model_config, dt_minutes=dt_minutes)
        prior_state = replace(self._state, insulin_rate=control_input)
        predicted_state = self._model.integrate(prior_state, step_config)
        transition = self._state_transition_jacobian(
            prior_state,
            step_config,
            control_input,
            predicted_state,
        )
        process_noise = self._process_noise_covariance()
        self._covariance = (
            transition @ self._covariance @ transition.T + process_noise
        )
        self._symmetrize_covariance()
        self._state = predicted_state
        return replace(self._state)

    def update(self, measured_interstitium: float) -> SimulationState:
        """Correct the estimate with a measured interstitial glucose value."""
        if measured_interstitium < 0.0:
            raise ValueError("measured_interstitium must be non-negative")

        state_vector = self._state_to_vector(self._state)
        innovation = measured_interstitium - state_vector[3]
        observation = np.zeros((1, 4), dtype=float)
        observation[0, 3] = 1.0
        innovation_covariance = (
            observation @ self._covariance @ observation.T
            + np.array(
                [[self._config.measurement_noise_variance]],
                dtype=float,
            )
        )
        innovation_scale = float(innovation_covariance[0, 0])
        if innovation_scale <= 0.0:
            raise ValueError("Innovation covariance must be positive")

        kalman_gain = self._covariance @ observation.T / innovation_scale
        updated_vector = state_vector + kalman_gain.flatten() * innovation

        updated_covariance = (
            np.eye(4, dtype=float) - kalman_gain @ observation
        ) @ self._covariance
        updated_covariance += (
            kalman_gain
            * self._config.measurement_noise_variance
            @ kalman_gain.T
        )

        self._state = self._vector_to_state(updated_vector, self._state)
        self._state = self._clamp_state(self._state)
        self._covariance = updated_covariance
        self._symmetrize_covariance()
        return replace(self._state)

    @staticmethod
    def _validate_state(state: SimulationState) -> None:
        """Reject invalid initial states before the filter starts."""
        if state.time_minutes < 0.0:
            raise ValueError("state.time_minutes must be non-negative")
        if state.glucose < 0.0:
            raise ValueError("state.glucose must be non-negative")
        if state.insulin < 0.0:
            raise ValueError("state.insulin must be non-negative")
        if state.carb_pool < 0.0:
            raise ValueError("state.carb_pool must be non-negative")
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

    def _state_transition_jacobian(
        self,
        state: SimulationState,
        step_config: ModelConfig,
        control_input: float,
        baseline: SimulationState,
    ) -> np.ndarray:
        """Estimate the linearized transition matrix by finite differences."""
        baseline_vector = self._state_to_vector(baseline)
        jacobian = np.zeros((4, 4), dtype=float)
        state_vector = self._state_to_vector(state)

        for index in range(4):
            perturbation = max(
                self._config.finite_difference_step,
                abs(state_vector[index]) * 1e-4,
            )
            perturbed_vector = state_vector.copy()
            perturbed_vector[index] += perturbation
            perturbed_state = self._vector_to_state(perturbed_vector, state)
            perturbed_state = replace(
                perturbed_state,
                insulin_rate=control_input,
            )
            perturbed_result = self._model.integrate(
                perturbed_state,
                step_config,
            )
            jacobian[:, index] = (
                self._state_to_vector(perturbed_result) - baseline_vector
            ) / perturbation

        return jacobian

    def _process_noise_covariance(self) -> np.ndarray:
        """Build a diagonal process noise matrix with safe defaults."""
        scale = self._config.process_noise_scale
        return np.eye(4, dtype=float) * scale

    def _symmetrize_covariance(self) -> None:
        """Keep covariance symmetric and numerically well-behaved."""
        self._covariance = 0.5 * (self._covariance + self._covariance.T)
        diagonal = np.diag(self._covariance)
        minimum = self._config.minimum_covariance
        diagonal = np.maximum(diagonal, minimum)
        np.fill_diagonal(self._covariance, diagonal)

    @staticmethod
    def _state_to_vector(state: SimulationState) -> np.ndarray:
        """Convert the continuous state subset to a numeric vector."""
        return np.array(
            [
                state.glucose,
                state.insulin,
                state.carb_pool,
                state.interstitium,
            ],
            dtype=float,
        )

    @staticmethod
    def _vector_to_state(
        vector: np.ndarray,
        template: SimulationState,
    ) -> SimulationState:
        """Convert a numeric vector back into the simulator state shape."""
        return replace(
            template,
            glucose=float(vector[0]),
            insulin=float(vector[1]),
            carb_pool=max(0.0, float(vector[2])),
            interstitium=float(vector[3]),
        )

    def _clamp_state(self, state: SimulationState) -> SimulationState:
        """Project corrected values back into physiological bounds."""
        return replace(
            state,
            glucose=max(
                self._model_config.min_glucose,
                min(state.glucose, self._model_config.max_glucose),
            ),
            insulin=max(
                self._model_config.min_insulin,
                min(state.insulin, self._model_config.max_insulin),
            ),
            carb_pool=max(0.0, state.carb_pool),
            interstitium=max(
                self._model_config.min_glucose,
                min(state.interstitium, self._model_config.max_glucose),
            ),
        )
