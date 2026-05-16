#!/usr/bin/env python3
"""Tune model and estimator parameters against benchmark replay data.

The script performs a small grid search over user-provided or default
parameter ranges, replays one or more GlucoBench validation windows, and
reports the candidate with the lowest glucose-trace error.

Usage:
    python scripts/tune_parameters.py
    python scripts/tune_parameters.py --window U001 2024-09-01 2024-09-09
    python scripts/tune_parameters.py \
        --parameter model.glucose_decay=0.010,0.015,0.020
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from itertools import product
import argparse
import csv
import json
from pathlib import Path
import sys


def _ensure_project_root_on_sys_path() -> None:
    """Allow running the script directly from the repository root."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


_ensure_project_root_on_sys_path()

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.benchmark_loader import ValidationWindowData
from src.core.controller import ProportionalController
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.model import PhysiologyModel
from src.core.prediction_metrics import PredictionMetrics
from src.core.prediction_metrics import compute_prediction_metrics
from src.core.simulator import GlucoseSimulator
from src.core.state import ControllerConfig
from src.core.state import EstimatorConfig
from src.core.state import IntegratorConfig
from src.core.state import ModelConfig
from src.core.state import SimulationState
from src.core.utilities import collect_due_carb_events
from src.core.utilities import collect_due_insulin_events


DEFAULT_PARAMETER_GRID: dict[str, list[float]] = {
    "model.glucose_decay": [0.010, 0.015, 0.020],
    "model.insulin_sensitivity": [0.0004, 0.0006, 0.0008],
    "model.insulin_response_gain": [0.20, 0.32, 0.45],
    "estimator.process_noise_scale": [0.01, 0.02, 0.04],
    "estimator.measurement_noise_variance": [0.04, 0.09, 0.16],
}

MODEL_PARAMETER_FIELDS: dict[str, str] = {
    "model.dt_minutes": "dt_minutes",
    "model.plasma_volume_ml": "plasma_volume_ml",
    "model.glucose_basal": "glucose_basal",
    "model.insulin_basal": "insulin_basal",
    "model.glucose_decay": "glucose_decay",
    "model.insulin_decay": "insulin_decay",
    "model.insulin_sensitivity": "insulin_sensitivity",
    "model.insulin_response_gain": "insulin_response_gain",
    "model.stomach_tau_minutes": "stomach_tau_minutes",
    "model.intestine_tau_minutes": "intestine_tau_minutes",
    "model.carb_to_glucose_gain": "carb_to_glucose_gain",
    "model.interstitium_tau_minutes": "interstitium_tau_minutes",
    "model.insulin_subq_fraction": "insulin_subq_fraction",
    "model.insulin_subq_absorption_tau_minutes": (
        "insulin_subq_absorption_tau_minutes"
    ),
    "model.min_glucose": "min_glucose",
    "model.max_glucose": "max_glucose",
    "model.min_insulin": "min_insulin",
    "model.max_insulin": "max_insulin",
}

ESTIMATOR_PARAMETER_FIELDS: dict[str, str] = {
    "estimator.initial_covariance": "initial_covariance",
    "estimator.process_noise_scale": "process_noise_scale",
    "estimator.insulin_process_noise": "insulin_process_noise",
    "estimator.measurement_noise_variance": "measurement_noise_variance",
    "estimator.finite_difference_step": "finite_difference_step",
    "estimator.minimum_covariance": "minimum_covariance",
}


@dataclass(frozen=True)
class TuningWindowSpec:
    """User-selected benchmark window to tune against."""

    user_id: str
    start_day: str
    end_day: str


@dataclass(frozen=True)
class TuningResult:
    """Score and metrics for one candidate parameter combination."""

    score: float
    metrics: PredictionMetrics | None
    parameters: dict[str, float]
    mean_abs_insulin_rate: float
    max_insulin_rate: float


