"""Small smoke test for simulator replay and bolus behavior.

Run: python scripts/smoke_replay.py
"""
from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import EstimatorConfig
from src.core.state import ControllerConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def build_simulator():
    model_config = ModelConfig()
    controller_config = ControllerConfig()
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=model_config.glucose_basal,
        insulin=model_config.insulin_basal,
        carb_pool=0.0,
        interstitium=model_config.glucose_basal,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )
    estimator = ExtendedKalmanFilterEstimator(
        model=PhysiologyModel(),
        model_config=model_config,
        initial_state=initial_state,
        estimator_config=EstimatorConfig(),
    )
    sim = GlucoseSimulator(
        model=PhysiologyModel(),
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
        estimator=estimator,
    )
    return sim


if __name__ == "__main__":
    sim = build_simulator()
    print("Initial snapshot:", sim.history[-1])

    print("--- Replay step (controller disabled) ---")
    sim.queue_meal(30.0)
    snap = sim.step(measured_interstitium=5.0, use_controller=False)
    print("After replay step:", snap)

    print("--- Queue bolus and step (prediction) ---")
    sim.export_snapshot()  # snapshot available
    sim.queue_bolus(units=5.0)
    snap2 = sim.step()
    print("After bolus step:", snap2)

    print("History length:", len(sim.history))
