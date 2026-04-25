"""Tests for simulator composition root helpers."""

import pytest

from src.main import build_simulator


def test_build_simulator_uses_default_basal_glucose() -> None:
    """Default builder should start from model basal glucose level."""
    simulator = build_simulator("RK45")

    assert simulator.current_state.glucose == pytest.approx(5.0)


def test_build_simulator_accepts_validation_glucose_seed() -> None:
    """Builder should allow validation runs to seed initial glucose."""
    simulator = build_simulator("RK45", initial_glucose_mmol_l=7.2)

    assert simulator.current_state.glucose == pytest.approx(7.2)
