"""Embedded Matplotlib charts for the CustomTkinter dashboard."""

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import customtkinter as ctk


class PlotFrame(ctk.CTkFrame):
    """Displays glucose and insulin trajectories in two synchronized charts."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Create chart widgets and visual style."""
        super().__init__(master)

        self.figure = Figure(figsize=(8.0, 5.2), dpi=100)
        self.ax_glucose = self.figure.add_subplot(211)
        self.ax_insulin = self.figure.add_subplot(212, sharex=self.ax_glucose)

        self.ax_glucose.set_title("Glucose and Insulin Dynamics")
        self.ax_glucose.set_ylabel("Glucose [mmol/L]")
        self.ax_insulin.set_ylabel("Insulin [uU/mL]")
        self.ax_insulin.set_xlabel("Time [min]")

        self.line_glucose = self.ax_glucose.plot(
            [], [], color="#D7263D", linewidth=2.0, label="Glucose"
        )[0]
        self.line_insulin = self.ax_insulin.plot(
            [], [], color="#1B998B", linewidth=2.0, label="Insulin"
        )[0]

        self.ax_glucose.grid(alpha=0.2)
        self.ax_insulin.grid(alpha=0.2)
        self.ax_glucose.legend(loc="upper right")
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

    def update_plot(
        self,
        time_minutes: list[float],
        glucose_values: list[float],
        insulin_values: list[float],
    ) -> None:
        """Refresh line data and autoscale axes."""
        if not time_minutes:
            return

        self.line_glucose.set_data(time_minutes, glucose_values)
        self.line_insulin.set_data(time_minutes, insulin_values)

        self.ax_glucose.relim()
        self.ax_glucose.autoscale_view()
        self.ax_insulin.relim()
        self.ax_insulin.autoscale_view()
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]
