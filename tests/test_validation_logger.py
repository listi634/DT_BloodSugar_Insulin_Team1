"""Tests for validation replay logging artifacts."""

import json

from src.core.benchmark_loader import ValidationWindowData
from src.core.state import ControllerConfig
from src.core.state import ModelConfig
from src.core.state import SimulationSnapshot
from src.core.state import SimulationState
from src.core.validation_logger import ValidationReplayLogger


def _build_window() -> ValidationWindowData:
    return ValidationWindowData(
        user_id="user-1",
        start_timestamp="2026-05-01 00:00:00",
        end_timestamp="2026-05-01 00:05:00",
        initial_glucose_mmol_l=5.5,
        duration_minutes=5.0,
        glucose_reference=[(0.0, 5.5)],
        measurement_reference=[(0.0, 5.5)],
        carb_reference=[(0.0, 30.0)],
        carb_replay_events=[(0.0, 30.0)],
        basal_reference=[(0.0, 0.8)],
        insulin_reference=[(0.0, 2.0)],
    )


def _build_state() -> SimulationState:
    return SimulationState(
        time_minutes=0.0,
        glucose=5.5,
        insulin=10.0,
        carb_stomach=0.0,
        carb_intestine=0.0,
        interstitium=5.4,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
        basal_insulin_rate=0.8,
    )


def _build_snapshot() -> SimulationSnapshot:
    return SimulationSnapshot(
        time_minutes=1.0,
        glucose=5.6,
        insulin=10.2,
        carb_stomach=29.0,
        carb_intestine=0.5,
        interstitium=5.45,
        insulin_rate=0.1,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
        basal_insulin_rate=0.8,
    )


def test_validation_replay_logger_writes_jsonl(tmp_path) -> None:
    """Logger should write session, step, and footer records."""
    logger = ValidationReplayLogger(
        output_dir=tmp_path / "validation_logs",
        window=_build_window(),
        model_config=ModelConfig(),
        controller_config=ControllerConfig(),
        initial_state=_build_state(),
    )

    logger.record_step(
        snapshot=_build_snapshot(),
        mode="replay",
        measured_glucose_mmol_l=5.5,
        due_carb_grams=30.0,
        due_bolus_units=2.0,
        due_basal_rate_u_per_h=0.8,
    )
    logger.close()

    lines = logger.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3

    session = json.loads(lines[0])
    step = json.loads(lines[1])
    footer = json.loads(lines[2])

    assert session["type"] == "session"
    assert session["window"]["user_id"] == "user-1"
    assert step["type"] == "step"
    assert step["mode"] == "replay"
    assert step["measured_glucose_mmol_l"] == 5.5
    assert step["simulation_state"]["interstitium"] == 5.45
    assert footer["type"] == "footer"
    assert footer["record_count"] == 1
