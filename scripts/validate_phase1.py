#!/usr/bin/env python3
"""Validate Phase 1 two-compartment model against GlucoBench data.

This script:
1. Loads validation windows from project_files/phase1_validation_windows.txt
2. For each window, replays meals/boluses in simulator with user's baseline
3. Compares simulated interstitium vs measured CGM glucose
4. Computes RMSE, MAE, oscillation count
5. Generates 3-subplot matplotlib figures (glucose, insulin, errors)
6. Saves PNG plots and CSV metrics summary
"""

# pylint: disable=import-error

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import EstimatorConfig
from src.core.state import IntegratorConfig
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
            if current_window:
                windows.append(current_window)
            current_window = {"user_id": line.split(":", 1)[1].strip()}
        elif line.startswith("Date Range:"):
            parts = line.split(":", 1)[1].strip()
            dates = parts.split(" to ")
            if len(dates) == 2:
                current_window["start_date"] = dates[0].strip()
                current_window["end_date"] = dates[1].split(" (")[0].strip()

    if current_window:
        windows.append(current_window)

    return windows


def compute_metrics(
    measured: list[float], simulated: list[float]
) -> dict[str, float]:
    """Compute error metrics between measured and simulated glucose.

    Args:
        measured: Reference CGM glucose values (mmol/L)
        simulated: Simulated interstitium values (mmol/L)

    Returns:
        Dict with RMSE, MAE, mean_error, oscillation_count
    """
    if len(measured) != len(simulated):
        raise ValueError(
            f"Length mismatch: measured {len(measured)} vs "
            f"simulated {len(simulated)}"
        )

    measured_arr = np.array(measured, dtype=float)
    simulated_arr = np.array(simulated, dtype=float)

    errors = simulated_arr - measured_arr
    rmse = float(np.sqrt(np.mean(errors**2)))
    mae = float(np.mean(np.abs(errors)))
    mean_error = float(np.mean(errors))

    # Count oscillations (direction changes in error)
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
) -> dict[str, Any]:
    """Simulate a single validation window.

    Args:
        loader: GlucoBenchLoader instance with benchmark data
        user_id: User ID
        start_date: Start date in YYYY-mm-dd format
        end_date: End date in YYYY-mm-dd format

    Returns:
        Dict with validation results and time series
    """
    # Load validation window
    window = loader.build_validation_window_for_days(
        user_id, start_date, end_date
    )

    # Initialize simulator with user's baseline glucose
    model_config = ModelConfig(glucose_basal=window.initial_glucose_mmol_l)
    controller_config = ControllerConfig()

    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=window.initial_glucose_mmol_l,
        insulin=model_config.insulin_basal,
        carb_stomach=0.0,
        carb_intestine=0.0,
        interstitium=window.initial_glucose_mmol_l,
        insulin_rate=0.0,
        sport_multiplier=1.0,
        sport_minutes_remaining=0.0,
    )

    # Create estimator and simulator
    model = PhysiologyModel()
    estimator = ExtendedKalmanFilterEstimator(
        model=model,
        model_config=model_config,
        initial_state=initial_state,
        estimator_config=EstimatorConfig(),
    )

    controller = ProportionalController()

    simulator = GlucoseSimulator(
        model=model,
        controller=controller,
        model_config=model_config,
        controller_config=controller_config,
        initial_state=initial_state,
        estimator=estimator,
    )

    # Queue all meals and boluses at the beginning
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
    measured_glucose = [v for _, v in window.glucose_reference]
    measured_times = [t for t, _ in window.glucose_reference]

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

    # Resample measured to match simulated times (nearest neighbor)
    resampled_measured = []
    for sim_t in simulated_times:
        idx = min(
            range(len(measured_times)),
            key=lambda i: abs(measured_times[i] - sim_t),
        )
        resampled_measured.append(measured_glucose[idx])

    # Compute metrics
    metrics = compute_metrics(resampled_measured, simulated_interstitium)

    return {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "duration_minutes": window.duration_minutes,
        "initial_glucose": window.initial_glucose_mmol_l,
        "simulated_times": simulated_times,
        "simulated_glucose": simulated_glucose,
        "simulated_interstitium": simulated_interstitium,
        "simulated_insulin": simulated_insulin,
        "measured_glucose": resampled_measured,
        "metrics": metrics,
        "meal_events": window.carb_replay_events,
        "bolus_events": window.insulin_reference,
    }