def _parse_float_list(values_text: str) -> list[float]:
    """Parse a comma-separated list of numeric values."""
    values = [item.strip() for item in values_text.split(",") if item.strip()]
    if not values:
        raise ValueError("Parameter grid must contain at least one value")

    parsed: list[float] = []
    for value_text in values:
        try:
            parsed.append(float(value_text))
        except ValueError as exc:
            raise ValueError(
                f"Invalid numeric parameter value: {value_text}"
            ) from exc
    return parsed


def _parse_parameter_spec(spec: str) -> tuple[str, list[float]]:
    """Parse a single `name=value1,value2` parameter-grid specification."""
    if "=" not in spec:
        raise ValueError(
            "Parameter specifications must use name=value1,value2 format"
        )

    name, values_text = spec.split("=", 1)
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Parameter name must not be empty")
    return normalized_name, _parse_float_list(values_text)


def _collect_due_measurement(
    measurement_points: list[tuple[float, float]],
    start_index: int,
    current_time_minutes: float,
) -> tuple[float | None, int]:
    """Return the latest measurement due at the current replay time."""
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


def _build_default_model_config(window: ValidationWindowData) -> ModelConfig:
    """Derive a baseline model configuration from replayed insulin data."""
    basal_series = window.basal_reference or []
    insulin_series = window.insulin_reference or []
    has_pump_basal = any(point[1] > 0.0 for point in basal_series)
    has_bolus = any(point[1] > 0.0 for point in insulin_series)

    if has_pump_basal:
        return replace(
            ModelConfig(),
            insulin_basal=0.0,
            insulin_response_gain=0.0,
        )
    if not has_pump_basal and not has_bolus:
        return replace(
            ModelConfig(),
            insulin_basal=10.0,
            insulin_response_gain=0.32,
        )
    return replace(
        ModelConfig(),
        insulin_basal=10.0,
        insulin_response_gain=0.0,
    )


def _apply_parameter_overrides(
    base_model_config: ModelConfig,
    base_estimator_config: EstimatorConfig,
    overrides: dict[str, float],
) -> tuple[ModelConfig, EstimatorConfig]:
    """Apply parameter overrides to model and estimator configurations."""
    model_kwargs: dict[str, float | None] = {}
    estimator_kwargs: dict[str, float | None] = {}
    for name, value in overrides.items():
        if name in MODEL_PARAMETER_FIELDS:
            model_kwargs[MODEL_PARAMETER_FIELDS[name]] = value
        elif name in ESTIMATOR_PARAMETER_FIELDS:
            estimator_kwargs[ESTIMATOR_PARAMETER_FIELDS[name]] = value
        else:
            raise ValueError(f"Unsupported parameter name: {name}")

    model_config = replace(base_model_config, **model_kwargs)
    estimator_config = replace(base_estimator_config, **estimator_kwargs)
    return model_config, estimator_config


def _build_simulator_for_window(
    window: ValidationWindowData,
    model_config: ModelConfig,
    estimator_config: EstimatorConfig,
    integrator_method: str,
) -> GlucoseSimulator:
    """Create a simulator aligned with the selected validation window."""
    initial_glucose = window.initial_glucose_mmol_l
    initial_state = SimulationState(
        time_minutes=0.0,
        glucose=initial_glucose,
        insulin=model_config.insulin_basal,
        insulin_subcutaneous=0.0,
        carb_stomach=0.0,
        carb_intestine=0.0,
        interstitium=initial_glucose,
        insulin_rate=0.0,
        insulin_subq_rate=0.0,
        insulin_subq_minutes_remaining=0.0,
        basal_insulin_rate=0.0,
    )
    model = PhysiologyModel(
        integrator_config=IntegratorConfig(method=integrator_method),
    )
    return GlucoseSimulator(
        model=model,
        controller=ProportionalController(),
        model_config=model_config,
        controller_config=ControllerConfig(),
        initial_state=initial_state,
        estimator=ExtendedKalmanFilterEstimator(
            model=model,
            model_config=model_config,
            initial_state=initial_state,
            estimator_config=estimator_config,
        ),
        integrator_config=IntegratorConfig(method=integrator_method),
    )


