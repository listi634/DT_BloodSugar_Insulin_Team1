"""Tests for the parameter tuning CLI helpers."""

from scripts.tune_parameters import _parse_parameter_spec
from scripts.tune_parameters import _parse_float_list


def test_parse_parameter_spec_returns_name_and_values() -> None:
    """Parameter specs should split into a name and numeric grid."""
    name, values = _parse_parameter_spec("model.glucose_decay=0.01,0.02")

    assert name == "model.glucose_decay"
    assert values == [0.01, 0.02]


def test_parse_float_list_rejects_empty_grids() -> None:
    """An empty parameter list should fail with a clear error."""
    try:
        _parse_float_list(" , ")
    except ValueError as exc:
        assert "at least one value" in str(exc)
    else:
        raise AssertionError("Expected ValueError for an empty grid")