"""Unit tests for validation runtime helper functions."""

from src.core.utilities import collect_due_carb_events
from src.core.utilities import collect_due_insulin_events
from src.core.utilities import sanitize_reference_points


def test_collect_due_carb_events_advances_replay_index() -> None:
    """Helper should return only due events at current simulation time."""
    events = [(0.0, 10.0), (5.0, 20.0), (10.0, 30.0)]

    due_carbs, next_index = collect_due_carb_events(
        carb_events=events,
        start_index=0,
        current_time_minutes=5.0,
    )

    assert due_carbs == [10.0, 20.0]
    assert next_index == 2


def test_sanitize_reference_points_sorts_by_elapsed_time() -> None:
    """Overlay helpers should normalize and sort incoming point tuples."""
    points = [(15.0, 1.0), (0.0, 2.0), (5.0, 3.0)]

    normalized = sanitize_reference_points(points)

    assert normalized == [(0.0, 2.0), (5.0, 3.0), (15.0, 1.0)]


def test_collect_due_insulin_events_advances_replay_index() -> None:
    """Helper should return insulin events due at current time."""
    events = [(0.0, 0.5), (4.0, 1.0), (9.0, 2.0)]

    due_insulin, next_index = collect_due_insulin_events(
        insulin_events=events,
        start_index=0,
        current_time_minutes=4.0,
    )

    assert due_insulin == [0.5, 1.0]
    assert next_index == 2