def _replay_window(
    simulator: GlucoseSimulator,
    window: ValidationWindowData,
) -> tuple[list[float], list[float], list[float]]:
    """Replay one validation window and return time, glucose, and insulin."""
    measurement_points = list(window.measurement_reference)
    carb_points = list(window.carb_replay_events)
    basal_points = list(window.basal_reference)
    insulin_points = list(window.insulin_reference)

    measurement_index = 0
    carb_index = 0
    basal_index = 0
    insulin_index = 0

    time_minutes: list[float] = [simulator.current_state.time_minutes]
    glucose_values: list[float] = [simulator.current_state.interstitium]
    insulin_values: list[float] = [simulator.current_state.insulin]

    epsilon = 1e-9
    while simulator.current_state.time_minutes < window.duration_minutes - epsilon:
        current_time = simulator.current_state.time_minutes

        due_basal, next_basal_index = collect_due_insulin_events(
            basal_points,
            basal_index,
            current_time,
        )
        basal_index = next_basal_index
        if due_basal:
            simulator.set_basal_rate(due_basal[-1])

        due_insulin, next_insulin_index = collect_due_insulin_events(
            insulin_points,
            insulin_index,
            current_time,
        )
        insulin_index = next_insulin_index
        if due_insulin:
            simulator.queue_bolus(sum(due_insulin))

        due_carbs, next_carb_index = collect_due_carb_events(
            carb_points,
            carb_index,
            current_time,
        )
        carb_index = next_carb_index
        if due_carbs:
            simulator.queue_meal(sum(due_carbs))

        measured_interstitium, next_measurement_index = _collect_due_measurement(
            measurement_points,
            measurement_index,
            current_time,
        )
        measurement_index = next_measurement_index
        if measured_interstitium is None:
            measured_interstitium = simulator.current_state.interstitium

        snapshot = simulator.step_replay(measured_interstitium)
        time_minutes.append(snapshot.time_minutes)
        glucose_values.append(snapshot.interstitium)
        insulin_values.append(snapshot.insulin)

    return time_minutes, glucose_values, insulin_values


def _evaluate_candidate(
    window: ValidationWindowData,
    overrides: dict[str, float],
    integrator_method: str,
    estimator_config: EstimatorConfig,
) -> TuningResult:
    """Run one replay candidate and compute its tuning score."""
    base_model_config = _build_default_model_config(window)
    model_config, tuned_estimator_config = _apply_parameter_overrides(
        base_model_config,
        estimator_config,
        overrides,
    )
    simulator = _build_simulator_for_window(
        window=window,
        model_config=model_config,
        estimator_config=tuned_estimator_config,
        integrator_method=integrator_method,
    )

    time_minutes, glucose_values, insulin_values = _replay_window(
        simulator,
        window,
    )
    metrics = compute_prediction_metrics(
        [point[0] for point in window.glucose_reference],
        [point[1] for point in window.glucose_reference],
        time_minutes,
        glucose_values,
    )
    if metrics is None:
        raise ValueError("Validation window did not produce comparable data")

    score = metrics.rmse
    mean_abs_insulin_rate = sum(abs(value) for value in insulin_values) / len(
        insulin_values
    )
    max_insulin_rate = max(insulin_values)
    return TuningResult(
        score=score,
        metrics=metrics,
        parameters=dict(overrides),
        mean_abs_insulin_rate=mean_abs_insulin_rate,
        max_insulin_rate=max_insulin_rate,
    )


def _build_windows(
    loader: GlucoBenchLoader,
    window_specs: Sequence[TuningWindowSpec] | None,
) -> list[ValidationWindowData]:
    """Resolve user-selected windows or fall back to the first dataset span."""
    if window_specs:
        return [
            loader.build_validation_window_for_days(
                spec.user_id,
                spec.start_day,
                spec.end_day,
            )
            for spec in window_specs
        ]

    user_ids = loader.get_user_ids()
    if not user_ids:
        raise ValueError("Benchmark dataset does not contain any users")

    first_user = user_ids[0]
    user_days = loader.get_user_days(first_user)
    if not user_days:
        raise ValueError(
            f"Benchmark dataset does not contain days for {first_user}"
        )

    return [
        loader.build_validation_window_for_days(
            first_user,
            user_days[0],
            user_days[-1],
        )
    ]


