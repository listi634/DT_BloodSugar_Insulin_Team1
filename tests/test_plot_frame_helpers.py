"""Tests for plot timestamp helpers."""

from datetime import datetime

from src.gui.plot_frame import format_day_label


def test_format_day_label_rolls_over_at_midnight() -> None:
    """Minute offsets should format as day-level timestamps."""
    origin = datetime(2026, 5, 1, 23, 30)

    assert format_day_label(origin, 60.0) == "2026-05-02"