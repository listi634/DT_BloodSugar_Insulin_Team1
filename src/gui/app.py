"""CustomTkinter application shell for the glucose-insulin simulator."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import customtkinter as ctk

from src.core.benchmark_loader import GlucoBenchLoader
from src.core.benchmark_loader import ValidationWindowData
from src.core.estimator import ExtendedKalmanFilterEstimator
from src.core.simulator import GlucoseSimulator
from src.core.simulator import SimulatorSnapshot
from src.core.validation_logger import ValidationReplayLogger
from src.core.state import IntegratorMethod
from src.core.utilities import collect_due_carb_events
from src.core.utilities import collect_due_insulin_events
from src.gui.control_panel import ControlPanel
from src.gui.plot_frame import PlotFrame


@dataclass
class ValidationRunState:
    """Mutable validation runtime state managed by the app layer."""

    loaded: bool = False
    user_id: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""
    initial_glucose_mmol_l: float | None = None
    duration_minutes: float = 0.0
    glucose_reference: list[tuple[float, float]] | None = None
    measurement_reference: list[tuple[float, float]] | None = None
    carb_reference: list[tuple[float, float]] | None = None
    carb_replay_events: list[tuple[float, float]] | None = None
    basal_reference: list[tuple[float, float]] | None = None
    insulin_reference: list[tuple[float, float]] | None = None
    measurement_replay_index: int = 0
    replay_index: int = 0
    basal_replay_index: int = 0
    insulin_replay_index: int = 0

    @classmethod
    def from_window(cls, window: ValidationWindowData) -> "ValidationRunState":
        """Create a loaded runtime state from a preloaded data window."""
        return cls(
            loaded=True,
            user_id=window.user_id,
            start_timestamp=window.start_timestamp,
            end_timestamp=window.end_timestamp,
            initial_glucose_mmol_l=window.initial_glucose_mmol_l,
            duration_minutes=window.duration_minutes,
            glucose_reference=list(window.glucose_reference),
            measurement_reference=list(window.measurement_reference),
            carb_reference=list(window.carb_reference),
            carb_replay_events=list(window.carb_replay_events),
            basal_reference=list(window.basal_reference),
            insulin_reference=list(window.insulin_reference),
            measurement_replay_index=0,
            replay_index=0,
            basal_replay_index=0,
            insulin_replay_index=0,
        )


@dataclass(frozen=True)
class PredictionOverlay:
    """Stored prediction series for plotting as a background overlay."""

    time_minutes: list[float]
    glucose: list[float]
    insulin: list[float]


@dataclass(frozen=True)
class SmoothedOverlay:
    """Stored smoothed insulin series for replay visualization."""

    time_minutes: list[float]
    insulin: list[float]


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


class DigitalTwinApp(ctk.CTk):
    """Desktop dashboard for interactive simulation and monitoring."""

    def __init__(
        self,
        simulator_builder: Callable[
            [IntegratorMethod, float | None],
            GlucoseSimulator,
        ],
        step_interval_ms: int = 200,
        integrator_method: IntegratorMethod = "RK45",
    ) -> None:
        """Create app widgets and bind control callbacks."""
        super().__init__()
        if step_interval_ms <= 0:
            raise ValueError("step_interval_ms must be positive")

        self._simulator_builder = simulator_builder
        self._integrator_method = integrator_method
        self._simulator = simulator_builder(integrator_method, None)
        self._step_interval_ms = step_interval_ms
        self._running = False
        self._loop_after_id: str | None = None
        self._validation = ValidationRunState()
        self._benchmark_loader: GlucoBenchLoader | None = None
        self._pending_meal_carbs: float | None = None
        self._pending_bolus_units: list[float] = []
        self._premeal_snapshot: SimulatorSnapshot | None = None
        self._prediction_overlay: PredictionOverlay | None = None
        self._smoothed_overlay: SmoothedOverlay | None = None
        self._validation_logger: ValidationReplayLogger | None = None
        self._awaiting_resume = False
        self._prediction_horizon_minutes = 1200.0

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
            on_method_change=self._on_integrator_method_change,
            on_toggle_run=self._toggle_run,
            on_reset=self._on_reset,
            on_speed_change=self._on_speed_change,
            on_validation_user_change=self._on_validation_user_change,
            on_validation_start_change=self._on_validation_start_change,
            on_validation_end_change=self._on_validation_end_change,
            on_validation_preload=self._on_validation_preload,
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
        self._setup_validation_data()
        self._refresh_view()

    def _toggle_run(self) -> None:
        """Toggle run/pause state for non-blocking simulation loop."""
        if self._running:
            self._running = False
            self.control_panel.set_running(False)
            self._set_status("Simulation paused.")
            self._cancel_schedule()
            return

        if not self._validation.loaded:
            self._set_status("Preload a GlucoBench window before running.")
            return

        if self._awaiting_resume:
            self._resume_after_prediction()

        self._running = True
        self.control_panel.set_running(self._running)
        self._set_status("Simulation running.")
        self._schedule_next_step()

    def _on_reset(self) -> None:
        """Reset simulator state and chart data."""
        self._cancel_schedule()
        self._running = False
        self.control_panel.set_running(False)
        self._close_validation_logger()
        self._validation = ValidationRunState()
        self._simulator = self._simulator_builder(
            self._integrator_method, None
        )
        self._pending_meal_carbs = None
        self._pending_bolus_units = []
        self._premeal_snapshot = None
        self._prediction_overlay = None
        self._smoothed_overlay = None
        self._awaiting_resume = False
        self.plot_frame.set_time_origin(None)
        self.plot_frame.clear_prediction_overlay()
        self.plot_frame.clear_smoothed_overlay()
        self.control_panel.set_validation_status(
            "No validation window loaded."
        )
        self._refresh_view()
        self._set_status("Simulation reset.")

    def _on_integrator_method_change(self, method: str) -> None:
        """Apply selected integrator method and rebuild simulator state."""
        if method not in {"RK45", "DOP853", "BDF"}:
            self._set_status(f"Unsupported integrator method: {method}")
            return
        if method == self._integrator_method:
            return
        selected_method = cast(IntegratorMethod, method)
        self._cancel_schedule()
        self._running = False
        self.control_panel.set_running(False)
        self._close_validation_logger()
        self._pending_meal_carbs = None
        self._pending_bolus_units = []
        self._premeal_snapshot = None
        self._prediction_overlay = None
        self._smoothed_overlay = None
        self._awaiting_resume = False
        self.plot_frame.clear_prediction_overlay()
        self.plot_frame.clear_smoothed_overlay()
        self._integrator_method = selected_method
        if self._validation.loaded:
            self._simulator = self._simulator_builder(
                selected_method,
                self._validation.initial_glucose_mmol_l,
            )
            self._validation.replay_index = 0
            self._set_status(
                "Integrator method updated. Validation replay reset."
            )
        else:
            self._simulator = self._simulator_builder(selected_method, None)
            self._set_status(f"Integrator method set to {selected_method}.")
        self._refresh_view()

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

        due_basal_rate = 0.0
        due_insulin: list[float] = []
        if self._validation.loaded:
            due_basal = self._collect_validation_basal()
            if due_basal:
                due_basal_rate = due_basal[-1]
                self._simulator.set_basal_rate(due_basal_rate)
            due_insulin = self._collect_validation_insulin()
            due_carbs = self._collect_validation_carbs()
            if due_carbs:
                self._pause_for_meal(due_carbs, due_insulin)
                return
            if due_insulin:
                self._apply_bolus_units(due_insulin)

        if self._validation.loaded:
            measured_interstitium = self._inject_validation_measurement()
            # Replay step: assimilate measurement, disable controller
            snapshot = self._simulator.step_replay(measured_interstitium)
            self._append_validation_log(
                snapshot=snapshot,
                mode="replay",
                measured_glucose_mmol_l=measured_interstitium,
                due_carb_grams=sum(due_carbs),
                due_bolus_units=sum(due_insulin),
                due_basal_rate_u_per_h=due_basal_rate,
            )
        else:
            # Idle/manual runs keep controller active
            self._simulator.step()
        self._refresh_view()

        if self._validation.loaded and self._is_validation_finished():
            self._running = False
            self.control_panel.set_running(False)
            self._refresh_smoothed_overlay()
            self._close_validation_logger()
            self._set_status(
                "Validation run finished at selected end timestamp."
            )
            return

        self._schedule_next_step()

    def _refresh_view(self) -> None:
        """Refresh chart and metric labels from simulator history/state."""
        time, glucose, insulin, _ = self._simulator.get_history_arrays()
        interstitium = [s.interstitium for s in self._simulator.history]
        glucose_reference = None
        carb_reference = None
        if self._validation.loaded:
            glucose_reference = self._validation.glucose_reference
            carb_reference = self._validation.carb_reference
        self.plot_frame.update_plot(
            time,
            glucose,
            insulin,
            interstitium,
            actual_glucose_reference=glucose_reference,
            carb_reference=carb_reference,
            basal_reference=(
                self._validation.basal_reference
                if self._validation.loaded
                else None
            ),
            insulin_reference=(
                self._validation.insulin_reference
                if self._validation.loaded
                else None
            ),
            prediction_time=(
                self._prediction_overlay.time_minutes
                if self._prediction_overlay
                else None
            ),
            prediction_glucose=(
                self._prediction_overlay.glucose
                if self._prediction_overlay
                else None
            ),
            prediction_insulin=(
                self._prediction_overlay.insulin
                if self._prediction_overlay
                else None
            ),
            smoothed_insulin_time=(
                self._smoothed_overlay.time_minutes
                if self._smoothed_overlay
                else None
            ),
            smoothed_insulin_values=(
                self._smoothed_overlay.insulin
                if self._smoothed_overlay
                else None
            ),
        )

        state = self._simulator.current_state
        mode = "glucobench" if self._validation.loaded else "idle"
        metrics_text = (
            f"t={state.time_minutes:.0f} min    "
            f"G={state.glucose:.2f} mmol/L    "
            f"I={state.insulin:.2f} uU/mL    "
            f"rate={state.insulin_rate:.2f}    "
            f"basal={state.basal_insulin_rate:.2f}    "
            f"mode={mode}"
        )
        self.metrics_label.configure(text=metrics_text)

    def _set_status(self, message: str) -> None:
        """Update status message in UI."""
        self.status_label.configure(text=message)

    def _on_close(self) -> None:
        """Ensure scheduled callbacks are canceled before app closes."""
        self._cancel_schedule()
        self._close_validation_logger()
        self.destroy()

    def _setup_validation_data(self) -> None:
        """Initialize benchmark loader and validation selectors."""
        csv_path = Path(__file__).resolve().parents[2] / "data" / "CGM.csv"
        try:
            self._benchmark_loader = GlucoBenchLoader(csv_path)
            user_ids = self._benchmark_loader.get_user_ids()
        except (FileNotFoundError, ValueError) as exc:
            self.control_panel.set_validation_controls_enabled(False)
            self.control_panel.set_validation_status(
                f"Validation unavailable: {exc}"
            )
            self._set_status("Validation data unavailable.")
            return

        self.control_panel.set_validation_controls_enabled(True)
        self.control_panel.set_validation_users(user_ids)
        self.control_panel.set_validation_status(
            "Choose user and days, then preload validation."
        )

    def _on_validation_user_change(self, user_id: str) -> None:
        """Update day dropdowns when selected user changes."""
        if self._benchmark_loader is None or user_id == "No data":
            return

        try:
            days = self._benchmark_loader.get_user_days(user_id)
            self.control_panel.set_validation_days(days)
            self.control_panel.set_validation_status(
                f"Loaded days for user {user_id}."
            )
        except ValueError as exc:
            self._set_status(str(exc))

    def _on_validation_start_change(self, start_day: str) -> None:
        """Constrain end-day options from selected start day."""
        if self._benchmark_loader is None or start_day == "No data":
            return
        user_id, _, _ = self.control_panel.get_validation_selection()
        try:
            valid_end_days = self._benchmark_loader.get_valid_end_days(
                user_id,
                start_day,
            )
            self.control_panel.set_validation_end_days(valid_end_days)
        except ValueError as exc:
            self._set_status(str(exc))

    def _on_validation_end_change(self, end_timestamp: str) -> None:
        """Handle end timestamp selection changes."""
        del end_timestamp

    def _on_validation_preload(self) -> None:
        """Preload selected benchmark window and seed simulator state."""
        if self._benchmark_loader is None:
            self._set_status("Validation data unavailable.")
            return

        user_id, start_day, end_day = (
            self.control_panel.get_validation_selection()
        )
        if "No data" in {user_id, start_day, end_day}:
            self._set_status("Select user, start day, and end day first.")
            return

        try:
            window = self._benchmark_loader.build_validation_window_for_days(
                user_id,
                start_day,
                end_day,
            )
        except ValueError as exc:
            self._set_status(str(exc))
            self.control_panel.set_validation_status(f"Preload failed: {exc}")
            return

        self._cancel_schedule()
        self._running = False
        self.control_panel.set_running(False)
        self._close_validation_logger()
        self._pending_meal_carbs = None
        self._premeal_snapshot = None
        self._prediction_overlay = None
        self._smoothed_overlay = None
        self._awaiting_resume = False
        self.plot_frame.clear_prediction_overlay()
        self.plot_frame.clear_smoothed_overlay()

        self._validation = ValidationRunState.from_window(window)
        self.plot_frame.set_time_origin(window.start_timestamp)
        self._simulator = self._simulator_builder(
            self._integrator_method,
            window.initial_glucose_mmol_l,
        )
        # Detect user profile from replayed basal and bolus signals
        basal_series = window.basal_reference or []
        insulin_series = window.insulin_reference or []
        has_pump_basal = any(point[1] > 0.0 for point in basal_series)
        has_bolus = any(point[1] > 0.0 for point in insulin_series)

        if has_pump_basal:
            profile_text = "Type 1 (Pump)"
            insulin_basal_val = 0.0
            insulin_response_gain_val = 0.0
            profile_color = "#FFCCCC"
        elif not has_pump_basal and not has_bolus:
            profile_text = "Healthy"
            insulin_basal_val = 10.0
            insulin_response_gain_val = 0.32
            profile_color = "#CCFFCC"
        else:
            profile_text = "Type 1 (MDI/Syringe)"
            insulin_basal_val = 10.0
            insulin_response_gain_val = 0.0
            profile_color = "#FFE6CC"

        # Apply profile adjustments to the simulator's model config
        old_config = self._simulator.model_config
        new_config = replace(
            old_config,
            insulin_basal=insulin_basal_val,
            insulin_response_gain=insulin_response_gain_val,
        )
        # Update simulator internals and recreate estimator with new config
        self._simulator._model_config = new_config
        # Update initial and current insulin state to match new basal
        self._simulator._initial_state = replace(
            self._simulator._initial_state, insulin=insulin_basal_val
        )
        self._simulator._state = replace(
            self._simulator._state, insulin=insulin_basal_val
        )
        # Recreate estimator to use updated model config
        self._simulator._estimator = ExtendedKalmanFilterEstimator(
            model=self._simulator._model,
            model_config=new_config,
            initial_state=self._simulator.current_state,
        )

        # Update GUI with detected profile
        try:
            self.control_panel.set_user_profile(profile_text, profile_color)
        except Exception:
            self.control_panel.set_user_profile(profile_text)

        self._close_validation_logger()
        self._validation_logger = ValidationReplayLogger(
            output_dir=(
                Path(__file__).resolve().parents[2]
                / "logs"
            ),
            window=window,
            model_config=self._simulator.model_config,
            initial_state=self._simulator.current_state,
        )
        self._refresh_view()

        self.control_panel.set_validation_status(
            "Preloaded user "
            f"{window.user_id}: {window.start_timestamp} to "
            f"{window.end_timestamp}."
        )
        self._set_status("Validation window preloaded.")

    def _collect_validation_carbs(self) -> list[float]:
        """Collect carb events due for the current validation time."""
        if self._validation.carb_replay_events is None:
            return []

        current_time = self._simulator.current_state.time_minutes
        due_carbs, next_index = collect_due_carb_events(
            self._validation.carb_replay_events,
            self._validation.replay_index,
            current_time,
        )
        self._validation.replay_index = next_index
        return due_carbs

    def _on_speed_change(self, steps_per_second: int) -> None:
        """Update the step interval and reschedule if running."""
        if steps_per_second <= 0:
            return
        self._step_interval_ms = max(1, int(round(1000 / steps_per_second)))
        if self._running:
            self._cancel_schedule()
            self._schedule_next_step()

    def _collect_validation_insulin(self) -> list[float]:
        """Collect insulin bolus events due for the current time."""
        if self._validation.insulin_reference is None:
            return []

        current_time = self._simulator.current_state.time_minutes
        due_units, next_index = collect_due_insulin_events(
            self._validation.insulin_reference,
            self._validation.insulin_replay_index,
            current_time,
        )
        self._validation.insulin_replay_index = next_index
        return due_units

    def _collect_validation_basal(self) -> list[float]:
        """Collect basal-rate events due for the current validation time."""
        if self._validation.basal_reference is None:
            return []

        current_time = self._simulator.current_state.time_minutes
        due_rates, next_index = collect_due_insulin_events(
            self._validation.basal_reference,
            self._validation.basal_replay_index,
            current_time,
        )
        self._validation.basal_replay_index = next_index
        return due_rates

    def _append_validation_log(
        self,
        snapshot: SimulatorSnapshot,
        mode: str,
        measured_glucose_mmol_l: float | None,
        due_carb_grams: float,
        due_bolus_units: float,
        due_basal_rate_u_per_h: float,
    ) -> None:
        """Append one validation step to the active replay log."""
        if self._validation_logger is None:
            return

        self._validation_logger.record_step(
            snapshot=snapshot,
            mode=mode,
            measured_glucose_mmol_l=measured_glucose_mmol_l,
            due_carb_grams=due_carb_grams,
            due_bolus_units=due_bolus_units,
            due_basal_rate_u_per_h=due_basal_rate_u_per_h,
        )

    def _close_validation_logger(self) -> None:
        """Close the active validation replay log, if any."""
        if self._validation_logger is None:
            return

        self._validation_logger.close()
        self._validation_logger = None

    def _inject_validation_measurement(self) -> float | None:
        """Return the latest measurement due for the current tick."""
        if self._validation.measurement_reference is None:
            return None

        current_time = self._simulator.current_state.time_minutes
        measurement, next_index = collect_due_measurement(
            self._validation.measurement_reference,
            self._validation.measurement_replay_index,
            current_time,
        )
        self._validation.measurement_replay_index = next_index
        return measurement

    def _is_validation_finished(self) -> bool:
        """Check if selected validation time window has been fully replayed."""
        return (
            self._simulator.current_state.time_minutes
            >= self._validation.duration_minutes
        )

    def _pause_for_meal(
        self,
        due_carbs: list[float],
        due_insulin: list[float],
    ) -> None:
        """Pause simulation and prompt for meal decision."""
        total_carbs = sum(due_carbs)
        if total_carbs <= 0.0:
            return

        self._running = False
        self.control_panel.set_running(False)
        self._cancel_schedule()
        self._premeal_snapshot = self._simulator.export_snapshot(
            mode="replay",
            bolus_description="none",
        )
        self._pending_meal_carbs = total_carbs
        self._pending_bolus_units = list(due_insulin)

        choice = self._prompt_meal_action(total_carbs)
        if choice == "continue":
            self._apply_pending_meal_and_resume()
        else:
            self._run_prediction(total_carbs)

    def _prompt_meal_action(self, carbs: float) -> str:
        """Ask the user whether to continue or run a prediction."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Meal detected")
        dialog.geometry("420x190")
        dialog.resizable(False, False)
        dialog.grab_set()

        message = (
            f"Meal event detected ({carbs:.1f} g carbs).\n"
            "Continue simulation or run a prediction?"
        )
        label = ctk.CTkLabel(dialog, text=message, justify="left")
        label.pack(padx=16, pady=(18, 12), anchor="w")

        result: dict[str, str] = {"choice": "continue"}

        def choose_continue() -> None:
            result["choice"] = "continue"
            dialog.destroy()

        def choose_predict() -> None:
            result["choice"] = "predict"
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", choose_continue)

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(padx=16, pady=(0, 16), fill="x")

        continue_button = ctk.CTkButton(
            button_frame,
            text="Continue",
            command=choose_continue,
        )
        continue_button.pack(side="left", expand=True, padx=(0, 8))

        predict_button = ctk.CTkButton(
            button_frame,
            text="Predict",
            fg_color="#555555",
            hover_color="#444444",
            command=choose_predict,
        )
        predict_button.pack(side="right", expand=True, padx=(8, 0))

        self.wait_window(dialog)
        return result["choice"]

    def _apply_pending_meal_and_resume(self) -> None:
        """Apply the queued meal and resume the simulation loop."""
        if self._pending_meal_carbs is None:
            self._set_status("No meal pending to apply.")
            return
        try:
            self._simulator.queue_meal(self._pending_meal_carbs)
            self._apply_bolus_units(self._pending_bolus_units)
        except ValueError as exc:
            self._set_status(str(exc))
            return

        self._pending_meal_carbs = None
        self._pending_bolus_units = []
        self._premeal_snapshot = None
        self._awaiting_resume = False
        self._running = True
        self.control_panel.set_running(True)
        self._set_status("Meal applied. Simulation running.")
        self._schedule_next_step()

    def _apply_bolus_units(self, units_list: list[float]) -> None:
        """Queue each pending bolus unit value into the simulator."""
        total_units = sum(units for units in units_list if units > 0.0)
        if total_units > 0.0:
            self._simulator.queue_bolus(total_units)

    def _refresh_smoothed_overlay(self) -> None:
        """Compute and store RTS-smoothed insulin overlay after replay."""
        trace = self._simulator.get_estimator_trace()
        if not trace:
            self._smoothed_overlay = None
            self.plot_frame.clear_smoothed_overlay()
            return

        smoothed_states = ExtendedKalmanFilterEstimator.rts_smooth(trace)
        history = self._simulator.history
        time_minutes = [snapshot.time_minutes for snapshot in history[1:]]
        insulin_values = [state.insulin for state in smoothed_states]
        if len(time_minutes) != len(insulin_values):
            self._smoothed_overlay = None
            self.plot_frame.clear_smoothed_overlay()
            return

        self._smoothed_overlay = SmoothedOverlay(
            time_minutes=time_minutes,
            insulin=insulin_values,
        )
        self.plot_frame.set_smoothed_overlay(time_minutes, insulin_values)

    def _run_prediction(self, meal_carbs: float) -> None:
        """Run a prediction horizon and store its overlay trace."""
        if self._premeal_snapshot is None:
            self._set_status("Prediction unavailable without snapshot.")
            return

        self._set_status("Running prediction...")
        prediction_end = (
            self._premeal_snapshot.state.time_minutes
            + self._prediction_horizon_minutes
        )
        self._skip_validation_meals_until(prediction_end)
        self._skip_validation_insulin_until(prediction_end)

        dt_minutes = self._simulator.model_config.dt_minutes
        steps = int(self._prediction_horizon_minutes / dt_minutes)
        if steps <= 0:
            self._set_status("Prediction duration too short.")
            return

        snapshot = self._premeal_snapshot
        try:
            self._simulator.queue_meal(meal_carbs)
            self._apply_bolus_units(self._pending_bolus_units)
            for _ in range(steps):
                self._simulator.step_prediction()
        except ValueError as exc:
            self._set_status(str(exc))
            self._simulator.restore_snapshot(snapshot)
            return

        time, glucose, insulin, _ = self._simulator.get_history_arrays()
        start_time = snapshot.state.time_minutes
        overlay_time: list[float] = []
        overlay_glucose: list[float] = []
        overlay_insulin: list[float] = []
        for time_point, glucose_value, insulin_value in zip(
            time, glucose, insulin
        ):
            if time_point >= start_time:
                overlay_time.append(time_point)
                overlay_glucose.append(glucose_value)
                overlay_insulin.append(insulin_value)

        self._prediction_overlay = PredictionOverlay(
            time_minutes=overlay_time,
            glucose=overlay_glucose,
            insulin=overlay_insulin,
        )
        self.plot_frame.set_prediction_overlay(
            overlay_time, overlay_glucose, overlay_insulin
        )
        self._simulator.restore_snapshot(snapshot)
        self._refresh_view()

        self._awaiting_resume = True
        self._running = False
        self.control_panel.set_running(False)
        self._set_status(
            "Prediction complete. Press Run to continue simulation."
        )

    def _resume_after_prediction(self) -> None:
        """Restore pre-meal snapshot and apply the stored meal."""
        if self._premeal_snapshot is None or self._pending_meal_carbs is None:
            self._awaiting_resume = False
            return
        self._simulator.restore_snapshot(self._premeal_snapshot)
        self._premeal_snapshot = None
        self._apply_pending_meal_and_resume()

    def _skip_validation_meals_until(self, end_time: float) -> None:
        """Advance replay index to skip meals during prediction window."""
        if self._validation.carb_replay_events is None:
            return

        _, next_index = collect_due_carb_events(
            self._validation.carb_replay_events,
            self._validation.replay_index,
            end_time,
        )
        self._validation.replay_index = next_index

    def _skip_validation_insulin_until(self, end_time: float) -> None:
        """Advance insulin replay index to skip boluses in prediction."""
        if self._validation.insulin_reference is None:
            return

        _, next_index = collect_due_insulin_events(
            self._validation.insulin_reference,
            self._validation.insulin_replay_index,
            end_time,
        )
        self._validation.insulin_replay_index = next_index