def _iter_parameter_combinations(
    parameter_grid: dict[str, list[float]],
) -> list[dict[str, float]]:
    """Expand a parameter grid into concrete override dictionaries."""
    names = list(parameter_grid.keys())
    value_sets = [parameter_grid[name] for name in names]
    combinations: list[dict[str, float]] = []
    for values in product(*value_sets):
        combinations.append(dict(zip(names, values, strict=True)))
    return combinations


def _aggregate_window_scores(
    results: list[TuningResult],
) -> TuningResult:
    """Average metrics across windows while preserving the tested parameters."""
    if not results:
        raise ValueError("At least one result is required")

    score = sum(result.score for result in results) / len(results)
    mean_abs_insulin_rate = sum(
        result.mean_abs_insulin_rate for result in results
    ) / len(results)
    max_insulin_rate = max(result.max_insulin_rate for result in results)

    metrics = None
    if all(result.metrics is not None for result in results):
        assert results[0].metrics is not None
        metrics = PredictionMetrics(
            rmse=sum(result.metrics.rmse for result in results if result.metrics)
            / len(results),
            mard_percent=
            sum(
                result.metrics.mard_percent
                for result in results
                if result.metrics
            )
            / len(results),
            peak_time_error_minutes=
            sum(
                result.metrics.peak_time_error_minutes
                for result in results
                if result.metrics
            )
            / len(results),
            sample_count=sum(
                result.metrics.sample_count for result in results if result.metrics
            ),
        )

    return TuningResult(
        score=score,
        metrics=metrics,
        parameters=dict(results[0].parameters),
        mean_abs_insulin_rate=mean_abs_insulin_rate,
        max_insulin_rate=max_insulin_rate,
    )


def _format_result_row(result: TuningResult) -> str:
    """Format one result row for console output."""
    metrics = result.metrics
    metric_text = "n/a"
    if metrics is not None:
        metric_text = (
            f"RMSE={metrics.rmse:.3f} "
            f"MARD={metrics.mard_percent:.1f}% "
            f"Peak={metrics.peak_time_error_minutes:+.0f}min"
        )
    parameter_text = ", ".join(
        f"{name}={value:g}" for name, value in sorted(result.parameters.items())
    )
    return (
        f"score={result.score:.3f} "
        f"mean|insulin|={result.mean_abs_insulin_rate:.3f} "
        f"max insulin={result.max_insulin_rate:.3f} "
        f"{metric_text} "
        f"{parameter_text}"
    )


