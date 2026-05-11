"""Composition root for the modular glucose-insulin simulator app."""

from pathlib import Path
import sys
from typing import Literal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.simulator import GlucoseSimulator

IntegratorMethod = Literal["RK45", "DOP853", "BDF"]


def _ensure_project_root_on_sys_path() -> None:
    """Allow running as a script via `python src/main.py`."""
    if __package__ in (None, ""):
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))


def build_simulator(
    integrator_method: IntegratorMethod = "RK45",
    initial_glucose_mmol_l: float | None = None,
    validation_mode: bool = False,
) -> "GlucoseSimulator":
    """Build simulator dependencies with validated configuration.

    Args:
        integrator_method: ODE solver method.
        initial_glucose_mmol_l: Seed initial glucose, or use basal.
        validation_mode: If True, disable controller (passive replay mode).
    """
    _ensure_project_root_on_sys_path()

    from src.core.controller import ProportionalController
    from src.core.integrator import SolveIvPIntegrator
    from src.core.model import PhysiologyModel
    from src.core.simulator import GlucoseSimulator
    from src.core.state import ControllerConfig
    from src.core.state import IntegratorConfig
    from src.core.state import ModelConfig
    from src.core.state import SimulationState

    model_config = ModelConfig()
    glucose_start = model_config.glucose_basal
    if initial_glucose_mmol_l is not None:
        if initial_glucose_mmol_l <= 0.0:
            raise ValueError("initial_glucose_mmol_l must be positive")
        glucose_start = initial_glucose_mmol_l

    controller_config = ControllerConfig()
    integrator_config = IntegratorConfig(method=integrator_method)
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=glucose_start,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        interstitium=glucose_start,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    return GlucoseSimulator(
        model=PhysiologyModel(
            integrator=SolveIvPIntegrator(),
            integrator_config=integrator_config,
        ),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
        integrator_config=integrator_config,
        validation_mode=validation_mode,
    )


def main() -> int:
    """Start application and report dependency/setup issues clearly."""
    _ensure_project_root_on_sys_path()

    try:
        from src.gui.app import DigitalTwinApp
    except ImportError as exc:
        print(
            "Failed to start GUI. Install dependencies first, e.g. "
            "pipenv install --dev"
        )
        print(f"Import error: {exc}")
        return 1

    app = DigitalTwinApp(
        simulator_builder=build_simulator,
        step_interval_ms=200,
    )
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
