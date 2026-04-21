"""Composition root for the modular glucose-insulin simulator app."""

from pathlib import Path
import sys

# Allow running as: python src/main.py
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.core.controller import ProportionalController
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def build_simulator() -> GlucoseSimulator:
    """Build simulator dependencies with validated configuration."""
    model_config = ModelConfig()
    controller_config = ControllerConfig()
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=model_config.glucose_basal,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    return GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
    )


def main() -> int:
    """Start application and report dependency/setup issues clearly."""
    try:
        from src.gui.app import DigitalTwinApp
    except ImportError as exc:
        print(
            "Failed to start GUI. Install dependencies first, e.g. "
            "pipenv install --dev"
        )
        print(f"Import error: {exc}")
        return 1

    simulator = build_simulator()
    app = DigitalTwinApp(simulator=simulator, step_interval_ms=200)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
