"""Tests for benchmark data loading and validation-window extraction."""

from pathlib import Path

import pytest

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.benchmark_loader import MGDL_PER_MMOLL


def _write_csv(file_path: Path, content: str) -> None:
    """Write helper CSV content to temporary file."""
    file_path.write_text(content, encoding="utf-8")


def test_loader_validates_required_columns(tmp_path: Path) -> None:
    """Loader should fail with clear error when required columns are missing."""
    csv_path = tmp_path / "invalid.csv"
    _write_csv(
        csv_path,
        "user_id,timestamp,glucose,carbs\n"
        "U001,2024-01-01 00:00:00,100,0\n",
    )

    with pytest.raises(ValueError, match="missing required columns"):
        GlucoBenchLoader(csv_path)


def test_get_user_ids_and_days_sorted(tmp_path: Path) -> None:
    """Users and distinct days should be returned in ascending order."""
    csv_path = tmp_path / "sample.csv"
    _write_csv(
        csv_path,
        "\n".join(
            [
                "user_id,timestamp,glucose,carbs,insulin_basal",
                "U002,2024-01-01 00:10:00,90,0,1.0",
                "U001,2024-01-01 00:15:00,99,0,0.9",
                "U001,2024-01-01 00:05:00,101,0,1.1",
                "U001,2024-01-02 00:05:00,102,0,1.2",
            ]
        ),
    )

    loader = GlucoBenchLoader(csv_path)

    assert loader.get_user_ids() == ["U001", "U002"]
    assert loader.get_user_days("U001") == ["2024-01-01", "2024-01-02"]


def test_get_valid_end_days_constrains_from_selected_start(
    tmp_path: Path,
) -> None:
    """End-day options should include only days at or after start day."""
    csv_path = tmp_path / "sample.csv"
    _write_csv(
        csv_path,
        "\n".join(
            [
                "user_id,timestamp,glucose,carbs,insulin_basal",
                "U001,2024-01-01 00:10:00,90,0,1.0",
                "U001,2024-01-02 00:10:00,91,0,1.1",
                "U001,2024-01-03 00:10:00,92,0,1.2",
            ]
        ),
    )

    loader = GlucoBenchLoader(csv_path)

    assert loader.get_valid_end_days("U001", "2024-01-02") == [
        "2024-01-02",
        "2024-01-03",
    ]


def test_build_validation_window_converts_and_extracts_carbs(
    tmp_path: Path,
) -> None:
    """Window extraction should include inclusive bounds and carb replay map."""
    csv_path = tmp_path / "sample.csv"
    _write_csv(
        csv_path,
        "\n".join(
            [
                "user_id,timestamp,glucose,carbs,insulin_basal",
                "U001,2024-01-01 00:00:00,126,0,1.0",
                "U001,2024-01-01 00:05:00,144,0,0.9",
                "U001,2024-01-01 00:10:00,162,25,0.8",
                "U001,2024-01-01 00:20:00,180,0,0.7",
            ]
        ),
    )

    loader = GlucoBenchLoader(csv_path)
    window = loader.build_validation_window(
        user_id="U001",
        start_timestamp="2024-01-01 00:05:00",
        end_timestamp="2024-01-01 00:20:00",
    )

    assert window.start_timestamp == "2024-01-01 00:05:00"
    assert window.end_timestamp == "2024-01-01 00:20:00"
    assert window.initial_glucose_mmol_l == pytest.approx(144 / MGDL_PER_MMOLL)
    assert window.duration_minutes == pytest.approx(15.0)
    assert window.glucose_reference == [
        (0.0, pytest.approx(144 / MGDL_PER_MMOLL)),
        (5.0, pytest.approx(162 / MGDL_PER_MMOLL)),
        (15.0, pytest.approx(180 / MGDL_PER_MMOLL)),
    ]
    assert window.measurement_reference == window.glucose_reference
    assert window.carb_reference == [(5.0, 25.0)]
    assert window.carb_replay_events == [(5.0, 25.0)]
    assert window.insulin_basal_reference == [
        (0.0, 0.9),
        (5.0, 0.8),
        (15.0, 0.7),
    ]
    assert window.insulin_reference == []


def test_build_validation_window_rejects_invalid_inputs(
    tmp_path: Path,
) -> None:
    """Window extraction should reject unknown users and invalid order."""
    csv_path = tmp_path / "sample.csv"
    _write_csv(
        csv_path,
        "\n".join(
            [
                "user_id,timestamp,glucose,carbs,insulin_basal",
                "U001,2024-01-01 00:00:00,120,0,1.0",
            ]
        ),
    )

    loader = GlucoBenchLoader(csv_path)

    with pytest.raises(ValueError, match="Unknown user_id"):
        loader.get_user_days("U999")

    with pytest.raises(ValueError, match="End timestamp"):
        loader.build_validation_window(
            user_id="U001",
            start_timestamp="2024-01-01 00:10:00",
            end_timestamp="2024-01-01 00:00:00",
        )

    with pytest.raises(ValueError, match="End day"):
        loader.build_validation_window_for_days(
            user_id="U001",
            start_day="2024-01-02",
            end_day="2024-01-01",
        )
