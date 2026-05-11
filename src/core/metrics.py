"""Validation metrics for CGM simulation fidelity."""

import numpy as np


def compute_rmse(simulated: list[float], actual: list[float]) -> float:
    """Compute root mean squared error between simulated and actual glucose.

    Args:
        simulated: List of simulated glucose values.
        actual: List of actual glucose values.

    Returns:
        RMSE in mmol/L.

    Raises:
        ValueError: If lists have different lengths or are empty.
    """
    if len(simulated) != len(actual):
        raise ValueError("Simulated and actual must have equal length")
    if simulated == []:
        raise ValueError("Lists must not be empty")

    mse = np.mean([(s - a) ** 2 for s, a in zip(simulated, actual)])
    return float(np.sqrt(mse))


def compute_time_in_range(
    glucose_values: list[float],
    lower_bound: float = 3.9,
    upper_bound: float = 10.0,
) -> float:
    """Compute percentage of time glucose is within target range.

    Args:
        glucose_values: List of glucose measurements.
        lower_bound: Lower range bound in mmol/L.
        upper_bound: Upper range bound in mmol/L.

    Returns:
        Percentage of time in range (0–100).

    Raises:
        ValueError: If list is empty or bounds are invalid.
    """
    if glucose_values == []:
        raise ValueError("Glucose values list must not be empty")
    if lower_bound >= upper_bound:
        raise ValueError("lower_bound must be less than upper_bound")

    in_range = sum(
        1 for g in glucose_values if lower_bound <= g <= upper_bound
    )
    return 100.0 * in_range / len(glucose_values)


def count_hypoglycemia_events(
    glucose_values: list[float],
    threshold: float = 3.9,
) -> int:
    """Count number of glucose measurements below threshold.

    Args:
        glucose_values: List of glucose measurements.
        threshold: Hypoglycemia threshold in mmol/L.

    Returns:
        Count of readings below threshold.
    """
    return sum(1 for g in glucose_values if g < threshold)


def count_hyperglycemia_events(
    glucose_values: list[float],
    threshold: float = 10.0,
) -> int:
    """Count number of glucose measurements above threshold.

    Args:
        glucose_values: List of glucose measurements.
        threshold: Hyperglycemia threshold in mmol/L.

    Returns:
        Count of readings above threshold.
    """
    return sum(1 for g in glucose_values if g > threshold)


def summarize_insulin_therapy(
    insulin_basal_values: list[float],
    insulin_bolus_values: list[float],
) -> dict[str, float | int]:
    """Summarize insulin therapy logs from a replay window.

    Args:
        insulin_basal_values: Basal insulin samples from the dataset.
        insulin_bolus_values: Bolus insulin doses from the dataset.

    Returns:
        Summary metrics for the insulin therapy trace.

    Raises:
        ValueError: If both input lists are empty.
    """
    if insulin_basal_values == [] and insulin_bolus_values == []:
        raise ValueError("Insulin therapy lists must not both be empty")

    nonzero_bolus_values = [
        value for value in insulin_bolus_values if value > 0.0
    ]
    return {
        "basal_sample_count": len(insulin_basal_values),
        "bolus_event_count": len(nonzero_bolus_values),
        "mean_basal_units": (
            float(np.mean(insulin_basal_values))
            if insulin_basal_values
            else 0.0
        ),
        "total_basal_units": (
            float(np.sum(insulin_basal_values))
            if insulin_basal_values
            else 0.0
        ),
        "total_bolus_units": float(np.sum(nonzero_bolus_values)),
        "max_basal_units": (
            float(np.max(insulin_basal_values))
            if insulin_basal_values
            else 0.0
        ),
        "max_bolus_units": (
            float(np.max(nonzero_bolus_values))
            if nonzero_bolus_values
            else 0.0
        ),
    }


def generate_validation_report(
    simulated_glucose: list[float],
    actual_glucose: list[float],
    time_minutes: list[float] | None = None,
    insulin_basal_values: list[float] | None = None,
    insulin_bolus_values: list[float] | None = None,
) -> dict[str, float | int]:
    """Generate a comprehensive validation report.

    Args:
        simulated_glucose: Simulated glucose trace.
        actual_glucose: Actual (benchmark) glucose trace.
        time_minutes: Optional time stamps for context.
        insulin_basal_values: Optional basal insulin replay samples.
        insulin_bolus_values: Optional bolus insulin replay samples.

    Returns:
        Dictionary with all metrics.

    Raises:
        ValueError: If inputs are invalid or mismatched.
    """
    if len(simulated_glucose) != len(actual_glucose):
        raise ValueError("Simulated and actual traces must have equal length")
    if simulated_glucose == []:
        raise ValueError("Traces must not be empty")

    report: dict[str, float | int] = {
        "trace_length": len(simulated_glucose),
        "rmse_mmol_l": compute_rmse(simulated_glucose, actual_glucose),
        "time_in_range_percent": compute_time_in_range(simulated_glucose),
        "actual_time_in_range_percent": compute_time_in_range(actual_glucose),
        "simulated_hypoglycemia_events": count_hypoglycemia_events(
            simulated_glucose
        ),
        "actual_hypoglycemia_events": count_hypoglycemia_events(
            actual_glucose
        ),
        "simulated_hyperglycemia_events": count_hyperglycemia_events(
            simulated_glucose
        ),
        "actual_hyperglycemia_events": count_hyperglycemia_events(
            actual_glucose
        ),
    }

    if time_minutes:
        duration_minutes = time_minutes[-1] - time_minutes[0]
        report["duration_minutes"] = duration_minutes

    if insulin_basal_values is not None or insulin_bolus_values is not None:
        report.update(
            summarize_insulin_therapy(
                insulin_basal_values or [],
                insulin_bolus_values or [],
            )
        )

    return report
