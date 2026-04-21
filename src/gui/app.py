"""CustomTkinter application shell for the glucose-insulin simulator."""

import customtkinter as ctk

from src.core.simulator import GlucoseSimulator
from src.gui.control_panel import ControlPanel
from src.gui.plot_frame import PlotFrame


class DigitalTwinApp(ctk.CTk):
    """Desktop dashboard for interactive simulation and monitoring."""

    def __init__(
        self,
        simulator: GlucoseSimulator,
        step_interval_ms: int = 200,
    ) -> None:
        """Create app widgets and bind control callbacks."""
        super().__init__()
        if step_interval_ms <= 0:
            raise ValueError("step_interval_ms must be positive")

        self._simulator = simulator
        self._step_interval_ms = step_interval_ms
        self._running = False
        self._loop_after_id: str | None = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title("Digital Twin: Glucose-Insulin V1")
        self.geometry("1200x760")
        self.minsize(980, 640)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.control_panel = ControlPanel(
            self,
            on_meal=self._on_meal,
            on_sport=self._on_sport,
            on_toggle_run=self._toggle_run,
            on_reset=self._on_reset,
            on_error=self._set_status,
        )
        self.control_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(14, 8),
            pady=14,
        )

        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 14),
            pady=14,
        )
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)

        self.plot_frame = PlotFrame(self.right_panel)
        self.plot_frame.grid(
            row=0, column=0, sticky="nsew", padx=8, pady=(8, 4)
        )

        self.metrics_label = ctk.CTkLabel(
            self.right_panel,
            text="",
            anchor="w",
        )
        self.metrics_label.grid(
            row=1, column=0, sticky="ew", padx=10, pady=(6, 2)
        )

        self.status_label = ctk.CTkLabel(
            self.right_panel,
            text="Ready.",
            anchor="w",
        )
        self.status_label.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 8)
        )

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_view()

    def _toggle_run(self) -> None:
        """Toggle run/pause state for non-blocking simulation loop."""
        self._running = not self._running
        self.control_panel.set_running(self._running)
        if self._running:
            self._set_status("Simulation running.")
            self._schedule_next_step()
        else:
            self._set_status("Simulation paused.")
            self._cancel_schedule()

    def _on_meal(self, carbs: float) -> None:
        """Handle user meal action and show feedback."""
        try:
            self._simulator.queue_meal(carbs)
            self._set_status(f"Queued meal: {carbs:.1f} g carbs")
        except ValueError as exc:
            self._set_status(str(exc))

    def _on_sport(self, multiplier: float, duration_minutes: float) -> None:
        """Handle user sport action and show feedback."""
        try:
            self._simulator.queue_sport(multiplier, duration_minutes)
            self._set_status(
                "Queued sport boost: "
                f"x{multiplier:.2f} for {duration_minutes:.0f} min"
            )
        except ValueError as exc:
            self._set_status(str(exc))

    def _on_reset(self) -> None:
        """Reset simulator state and chart data."""
        self._cancel_schedule()
        self._running = False
        self.control_panel.set_running(False)
        self._simulator.reset()
        self._refresh_view()
        self._set_status("Simulation reset.")

    def _schedule_next_step(self) -> None:
        """Schedule the next simulation tick on the Tk event loop."""
        if self._loop_after_id is None:
            self._loop_after_id = self.after(
                self._step_interval_ms,
                self._on_tick,
            )

    def _cancel_schedule(self) -> None:
        """Cancel scheduled callback if present."""
        if self._loop_after_id is not None:
            self.after_cancel(self._loop_after_id)
            self._loop_after_id = None

    def _on_tick(self) -> None:
        """Advance simulation once and queue next tick if running."""
        self._loop_after_id = None
        if not self._running:
            return
        self._simulator.step()
        self._refresh_view()
        self._schedule_next_step()

    def _refresh_view(self) -> None:
        """Refresh chart and metric labels from simulator history/state."""
        time, glucose, insulin, _ = self._simulator.get_history_arrays()
        self.plot_frame.update_plot(time, glucose, insulin)

        state = self._simulator.current_state
        metrics_text = (
            f"t={state.time_minutes:.0f} min    "
            f"G={state.glucose:.2f} mmol/L    "
            f"I={state.insulin:.2f} uU/mL    "
            f"rate={state.insulin_rate:.2f}"
        )
        self.metrics_label.configure(text=metrics_text)

    def _set_status(self, message: str) -> None:
        """Update status message in UI."""
        self.status_label.configure(text=message)

    def _on_close(self) -> None:
        """Ensure scheduled callbacks are canceled before app closes."""
        self._cancel_schedule()
        self.destroy()