def plot_simulation_results(result: dict[str, Any], output_path: Path) -> None:
    """Create 3-subplot figure with glucose, insulin, and error metrics.

    Args:
        result: Dictionary with simulation results
        output_path: Path to save PNG
    """
    times = result["simulated_times"]
    sim_glucose = result["simulated_glucose"]
    sim_interstitium = result["simulated_interstitium"]
    measured = result["measured_glucose"]
    insulin = result["simulated_insulin"]
    meals = result["meal_events"]
    boluses = result["bolus_events"]
    metrics = result["metrics"]

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # Subplot 1: Glucose dynamics
    ax1 = axes[0]
    ax1.plot(
        times,
        sim_glucose,
        "b-",
        label="Simulated plasma glucose",
        linewidth=2,
    )
    ax1.plot(
        times,
        sim_interstitium,
        "g--",
        label="Simulated interstitium",
        linewidth=2,
    )
    ax1.scatter(
        times, measured, color="red", s=20, label="Measured CGM", alpha=0.6
    )

    # Mark meal events
    for meal_time, carbs in meals:
        if carbs > 0:
            ax1.axvline(
                meal_time,
                color="orange",
                linestyle=":",
                alpha=0.5,
                linewidth=1,
            )

    ax1.set_xlabel("Time (minutes)")
    ax1.set_ylabel("Glucose (mmol/L)")
    ax1.set_title(
        f"Glucose Dynamics - {result['user_id']} "
        f"({result['start_date']} to {result['end_date']})"
    )
    ax1.legend(loc="best")
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Insulin dynamics
    ax2 = axes[1]
    ax2.plot(
        times, insulin, "purple", linewidth=2, label="Insulin infusion rate"
    )

    # Mark bolus events
    for bolus_time, bolus_units in boluses:
        if bolus_units > 0:
            ax2.axvline(
                bolus_time,
                color="darkred",
                linestyle=":",
                alpha=0.7,
                linewidth=1,
            )

    ax2.set_xlabel("Time (minutes)")
    ax2.set_ylabel("Insulin rate (mU/min)")
    ax2.set_title("Insulin Infusion Rate")
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Error metrics
    ax3 = axes[2]
    errors = np.array(sim_interstitium) - np.array(measured)
    ax3.plot(times, errors, "red", linewidth=1.5, label="Simulation error")
    ax3.axhline(0, color="black", linestyle="-", linewidth=0.5)
    ax3.fill_between(times, errors, alpha=0.3, color="red")

    ax3.set_xlabel("Time (minutes)")
    ax3.set_ylabel("Error (mmol/L)")
    ax3.set_title(
        f"Simulation Error - RMSE: {metrics['rmse']:.2f}, "
        f"MAE: {metrics['mae']:.2f}, "
        f"Oscillations: {metrics['oscillation_count']}"
    )
    ax3.legend(loc="best")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close()


def main() -> None:
    """Run Phase 1 validation for all selected windows."""
    # Resolve paths
    project_root = Path(__file__).parent.parent
    data_path = project_root / "data" / "GlucoBench_benchmark_dataset.csv"
    windows_path = (
        project_root / "project_files" / "phase1_validation_windows.txt"
    )
    output_dir = project_root / "project_files" / "phase1_results"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 1 VALIDATION: TWO-COMPARTMENT MODEL ASSESSMENT")
    print("=" * 70)

    # Load benchmark data
    try:
        loader = GlucoBenchLoader(str(data_path))
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Failed to load benchmark data: {e}")
        return

    # Parse validation windows
    try:
        windows = parse_validation_windows_text(windows_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Failed to parse validation windows: {e}")
        return

    if not windows:
        print("❌ No validation windows found")
        return

    print(f"\n✓ Loaded {len(windows)} validation windows\n")

    # Run simulations and collect metrics
    all_metrics: list[dict[str, Any]] = []

    for window_idx, window in enumerate(windows, start=1):
        user_id = window["user_id"]
        start_date = window["start_date"]
        end_date = window["end_date"]

        print(
            f"[{window_idx}/{len(windows)}] Running: {user_id} "
            f"({start_date} to {end_date})... ",
            end="",
            flush=True,
        )

        try:
            result = simulate_window(loader, user_id, start_date, end_date)

            # Save plot
            plot_filename = (
                f"{user_id}_{start_date}_to_{end_date}" f"_validation.png"
            )
            plot_path = output_dir / plot_filename
            plot_simulation_results(result, plot_path)

            # Record metrics
            metrics_row = {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "duration_hours": (result["duration_minutes"] / 60.0),
                "initial_glucose": (f"{result['initial_glucose']:.2f}"),
                "rmse": f"{result['metrics']['rmse']:.3f}",
                "mae": f"{result['metrics']['mae']:.3f}",
                "mean_error": (f"{result['metrics']['mean_error']:.3f}"),
                "oscillations": result["metrics"]["oscillation_count"],
                "plot_file": plot_filename,
            }
            all_metrics.append(metrics_row)

            print(
                f"✓ RMSE={result['metrics']['rmse']:.3f}, "
                f"MAE={result['metrics']['mae']:.3f}"
            )

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    # Save metrics CSV
    if all_metrics:
        csv_path = output_dir / "phase1_validation_metrics.csv"
        fieldnames = [
            "user_id",
            "start_date",
            "end_date",
            "duration_hours",
            "initial_glucose",
            "rmse",
            "mae",
            "mean_error",
            "oscillations",
            "plot_file",
        ]

        with csv_path.open(mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_metrics)

        print(f"\n✓ Metrics saved to: {csv_path}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    if all_metrics:
        rmse_values = [float(row["rmse"]) for row in all_metrics]
        mae_values = [float(row["mae"]) for row in all_metrics]
        osc_values = [int(row["oscillations"]) for row in all_metrics]

        print(f"Windows analyzed: {len(all_metrics)}")
        print(f"Mean RMSE: {np.mean(rmse_values):.3f} mmol/L")
        print(f"Mean MAE:  {np.mean(mae_values):.3f} mmol/L")
        print(f"Total oscillations: {sum(osc_values)}")
        print(f"Output directory: {output_dir}")
    else:
        print("❌ No successful validations")

    print("=" * 70)


if __name__ == "__main__":
    main()
