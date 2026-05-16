"""Tests for glucose prediction metrics."""

from src.core.prediction_metrics import compute_prediction_metrics
from src.core.prediction_metrics import format_prediction_metrics


def test_prediction_metrics_compute_perfect_match() -> None:
    """A perfect prediction should report zero error metrics."""
    metrics = compute_prediction_metrics(
        reference_time_minutes=[0.0, 5.0, 10.0],
        reference_glucose=[5.0, 6.0, 7.0],
        predicted_time_minutes=[0.0, 5.0, 10.0],
        predicted_glucose=[5.0, 6.0, 7.0],
    )

    assert metrics is not None
    assert metrics.rmse == 0.0
    assert metrics.mard_percent == 0.0
    assert metrics.peak_time_error_minutes == 0.0


def test_prediction_metrics_report_peak_time_shift() -> None:
    """Peak time error should reflect a shifted prediction peak."""
    metrics = compute_prediction_metrics(
        reference_time_minutes=[0.0, 5.0, 10.0, 15.0],
        reference_glucose=[5.0, 7.0, 9.0, 8.0],
        predicted_time_minutes=[0.0, 5.0, 10.0, 15.0],
        predicted_glucose=[5.0, 6.0, 8.0, 10.0],
    )

    assert metrics is not None
    assert metrics.peak_time_error_minutes == 5.0
    assert "RMSE" in format_prediction_metrics(metrics)