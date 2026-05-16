"""Prediction quality metrics for glucose forecast comparisons."""

from dataclasses import dataclass
from collections.abc import Sequence

import numpy as np


@dataclass(frozen=True)
class PredictionMetrics:
    """Summary statistics for a prediction window."""

    rmse: float
    mard_percent: float
    peak_time_error_minutes: float
    sample_count: int


def compute_prediction_metrics(
    reference_time_minutes: Sequence[float],
    reference_glucose: Sequence[float],
    predicted_time_minutes: Sequence[float],
    predicted_glucose: Sequence[float],
) -> PredictionMetrics | None:
    """Compare a predicted glucose series against a reference series."""
    reference_time = np.asarray(reference_time_minutes, dtype=float)
    reference_values = np.asarray(reference_glucose, dtype=float)
    predicted_time = np.asarray(predicted_time_minutes, dtype=float)
    predicted_values = np.asarray(predicted_glucose, dtype=float)

    if (
        reference_time.size < 2
        or predicted_time.size < 2
        or reference_values.size != reference_time.size
        or predicted_values.size != predicted_time.size
    ):
        return None

    overlap_start = max(reference_time[0], predicted_time[0])
    overlap_end = min(reference_time[-1], predicted_time[-1])
    if overlap_end <= overlap_start:
        return None

    sample_mask = (reference_time >= overlap_start) & (
        reference_time <= overlap_end
    )
    sample_times = reference_time[sample_mask]
    if sample_times.size < 2:
        sample_mask = (predicted_time >= overlap_start) & (
            predicted_time <= overlap_end
        )
        sample_times = predicted_time[sample_mask]
    if sample_times.size < 2:
        return None

    predicted_samples = np.interp(
        sample_times,
        predicted_time,
        predicted_values,
    )
    reference_samples = np.interp(
        sample_times,
        reference_time,
        reference_values,
    )
    residuals = predicted_samples - reference_samples
    rmse = float(np.sqrt(np.mean(residuals**2)))

    valid_reference = np.abs(reference_samples) > 1e-9
    if np.any(valid_reference):
        mard_percent = float(
            np.mean(
                np.abs(residuals[valid_reference])
                / np.abs(reference_samples[valid_reference])
            )
            * 100.0
        )
    else:
        mard_percent = 0.0

    predicted_overlap = predicted_values[
        (predicted_time >= overlap_start) & (predicted_time <= overlap_end)
    ]
    predicted_overlap_time = predicted_time[
        (predicted_time >= overlap_start) & (predicted_time <= overlap_end)
    ]
    reference_overlap = reference_values[
        (reference_time >= overlap_start) & (reference_time <= overlap_end)
    ]
    reference_overlap_time = reference_time[
        (reference_time >= overlap_start) & (reference_time <= overlap_end)
    ]

    if not predicted_overlap.size or not reference_overlap.size:
        return None

    predicted_peak_time = float(
        predicted_overlap_time[int(np.argmax(predicted_overlap))]
    )
    reference_peak_time = float(
        reference_overlap_time[int(np.argmax(reference_overlap))]
    )

    return PredictionMetrics(
        rmse=rmse,
        mard_percent=mard_percent,
        peak_time_error_minutes=predicted_peak_time - reference_peak_time,
        sample_count=int(sample_times.size),
    )


def format_prediction_metrics(metrics: PredictionMetrics) -> str:
    """Format metrics for display under the glucose plot."""
    return (
        f"RMSE: {metrics.rmse:.2f} mmol/L\n"
        f"MARD: {metrics.mard_percent:.1f}%\n"
        f"Peak Time Error: {metrics.peak_time_error_minutes:+.0f} min"
    )
