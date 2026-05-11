"""Tests for low-order physiology model behavior."""

import numpy as np

from src.core.model import PhysiologyModel
from src.core.state import IntegratorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def test_meal_carb_pool_increases_glucose() -> None:
    """A non-zero carb pool should raise glucose without immediate clipping."""
    model = PhysiologyModel()
    config = ModelConfig()
    state = SimulationState(
        time_minutes=0.0,
        glucose=config.glucose_basal,
        insulin=config.insulin_basal,
        carb_pool=80.0,
        interstitium=config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    next_state = model.integrate(state, config)

    assert next_state.glucose > config.glucose_basal
    assert next_state.glucose < 6.0


def test_meal_absorption_uses_intermediate_intestine_compartment() -> None:
    """Meal input should flow through the new intestine compartment."""
    model = PhysiologyModel()
    config = ModelConfig()
    state = SimulationState(
        time_minutes=0.0,
        glucose=config.glucose_basal,
        insulin=config.insulin_basal,
        carb_pool=80.0,
        interstitium=config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    next_state = model.integrate(state, config)

    assert next_state.carb_pool < state.carb_pool
    assert next_state.intestine_carb > 0.0
    assert next_state.glucose < 6.0


def test_high_glucose_triggers_endogenous_insulin_response() -> None:
    """Insulin should increase when glucose is elevated."""
    model = PhysiologyModel()
    config = ModelConfig()
    state = SimulationState(
        time_minutes=0.0,
        glucose=9.0,
        insulin=config.insulin_basal,
        carb_pool=0.0,
        interstitium=9.0,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    next_state = model.integrate(state, config)

    assert next_state.insulin > config.insulin_basal


def test_insulin_action_lags_behind_insulin_level() -> None:
    """The delayed insulin-action compartment should respond gradually."""
    model = PhysiologyModel()
    config = ModelConfig()
    state = SimulationState(
        time_minutes=0.0,
        glucose=9.0,
        insulin=config.insulin_basal,
        carb_pool=0.0,
        interstitium=9.0,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    next_state = model.integrate(state, config)

    assert next_state.insulin > config.insulin_basal
    assert next_state.insulin_action >= 0.0
    assert next_state.insulin_action < next_state.insulin - config.insulin_basal


def test_state_values_are_clamped_to_safety_bounds() -> None:
    """Integrator should keep outputs within configured limits."""
    model = PhysiologyModel()
    config = ModelConfig(max_glucose=12.0, max_insulin=50.0)
    state = SimulationState(
        time_minutes=0.0,
        glucose=20.0,
        insulin=55.0,
        carb_pool=1000.0,
        interstitium=12.0,
        insulin_rate=10.0,
        sport_multiplier=1.5,
        sport_minutes_remaining=10.0,
    )

    next_state = model.integrate(state, config)

    assert next_state.glucose <= config.max_glucose
    assert next_state.insulin <= config.max_insulin


def test_integrator_events_are_forwarded_to_solver() -> None:
    """Configured integrator events should be invoked during integration."""
    event_calls: list[float] = []

    def tracking_event(time_minutes: float, values: object) -> float:
        del values
        event_calls.append(time_minutes)
        return 1.0

    model = PhysiologyModel(
        integrator_config=IntegratorConfig(events=[tracking_event])
    )
    config = ModelConfig()
    state = SimulationState(
        time_minutes=0.0,
        glucose=config.glucose_basal,
        insulin=config.insulin_basal,
        carb_pool=10.0,
        interstitium=config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    model.integrate(state, config)

    assert np.asarray(event_calls).size > 0
