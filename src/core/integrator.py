"""Adapter layer for one-step ODE integration with scipy.solve_ivp."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from src.core.state import IntegratorConfig


@dataclass(frozen=True)
class SolverStepInfo:
    """Optional diagnostics collected from a solver step."""

    success: bool
    status: int
    message: str
    nfev: int


class SolveIvPIntegrator:
    """Integrates one interval [t, t + dt] using scipy.solve_ivp."""

    def integrate_step(
        self,
        derivative: Callable[[float, np.ndarray], np.ndarray],
        y0: np.ndarray,
        t0: float,
        dt: float,
        config: IntegratorConfig,
    ) -> tuple[np.ndarray, SolverStepInfo]:
        """Run one ODE step and return end state with solver metadata.

        Args:
            derivative: Right-hand-side ODE function f(t, y).
            y0: Initial continuous state vector.
            t0: Start time in minutes.
            dt: Step width in minutes.
            config: Integrator configuration for this solve call.

        Returns:
            Tuple of end-state vector at t0 + dt and solver diagnostics.

        Raises:
            ValueError: If dt is not positive.
            RuntimeError: If solve_ivp does not return a successful step.
        """
        config.validate()
        if dt <= 0.0:
            raise ValueError("dt must be positive")

        solver_kwargs: dict[str, object] = {
            "method": config.method,
            "rtol": config.rtol,
            "atol": config.atol,
            "dense_output": config.dense_output,
            "events": config.events,
        }
        if config.max_step is not None:
            solver_kwargs["max_step"] = config.max_step

        solution = solve_ivp(
            fun=derivative,
            t_span=(t0, t0 + dt),
            y0=y0,
            **solver_kwargs,
        )

        info = SolverStepInfo(
            success=bool(solution.success),
            status=int(solution.status),
            message=str(solution.message),
            nfev=int(solution.nfev),
        )

        if not info.success:
            raise RuntimeError(f"solve_ivp failed: {info.message}")

        end_state = np.asarray(solution.y[:, -1], dtype=float)
        return end_state, info
