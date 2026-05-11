"""Tests for validation metrics."""

from src.core.metrics import (
    compute_rmse,
    compute_time_in_range,
    count_hypoglycemia_events,
    count_hyperglycemia_events,
    generate_validation_report,
    summarize_insulin_therapy,
)


def test_compute_rmse() -> None:
    """RMSE should be zero for identical traces."""
    trace = [5.0, 6.0, 7.0, 5.5]

    rmse = compute_rmse(trace, trace)

    assert rmse == 0.0


def test_compute_rmse_simple_difference() -> None:
    """RMSE should compute correctly for offset traces."""
    trace1 = [5.0, 6.0, 7.0]
    trace2 = [6.0, 7.0, 8.0]

    rmse = compute_rmse(trace1, trace2)

    assert rmse == 1.0


def test_compute_time_in_range_all_in() -> None:
    """All values in range should return 100%."""
    glucose = [5.0, 6.0, 7.0, 8.0, 9.0]

    tir = compute_time_in_range(glucose, 3.9, 10.0)

    assert tir == 100.0


def test_compute_time_in_range_all_out() -> None:
    """No values in range should return 0%."""
    glucose = [2.0, 3.0, 15.0, 20.0]

    tir = compute_time_in_range(glucose, 3.9, 10.0)

    assert tir == 0.0


def test_compute_time_in_range_half() -> None:
    """Half in range should return 50%."""
    glucose = [5.0, 6.0, 2.0, 20.0]

    tir = compute_time_in_range(glucose, 3.9, 10.0)

    assert tir == 50.0


def test_count_hypoglycemia_events() -> None:
    """Count events below threshold."""
    glucose = [5.0, 3.5, 7.0, 3.0, 6.0]

    count = count_hypoglycemia_events(glucose, 3.9)

    assert count == 2


def test_count_hyperglycemia_events() -> None:
    """Count events above threshold."""
    glucose = [5.0, 12.0, 7.0, 11.0, 6.0]

    count = count_hyperglycemia_events(glucose, 10.0)

    assert count == 2


def test_generate_validation_report() -> None:
    """Report should contain all expected metrics."""
    simulated = [5.0, 6.0, 7.0, 8.0]
    actual = [5.0, 6.0, 7.0, 8.0]
    times = [0.0, 5.0, 10.0, 15.0]

    report = generate_validation_report(simulated, actual, times)

    assert "trace_length" in report
    assert "rmse_mmol_l" in report
    assert "time_in_range_percent" in report
    assert "simulated_hypoglycemia_events" in report
    assert "actual_hypoglycemia_events" in report
    assert report["rmse_mmol_l"] == 0.0
    assert report["trace_length"] == 4
    assert report["duration_minutes"] == 15.0


def test_summarize_insulin_therapy() -> None:
    """Insulin therapy summary should report counts and totals."""
    basal = [1.0, 0.9, 1.1]
    bolus = [0.0, 2.0, 0.0, 1.5]

    summary = summarize_insulin_therapy(basal, bolus)

    assert summary["basal_sample_count"] == 3
    assert summary["bolus_event_count"] == 2
    assert summary["mean_basal_units"] == 1.0
    assert summary["total_basal_units"] == 3.0
    assert summary["total_bolus_units"] == 3.5
    assert summary["max_basal_units"] == 1.1
    assert summary["max_bolus_units"] == 2.0
