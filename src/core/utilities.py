"""Pure utility functions for validation and data processing."""

from collections.abc import Sequence


def collect_due_carb_events(
    carb_events: list[tuple[float, float]],
    start_index: int,
    current_time_minutes: float,
) -> tuple[list[float], int]:
    """Return carb events due at current step time and next replay index."""
    due_carbs: list[float] = []
    replay_index = start_index
    epsilon = 1e-9
    while replay_index < len(carb_events):
        event_time, carbs = carb_events[replay_index]
        if event_time <= current_time_minutes + epsilon:
            due_carbs.append(carbs)
            replay_index += 1
            continue
        break
    return due_carbs, replay_index


def collect_due_insulin_events(
    insulin_events: list[tuple[float, float]],
    start_index: int,
    current_time_minutes: float,
) -> tuple[list[float], int]:
    """Return insulin events due at current step time and next index."""
    due_insulin: list[float] = []
    replay_index = start_index
    epsilon = 1e-9
    while replay_index < len(insulin_events):
        event_time, units = insulin_events[replay_index]
        if event_time <= current_time_minutes + epsilon:
            due_insulin.append(units)
            replay_index += 1
            continue
        break
    return due_insulin, replay_index


def sanitize_reference_points(
    points: Sequence[tuple[float, float]] | None,
) -> list[tuple[float, float]]:
    """Return reference points sorted by time with safe empty handling."""
    if points is None:
        return []
    return sorted(
        [(float(time), float(value)) for time, value in points],
        key=lambda item: item[0],
    )
