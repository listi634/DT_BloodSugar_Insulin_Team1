"""Embedded Matplotlib charts for the CustomTkinter dashboard."""

from collections.abc import Sequence

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import customtkinter as ctk

from src.core.utilities import sanitize_reference_points


class PlotFrame(ctk.CTkFrame):
    """Displays glucose and insulin trajectories in two synchronized charts."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Create chart widgets and visual style."""
        super().__init__(master)

        self.figure = Figure(figsize=(8.0, 5.2), dpi=100)
        self.ax_glucose = self.figure.add_subplot(211)
        self.ax_insulin = self.figure.add_subplot(212, sharex=self.ax_glucose)
        self.ax_carb = self.ax_glucose.twinx()

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
            label="Simulated Glucose",
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
            label="Actual Glucose (Ref)",
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
        actual_glucose_reference: Sequence[tuple[float, float]] | None = None,
        carb_reference: Sequence[tuple[float, float]] | None = None,
        prediction_time: list[float] | None = None,
        prediction_glucose: list[float] | None = None,
        prediction_insulin: list[float] | None = None,
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

        self.line_glucose.set_data(time_minutes, glucose_values)
        self.line_glucose_actual.set_data(glucose_ref_time, glucose_ref_values)
        self.line_carb_reference.set_data(carb_ref_time, carb_ref_values)
        self.line_insulin.set_data(time_minutes, insulin_values)

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
