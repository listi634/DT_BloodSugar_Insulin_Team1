#!/usr/bin/env python3
"""Systematically tune meal absorption parameters (stomach_tau, intestine_tau).

This script performs a grid search over meal absorption tau parameters,
evaluates each combination against validation windows, and logs results
to help identify optimal parameter values for reducing oscillations.

Process:
1. Define parameter ranges (stomach_tau: 10-25 min, intestine_tau: 20-50 min)
2. For each combination, run validation and compute metrics
3. Compare to baseline (stomach=15, intestine=30)
4. Log all results with improvement tracking
5. Save best parameters and detailed tuning log
"""

# pylint: disable=import-error

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import EstimatorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState


def parse_validation_windows_text(
    txt_path: Path,
) -> list[dict[str, Any]]:
    """Parse validation windows from text file.

    Args:
        txt_path: Path to phase1_validation_windows.txt

    Returns:
        List of dicts with keys: user_id, start_date, end_date
    """
    windows = []
    with txt_path.open(mode="r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    current_window: dict[str, Any] = {}
    for line in lines:
        if line.startswith("User:"):
            if current_window and "user_id" in current_window:
                windows.append(current_window)
            current_window = {"user_id": line.split()[1]}
        elif line.startswith("Date Range:"):
            # Parse "Date Range: 2024-09-01 to 2024-09-01 (24.0 hours)"
            parts = line.split(": ")[1].split(" to ")
            current_window["start_date"] = parts[0].strip()
            end_date_part = parts[1].split(" (")[0]
            current_window["end_date"] = end_date_part.strip()

    if current_window and "user_id" in current_window:
        windows.append(current_window)
    return windows


def compute_metrics(
    measured: np.ndarray, simulated: np.ndarray
) -> dict[str, float]:
    """Compute validation metrics.

    Args:
        measured: Measured glucose values (mmol/L)
        simulated: Simulated interstitium values (mmol/L)

    Returns:
        Dictionary with rmse, mae, mean_error, oscillation_count
    """
    errors = simulated - measured
    rmse = float(np.sqrt(np.mean(errors**2)))
    mae = float(np.mean(np.abs(errors)))
    mean_error = float(np.mean(errors))
    oscillations = 0
    for i in range(1, len(errors) - 1):
        if (errors[i] - errors[i - 1]) * (errors[i + 1] - errors[i]) < 0:
            oscillations += 1
    return {
        "rmse": rmse,
        "mae": mae,
        "mean_error": mean_error,
        "oscillation_count": oscillations,
    }


def simulate_window(
    loader: GlucoBenchLoader,
    user_id: str,
    start_date: str,
    end_date: str,
    model_config: ModelConfig,
) -> dict[str, Any]:
    """Simulate a single validation window with given ModelConfig.

    Args:
        loader: GlucoBenchLoader instance
        user_id: User identifier (e.g., 'U001')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        model_config: ModelConfig with tau parameters to test

    Returns:
        Dictionary with metrics and time series
    """
    # Load validation window
    window = loader.build_validation_window_for_days(
        user_id, start_date, end_date
    )

    # Create model config with user's baseline glucose
    model_config_with_baseline = ModelConfig(
        **{
            **model_config.__dict__,
            "glucose_basal": window.initial_glucose_mmol_l,
        }
    )
    controller_config = ControllerConfig()

    # Initialize simulator state
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=window.initial_glucose_mmol_l,
        insulin=model_config_with_baseline.insulin_basal,
        carb_stomach=0.0,
        carb_intestine=0.0,
        interstitium=window.initial_glucose_mmol_l,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    # Create components
    model = PhysiologyModel()
    estimator = ExtendedKalmanFilterEstimator(
        model=model,
        model_config=model_config_with_baseline,
        initial_state=initial_state,
        estimator_config=EstimatorConfig(),
    )
    controller = ProportionalController()

    simulator = GlucoseSimulator(
        model=model,
        controller=controller,
        model_config=model_config_with_baseline,
        controller_config=controller_config,
        initial_state=initial_state,
        estimator=estimator,
    )

    # Queue all meals and boluses
    for time_min, carbs_g in window.carb_replay_events:
        if carbs_g > 0.0:
            simulator.queue_meal(carbs_g)

    for time_min, bolus_units in window.insulin_reference:
        if bolus_units > 0.0:
            simulator.queue_bolus(bolus_units)

    # Run simulation with 5-minute steps
    dt_minutes = 5.0
    num_steps = int(window.duration_minutes / dt_minutes) + 1

    simulated_times = []
    simulated_glucose = []
    simulated_interstitium = []
    simulated_insulin = []

    # Extract measured glucose from reference
    measured_glucose = [v for _, v in window.measurement_reference]
    measured_times = [t for t, _ in window.measurement_reference]

    for step in range(num_steps):
        current_time = step * dt_minutes
        if current_time > window.duration_minutes:
            break

        # Find nearest measured glucose for this time
        nearest_idx = min(
            range(len(measured_times)),
            key=lambda i: abs(measured_times[i] - current_time),
        )
        measured_at_time = measured_glucose[nearest_idx]

        snapshot = simulator.step(measured_interstitium=measured_at_time)

        simulated_times.append(snapshot.time_minutes)
        simulated_glucose.append(snapshot.glucose)
        simulated_interstitium.append(snapshot.interstitium)
        simulated_insulin.append(snapshot.insulin_rate)

    # Resample measured to match simulated times
    resampled_measured = []
    for sim_t in simulated_times:
        idx = min(
            range(len(measured_times)),
            key=lambda i: abs(measured_times[i] - sim_t),
        )
        resampled_measured.append(measured_glucose[idx])

    # Compute metrics
    simulated_arr = np.array(simulated_interstitium)
    measured_arr = np.array(resampled_measured)
    metrics = compute_metrics(measured_arr, simulated_arr)

    return {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "measured_glucose": measured_arr,
        "simulated_interstitium": simulated_arr,
        "metrics": metrics,
    }


def log_tuning_entry(
    log_path: Path,
    stomach_tau: float,
    intestine_tau: float,
    all_metrics: list[dict[str, float]],
    improvement_pct: float,
) -> None:
    """Log a single parameter combination and its results.

    Args:
        log_path: Path to tuning log file
        stomach_tau: Stomach tau in minutes
        intestine_tau: Intestine tau in minutes
        all_metrics: List of metrics dicts from all windows
        improvement_pct: Percent improvement in oscillations vs baseline
    """


def main() -> None:
    """Run quick parameter tuning with focused parameter space."""
    base_dir = Path(__file__).parent.parent
    window_txt = base_dir / "project_files" / "phase1_validation_windows.txt"
    results_dir = base_dir / "project_files" / "phase1_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    tuning_log = base_dir / "project_files" / "phase1_tuning_log.txt"

    with tuning_log.open(mode="w", encoding="utf-8") as f:
        f.write("=" * 78 + "\n")
        f.write("PHASE 1 MEAL ABSORPTION PARAMETER TUNING (FOCUSED)\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write("=" * 78 + "\n\n")
        f.write("Testing focused parameter set based on literature:\n")
        f.write("- stomach_tau: 12-18 min (meal transit to intestine)\n")
        f.write(
            "- intestine_tau: 25-40 min (intestinal glucose absorption)\n\n"
        )

    loader = GlucoBenchLoader(
        base_dir / "data" / "GlucoBench_benchmark_dataset.csv"
    )
    windows = parse_validation_windows_text(window_txt)

    print("=" * 78)
    print("PHASE 1 PARAMETER TUNING (FOCUSED)")
    print("=" * 78)
    print(f"Loaded {len(windows)} validation windows\n")

    # Baseline
    baseline_config = ModelConfig()
    baseline_metrics_all = []
    for window in windows:
        result = simulate_window(
            loader,
            window["user_id"],
            window["start_date"],
            window["end_date"],
            baseline_config,
        )
        baseline_metrics_all.append(result["metrics"])

    baseline_osc = sum(m["oscillation_count"] for m in baseline_metrics_all)
    baseline_rmse = np.mean([m["rmse"] for m in baseline_metrics_all])
    print(f"Baseline (stomach=15.0, intestine=30.0):")
    print(f"  Mean RMSE: {baseline_rmse:.4f}")
    print(f"  Total Oscillations: {baseline_osc}\n")

    with tuning_log.open(mode="a", encoding="utf-8") as f:
        f.write(f"Baseline: stomach=15.0, intestine=30.0\n")
        f.write(f"  Oscillations: {baseline_osc}\n")
        f.write(f"  Mean RMSE: {baseline_rmse:.4f}\n\n")
        f.write("TEST RESULTS:\n")
        f.write("-" * 78 + "\n")

    # Test focused parameter combinations
    best_osc = baseline_osc
    best_params = (15.0, 30.0)
    candidates = [
        (12.0, 25.0),
        (12.0, 30.0),
        (15.0, 30.0),
        (15.0, 35.0),
        (18.0, 35.0),
        (18.0, 40.0),
    ]
    total_combos = len(candidates)

    for combo_idx, (stomach_tau, intestine_tau) in enumerate(candidates, 1):
        config = ModelConfig(
            stomach_tau_minutes=stomach_tau,
            intestine_tau_minutes=intestine_tau,
        )

        metrics_list = []
        for window in windows:
            try:
                result = simulate_window(
                    loader,
                    window["user_id"],
                    window["start_date"],
                    window["end_date"],
                    config,
                )
                metrics_list.append(result["metrics"])
            except Exception as e:  # pylint: disable=broad-except
                print(f"    Error: {e}")
                continue

        if not metrics_list:
            continue

        total_osc = sum(m["oscillation_count"] for m in metrics_list)
        mean_rmse = np.mean([m["rmse"] for m in metrics_list])
        improvement_pct = (baseline_osc - total_osc) / baseline_osc * 100.0

        # Log
        with tuning_log.open(mode="a", encoding="utf-8") as f:
            f.write(
                f"  stomach={stomach_tau:5.1f}, intestine={intestine_tau:5.1f} "
                f"| RMSE={mean_rmse:.4f}, Osc={total_osc:3d} "
                f"({improvement_pct:+6.1f}%)\n"
            )

        # Update best
        if total_osc < best_osc:
            best_osc = total_osc
            best_params = (stomach_tau, intestine_tau)

        status = "✓" if total_osc < baseline_osc else " "
        print(
            f"  [{combo_idx:2d}/{total_combos}] {status} "
            f"stomach={stomach_tau:5.1f}, intestine={intestine_tau:5.1f} "
            f"| Osc={total_osc:3d} ({improvement_pct:+6.1f}%)"
        )

    improvement_best = (baseline_osc - best_osc) / baseline_osc * 100.0
    with tuning_log.open(mode="a", encoding="utf-8") as f:
        f.write("-" * 78 + "\n")
        f.write(f"\nBEST PARAMETERS:\n")
        f.write(f"  stomach_tau_minutes: {best_params[0]}\n")
        f.write(f"  intestine_tau_minutes: {best_params[1]}\n")
        f.write(f"  Oscillations: {best_osc} ({improvement_best:+.1f}%)\n")
        f.write(f"\nCompleted: {datetime.now().isoformat()}\n")

    print(f"\n{'=' * 78}")
    print(
        f"BEST PARAMETERS: stomach_tau={best_params[0]}, "
        f"intestine_tau={best_params[1]}"
    )
    print(f"  Oscillations: {best_osc} ({improvement_best:+.1f}%)")
    print(f"{'=' * 78}\n")
    print(f"📝 Tuning log: {tuning_log}\n")


if __name__ == "__main__":
    main()
