"""Embedded Matplotlib charts for the CustomTkinter dashboard."""

from datetime import datetime
from datetime import timedelta
from collections.abc import Sequence

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import AutoLocator
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import MultipleLocator
import customtkinter as ctk

from src.core.utilities import sanitize_reference_points

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DAY_TICK_INTERVAL_MINUTES = 24.0 * 60.0


def format_day_label(origin: datetime, time_minutes: float) -> str:
    """Format a minute offset as a human-readable day label."""
    current_time = origin + timedelta(minutes=time_minutes)
    return current_time.strftime("%Y-%m-%d")


class PlotFrame(ctk.CTkFrame):
    """Displays glucose and insulin trajectories in two synchronized charts."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Create chart widgets and visual style."""
        super().__init__(master)

        self.figure = Figure(figsize=(8.0, 5.2), dpi=100)
        self.ax_glucose = self.figure.add_subplot(211)
        self.ax_insulin = self.figure.add_subplot(212, sharex=self.ax_glucose)
        self.ax_carb = self.ax_glucose.twinx()
        self._time_origin: datetime | None = None

        self.ax_glucose.set_title("Glucose and Insulin Dynamics")
        self.ax_glucose.set_ylabel("Glucose [mmol/L]")
        self.ax_carb.set_ylabel("Carbs [g]")
        self.ax_insulin.set_ylabel("Insulin [uU/mL]")
        self.ax_insulin.set_xlabel("Time [min]")

        self.line_glucose = self.ax_glucose.plot(
            [],
            [],
            color="#D7263D",
            linewidth=2.0,
            label="Plasma Glucose",
        )[0]
        self.line_interstitium = self.ax_glucose.plot(
            [],
            [],
            color="#F08A5D",
            linewidth=2.0,
            linestyle="--",
            alpha=0.9,
            label="Interstitial (sim CGM)",
        )[0]
        self.line_glucose_prediction = self.ax_glucose.plot(
            [],
            [],
            color="#6C757D",
            linewidth=2.0,
            linestyle=":",
            alpha=0.6,
            label="Prediction",
        )[0]
        self.line_glucose_actual = self.ax_glucose.plot(
            [],
            [],
            color="#2E86AB",
            linewidth=1.8,
            linestyle="--",
            label="Actual Glucose (CGM)",
        )[0]
        self.line_carb_reference = self.ax_carb.plot(
            [],
            [],
            linestyle="None",
            marker="^",
            markersize=6,
            color="#FF9F1C",
            label="Carbs (Ref)",
        )[0]
        self.line_insulin = self.ax_insulin.plot(
            [],
            [],
            color="#1B998B",
            linewidth=2.0,
            label="Simulated Insulin",
        )[0]
        self.line_insulin_basal = self.ax_insulin.plot(
            [],
            [],
            color="#6C757D",
            linewidth=1.8,
            linestyle="-",
            alpha=0.85,
            drawstyle="steps-post",
            label="Basal Insulin (Ref)",
        )[0]
        self.line_insulin_bolus = self.ax_insulin.plot(
            [],
            [],
            color="#E63946",
            linestyle="None",
            marker="v",
            markersize=7,
            label="Bolus Insulin (Ref)",
        )[0]
        self.line_insulin_smoothed = self.ax_insulin.plot(
            [],
            [],
            color="#3C6E71",
            linewidth=2.0,
            linestyle="--",
            alpha=0.8,
            label="Smoothed Insulin",
        )[0]
        self.line_insulin_prediction = self.ax_insulin.plot(
            [],
            [],
            color="#6C757D",
            linewidth=2.0,
            linestyle=":",
            alpha=0.6,
            label="Prediction",
        )[0]

        self.ax_glucose.grid(alpha=0.2)
        self.ax_insulin.grid(alpha=0.2)
        self._refresh_glucose_legend()
        self.ax_insulin.legend(loc="upper right")
        self.figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(  # type: ignore[no-untyped-call]
            self.figure,
            master=self,
        )
        tk_widget = (
            self.canvas.get_tk_widget()  # type: ignore[no-untyped-call]
        )
        self.canvas_widget = tk_widget
        self.canvas_widget.pack(fill="both", expand=True, padx=8, pady=8)

    def set_time_origin(self, timestamp_text: str | None) -> None:
        """Switch the x-axis between minute offsets and day timestamps."""
        if not timestamp_text:
            self._time_origin = None
            self.ax_glucose.xaxis.set_major_locator(AutoLocator())
            self.ax_glucose.xaxis.set_major_formatter(
                FuncFormatter(lambda x, _: f"{x:.0f}")
            )
            self.ax_insulin.xaxis.set_major_locator(AutoLocator())
            self.ax_insulin.xaxis.set_major_formatter(
                FuncFormatter(lambda x, _: f"{x:.0f}")
            )
            self.ax_insulin.set_xlabel("Time [min]")
            self.canvas.draw_idle()  # type: ignore[no-untyped-call]
            return

        self._time_origin = datetime.strptime(timestamp_text, TIMESTAMP_FORMAT)
        self.ax_glucose.xaxis.set_major_locator(
            MultipleLocator(DAY_TICK_INTERVAL_MINUTES)
        )
        self.ax_glucose.xaxis.set_major_formatter(
            FuncFormatter(self._format_timestamp_tick)
        )
        self.ax_insulin.xaxis.set_major_locator(
            MultipleLocator(DAY_TICK_INTERVAL_MINUTES)
        )
        self.ax_insulin.xaxis.set_major_formatter(
            FuncFormatter(self._format_timestamp_tick)
        )
        self.ax_insulin.set_xlabel("Timestamp [day]")
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def _format_timestamp_tick(self, x_value: float, _: int) -> str:
        """Format a tick value as a human-readable day label."""
        if self._time_origin is None:
            return f"{x_value:.0f}"
        return format_day_label(self._time_origin, x_value)

    def _refresh_glucose_legend(self) -> None:
        """Refresh combined legend for glucose and carb overlays."""
        glucose_handles, glucose_labels = (
            self.ax_glucose.get_legend_handles_labels()
        )
        carb_handles, carb_labels = self.ax_carb.get_legend_handles_labels()
        self.ax_glucose.legend(
            glucose_handles + carb_handles,
            glucose_labels + carb_labels,
            loc="upper right",
        )

    def update_plot(
        self,
        time_minutes: list[float],
        glucose_values: list[float],
        insulin_values: list[float],
        interstitium_values: list[float] | None = None,
        actual_glucose_reference: Sequence[tuple[float, float]] | None = None,
        carb_reference: Sequence[tuple[float, float]] | None = None,
        basal_reference: Sequence[tuple[float, float]] | None = None,
        insulin_reference: Sequence[tuple[float, float]] | None = None,
        prediction_time: list[float] | None = None,
        prediction_glucose: list[float] | None = None,
        prediction_insulin: list[float] | None = None,
        smoothed_insulin_time: list[float] | None = None,
        smoothed_insulin_values: list[float] | None = None,
    ) -> None:
        """Refresh line data and autoscale axes."""
        if not time_minutes:
            return

        glucose_overlay = sanitize_reference_points(actual_glucose_reference)
        carb_overlay = sanitize_reference_points(carb_reference)

        glucose_ref_time = [point[0] for point in glucose_overlay]
        glucose_ref_values = [point[1] for point in glucose_overlay]
        carb_ref_time = [point[0] for point in carb_overlay]
        carb_ref_values = [point[1] for point in carb_overlay]
        basal_overlay = sanitize_reference_points(basal_reference)
        bolus_overlay = sanitize_reference_points(insulin_reference)
        basal_time = [point[0] for point in basal_overlay]
        basal_values = [point[1] for point in basal_overlay]
        bolus_time = [point[0] for point in bolus_overlay]
        bolus_values = [point[1] for point in bolus_overlay]

        self.line_glucose.set_data(time_minutes, glucose_values)
        self.line_insulin.set_data(time_minutes, insulin_values)
        if interstitium_values is not None:
            self.line_interstitium.set_data(time_minutes, interstitium_values)
        self.line_glucose_actual.set_data(glucose_ref_time, glucose_ref_values)
        self.line_carb_reference.set_data(carb_ref_time, carb_ref_values)
        self.line_insulin_basal.set_data(basal_time, basal_values)
        self.line_insulin_bolus.set_data(bolus_time, bolus_values)
        # insulin already set above
        if smoothed_insulin_time is not None:
            smoothed_insulin_values = smoothed_insulin_values or []
            self.line_insulin_smoothed.set_data(
                smoothed_insulin_time,
                smoothed_insulin_values,
            )

        if prediction_time is not None:
            prediction_glucose = prediction_glucose or []
            prediction_insulin = prediction_insulin or []
            self.line_glucose_prediction.set_data(
                prediction_time, prediction_glucose
            )
            self.line_insulin_prediction.set_data(
                prediction_time, prediction_insulin
            )

        self.ax_glucose.relim()
        self.ax_glucose.autoscale_view()
        self.ax_carb.relim()
        self.ax_carb.autoscale_view()
        self.ax_insulin.relim()
        self.ax_insulin.autoscale_view()
        self._refresh_glucose_legend()
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def set_prediction_overlay(
        self,
        time_minutes: list[float],
        glucose_values: list[float],
        insulin_values: list[float],
    ) -> None:
        """Set the prediction overlay lines without altering main traces."""
        self.line_glucose_prediction.set_data(time_minutes, glucose_values)
        self.line_insulin_prediction.set_data(time_minutes, insulin_values)
        self._refresh_glucose_legend()
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def clear_prediction_overlay(self) -> None:
        """Clear any prediction overlay data from the charts."""
        self.line_glucose_prediction.set_data([], [])
        self.line_insulin_prediction.set_data([], [])
        self._refresh_glucose_legend()
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def set_smoothed_overlay(
        self,
        time_minutes: list[float],
        insulin_values: list[float],
    ) -> None:
        """Set the smoothed insulin overlay data."""
        self.line_insulin_smoothed.set_data(time_minutes, insulin_values)
        self.ax_insulin.legend(loc="upper right")
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def clear_smoothed_overlay(self) -> None:
        """Clear any smoothed overlay data from the charts."""
        self.line_insulin_smoothed.set_data([], [])
        self.ax_insulin.legend(loc="upper right")
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]
