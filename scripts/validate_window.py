"""CLI tool for validation metrics on GlucoBench windows."""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.metrics import generate_validation_report
from src.core.utilities import collect_due_carb_events
from src.main import build_simulator


def collect_due_measurement(
    measurement_points: list[tuple[float, float]],
    start_index: int,
    current_time_minutes: float,
) -> tuple[float | None, int]:
    """Return the latest measurement due at the current step time."""
    measurement_index = start_index
    latest_measurement: float | None = None
    epsilon = 1e-9
    while measurement_index < len(measurement_points):
        point_time, value = measurement_points[measurement_index]
        if point_time <= current_time_minutes + epsilon:
            latest_measurement = value
            measurement_index += 1
            continue
        break
    return latest_measurement, measurement_index


def main() -> int:
    """Run validation against a GlucoBench window and report metrics."""
    csv_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "GlucoBench_benchmark_dataset.csv"
    )

    if not csv_path.exists():
        print(f"Error: Benchmark CSV not found at {csv_path}")
        return 1

    try:
        loader = GlucoBenchLoader(csv_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading benchmark data: {exc}")
        return 1

    # Default to first user and first day
    user_ids = loader.get_user_ids()
    if not user_ids:
        print("Error: No users found in benchmark data")
        return 1

    user_id = user_ids[0]
    print(f"Selected user: {user_id}")

    try:
        days = loader.get_user_days(user_id)
    except ValueError as exc:
        print(f"Error getting days: {exc}")
        return 1

    if not days:
        print(f"Error: No days found for user {user_id}")
        return 1

    start_day = days[0]
    end_day = days[0]  # Single day for quick test
    print(f"Selected window: {start_day} to {end_day}")

    try:
        window = loader.build_validation_window_for_days(
            user_id, start_day, end_day
        )
    except ValueError as exc:
        print(f"Error building validation window: {exc}")
        return 1

    print(
        f"\nWindow duration: {window.duration_minutes:.0f} minutes"
        f" ({window.duration_minutes / 60:.1f} hours)"
    )
    print(f"Initial glucose: {window.initial_glucose_mmol_l:.2f} mmol/L")
    print(f"Measurement points: {len(window.measurement_reference)}")
    print(f"Carb events: {len(window.carb_replay_events)}")
    print(f"Basal insulin samples: {len(window.insulin_basal_reference)}")
    print(f"Bolus insulin events: {len(window.insulin_reference)}")

    # Build and run simulator
    simulator = build_simulator(
        integrator_method="RK45",
        initial_glucose_mmol_l=window.initial_glucose_mmol_l,
    )

    # Replay the window
    dt_minutes = simulator.model_config.dt_minutes
    steps_required = int(window.duration_minutes / dt_minutes)

    print(f"\nRunning validation replay ({steps_required} steps)...")

    carb_index = 0
    measurement_index = 0

    for step in range(steps_required):
        # Collect due carbs
        current_time = simulator.current_state.time_minutes
        due_carbs, carb_index = collect_due_carb_events(
            window.carb_replay_events,
            carb_index,
            current_time,
        )

        for carbs in due_carbs:
            simulator.queue_meal(carbs)

        # Collect due measurements
        measured_glucose, measurement_index = collect_due_measurement(
            window.measurement_reference,
            measurement_index,
            current_time,
        )

        # Step
        simulator.step(measured_interstitium=measured_glucose)

        if (step + 1) % 100 == 0:
            progress_pct = 100.0 * (step + 1) / steps_required
            print(f"  Progress: {step + 1}/{steps_required} ({progress_pct:.0f}%)")

    # Extract simulated trace
    time, glucose_sim, _, _ = simulator.get_history_arrays()

    # Extract actual trace (from measurement_reference)
    glucose_actual = [value for _, value in window.measurement_reference]

    # Resample simulated trace to match actual trace timing
    actual_times = [time_pt for time_pt, _ in window.measurement_reference]
    glucose_sim_at_measurements = []
    for actual_time in actual_times:
        # Find closest simulated time
        closest_idx = min(
            range(len(time)), key=lambda i: abs(time[i] - actual_time)
        )
        glucose_sim_at_measurements.append(glucose_sim[closest_idx])

    # Generate report
    print("\n" + "=" * 70)
    print("VALIDATION METRICS REPORT")
    print("=" * 70)

    report = generate_validation_report(
        glucose_sim_at_measurements,
        glucose_actual,
        actual_times,
        insulin_basal_values=[value for _, value in window.insulin_basal_reference],
        insulin_bolus_values=[value for _, value in window.insulin_reference],
    )

    print(f"\nTrace length: {report['trace_length']} measurements")
    print(f"Duration: {report.get('duration_minutes', 'N/A'):.0f} minutes")
    print(
        f"\n{'RMSE (simulated vs actual)':<40} "
        f"{report['rmse_mmol_l']:.3f} mmol/L"
    )
    print(f"\n{'Time In Range (3.9–10.0 mmol/L)':<40}")
    print(
        f"  {'Simulated':<35} "
        f"{report['time_in_range_percent']:.1f}%"
    )
    print(
        f"  {'Actual':<35} "
        f"{report['actual_time_in_range_percent']:.1f}%"
    )
    print(f"\n{'Hypoglycemia events (<3.9 mmol/L)':<40}")
    print(
        f"  {'Simulated':<35} "
        f"{report['simulated_hypoglycemia_events']} events"
    )
    print(
        f"  {'Actual':<35} "
        f"{report['actual_hypoglycemia_events']} events"
    )
    print(f"\n{'Hyperglycemia events (>10.0 mmol/L)':<40}")
    print(
        f"  {'Simulated':<35} "
        f"{report['simulated_hyperglycemia_events']} events"
    )
    print(
        f"  {'Actual':<35} "
        f"{report['actual_hyperglycemia_events']} events"
    )

    print(f"\n{'Insulin therapy summary':<40}")
    print(
        f"  {'Basal samples':<35} {report['basal_sample_count']} samples"
    )
    print(
        f"  {'Basal mean':<35} {report['mean_basal_units']:.3f} units"
    )
    print(
        f"  {'Basal total':<35} {report['total_basal_units']:.3f} units"
    )
    print(
        f"  {'Bolus events':<35} {report['bolus_event_count']} events"
    )
    print(
        f"  {'Bolus total':<35} {report['total_bolus_units']:.3f} units"
    )

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