def _write_results_csv(path: Path, results: list[TuningResult]) -> None:
    """Write the evaluated candidates to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    parameter_names: list[str] = []
    for result in results:
        for name in result.parameters:
            if name not in parameter_names:
                parameter_names.append(name)

    fieldnames = [
        "score",
        "rmse",
        "mard_percent",
        "peak_time_error_minutes",
        "sample_count",
        "mean_abs_insulin_rate",
        "max_insulin_rate",
    ] + parameter_names
    with path.open(mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row: dict[str, float | int] = {
                "score": result.score,
                "mean_abs_insulin_rate": result.mean_abs_insulin_rate,
                "max_insulin_rate": result.max_insulin_rate,
            }
            if result.metrics is not None:
                row.update(
                    {
                        "rmse": result.metrics.rmse,
                        "mard_percent": result.metrics.mard_percent,
                        "peak_time_error_minutes": (
                            result.metrics.peak_time_error_minutes
                        ),
                        "sample_count": result.metrics.sample_count,
                    }
                )
            for name in parameter_names:
                row[name] = result.parameters.get(name, 0.0)
            writer.writerow(row)


def _build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the tuning utility."""
    parser = argparse.ArgumentParser(
        description=(
            "Grid-search model and estimator parameters against benchmark "
            "replay windows."
        ),
    )
    parser.add_argument(
        "--data",
        default="data/CGM.csv",
        help="Path to the GlucoBench CSV dataset.",
    )
    parser.add_argument(
        "--window",
        action="append",
        nargs=3,
        metavar=("USER_ID", "START_DAY", "END_DAY"),
        help=(
            "Validation window to replay, repeated as needed. If omitted, "
            "the script uses the first user and full available day range."
        ),
    )
    parser.add_argument(
        "--parameter",
        action="append",
        default=[],
        help="Parameter grid as name=value1,value2 and can be repeated.",
    )
    parser.add_argument(
        "--integrator",
        default="RK45",
        choices=["RK45", "DOP853", "BDF"],
        help="Integrator method passed into the simulator builder.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of best candidates to print.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional CSV file path for the full tuning table.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional JSON file path for the best candidate summary.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the parameter sweep and report the best candidate."""
    parser = _build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.top_n <= 0:
        print("Error: --top-n must be positive")
        return 1

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: dataset not found at {data_path}")
        return 1

    loader = GlucoBenchLoader(data_path)
    window_specs = None
    if args.window:
        window_specs = [
            TuningWindowSpec(user_id=user, start_day=start, end_day=end)
            for user, start, end in args.window
        ]
    windows = _build_windows(loader, window_specs)

    parameter_grid = dict(DEFAULT_PARAMETER_GRID)
    if args.parameter:
        parameter_grid = {}
        for spec in args.parameter:
            name, values = _parse_parameter_spec(spec)
            parameter_grid[name] = values

    invalid_names = [
        name
        for name in parameter_grid
        if name not in MODEL_PARAMETER_FIELDS
        and name not in ESTIMATOR_PARAMETER_FIELDS
    ]
    if invalid_names:
        print(
            "Error: unsupported parameter names: "
            + ", ".join(sorted(invalid_names))
        )
        return 1

    candidate_overrides = _iter_parameter_combinations(parameter_grid)
    estimator_config = EstimatorConfig()
    results: list[TuningResult] = []

    print(f"Loaded {len(windows)} validation window(s) from {data_path}")
    print(f"Evaluating {len(candidate_overrides)} candidate combinations...\n")

    for candidate_index, overrides in enumerate(candidate_overrides, start=1):
        window_results: list[TuningResult] = []
        for window in windows:
            window_results.append(
                _evaluate_candidate(
                    window=window,
                    overrides=overrides,
                    integrator_method=args.integrator,
                    estimator_config=estimator_config,
                )
            )
        combined = _aggregate_window_scores(window_results)
        results.append(combined)
        print(
            f"[{candidate_index:>3}/{len(candidate_overrides)}] "
            f"{_format_result_row(combined)}"
        )

    results.sort(key=lambda result: result.score)
    best = results[0]

    print("\nTop candidates:")
    for candidate in results[: args.top_n]:
        print(_format_result_row(candidate))

    print("\nBest candidate:")
    print(_format_result_row(best))

    if args.output_csv:
        csv_path = Path(args.output_csv)
        _write_results_csv(csv_path, results)
        print(f"Wrote tuning table to {csv_path}")

    if args.output_json:
        json_path = Path(args.output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "best": {
                "score": best.score,
                "mean_abs_insulin_rate": best.mean_abs_insulin_rate,
                "max_insulin_rate": best.max_insulin_rate,
                "metrics": None if best.metrics is None else {
                    "rmse": best.metrics.rmse,
                    "mard_percent": best.metrics.mard_percent,
                    "peak_time_error_minutes": (
                        best.metrics.peak_time_error_minutes
                    ),
                    "sample_count": best.metrics.sample_count,
                },
                "parameters": best.parameters,
            },
            "window_count": len(windows),
            "candidate_count": len(results),
        }
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote best-candidate summary to {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())