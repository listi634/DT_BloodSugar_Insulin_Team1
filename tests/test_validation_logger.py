"""Tests for validation replay logging artifacts."""

import json

from src.core.benchmark_loader import ValidationWindowData
from src.core.state import ControllerConfig
from src.core.state import ModelConfig
from src.core.state import SimulationSnapshot
from src.core.state import SimulationState
from src.core.prediction import PredictionResult
from src.core.prediction import PredictionScenario
from src.core.prediction_metrics import PredictionMetrics
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


def test_validation_replay_logger_writes_prediction_records(tmp_path) -> None:
    """Logger should write a structured prediction record."""
    logger = ValidationReplayLogger(
        output_dir=tmp_path / "validation_logs",
        window=_build_window(),
        model_config=ModelConfig(),
        controller_config=ControllerConfig(),
        initial_state=_build_state(),
    )

    scenario = PredictionScenario(
        horizon_minutes=30.0,
        meal_carbs=45.0,
        bolus_units=2.0,
    )
    result = PredictionResult(
        time_minutes=[0.0, 1.0, 2.0],
        glucose=[5.5, 5.7, 5.9],
        insulin=[10.0, 10.1, 10.2],
        interstitium=[5.4, 5.6, 5.8],
        scenario=scenario,
    )
    metrics = PredictionMetrics(
        rmse=0.12,
        mard_percent=2.3,
        peak_time_error_minutes=1.0,
        sample_count=3,
    )

    logger.record_prediction(
        start_state=_build_state(),
        scenario=scenario,
        result=result,
        prediction_mode="interstitium",
        trigger="meal_event",
        show_metrics=True,
        metrics=metrics,
    )
    logger.close()

    lines = logger.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3

    prediction = json.loads(lines[1])
    footer = json.loads(lines[2])

    assert prediction["type"] == "prediction"
    assert prediction["trigger"] == "meal_event"
    assert prediction["prediction_mode"] == "interstitium"
    assert prediction["show_metrics"] is True
    assert prediction["start_state"]["glucose"] == 5.5
    assert prediction["scenario"]["meal_carbs"] == 45.0
    assert prediction["result"]["interstitium"] == [5.4, 5.6, 5.8]
    assert prediction["metrics"]["rmse"] == 0.12
    assert footer["record_count"] == 1
