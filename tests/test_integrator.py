"""Tests for solve_ivp integrator adapter and config validation."""

from typing import Any
from typing import cast

import numpy as np
import pytest

from src.core.integrator import SolveIvPIntegrator
from src.core.state import IntegratorConfig


def test_integrator_config_rejects_unsupported_method() -> None:
    """Only RK45, DOP853, and BDF should be accepted."""
    invalid_method = cast(Any, "RK23")
    config = IntegratorConfig(method=invalid_method)

    with pytest.raises(ValueError, match="method"):
        config.validate()


def test_integrator_config_rejects_non_positive_tolerances() -> None:
    """Absolute and relative tolerances must be strictly positive."""
    with pytest.raises(ValueError, match="rtol"):
        IntegratorConfig(rtol=0.0).validate()

    with pytest.raises(ValueError, match="atol"):
        IntegratorConfig(atol=-1e-8).validate()


def test_solve_ivp_integrator_runs_single_step_for_supported_methods() -> None:
    """Each supported method should produce a plausible one-step update."""
    integrator = SolveIvPIntegrator()

    for method in ("RK45", "DOP853", "BDF"):
        y0 = np.array([1.0], dtype=float)
        config = IntegratorConfig(method=method)
        y_end, info = integrator.integrate_step(
            derivative=lambda _time, values: -values,
            y0=y0,
            t0=0.0,
            dt=1.0,
            config=config,
        )

        assert info.success
        assert 0.0 < float(y_end[0]) < 1.0
