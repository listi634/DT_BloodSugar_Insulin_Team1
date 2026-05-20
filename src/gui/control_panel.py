"""Control panel widgets for user actions."""

from collections.abc import Callable
from tkinter import TclError

import customtkinter as ctk


class ControlPanel(ctk.CTkScrollableFrame):
    """Input controls for simulator runtime and GlucoBench workflow."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_method_change: Callable[[str], None],
        on_toggle_run: Callable[[], None],
        on_reset: Callable[[], None],
        on_speed_change: Callable[[int], None],
        on_validation_user_change: Callable[[str], None],
        on_validation_start_change: Callable[[str], None],
        on_validation_end_change: Callable[[str], None],
        on_validation_preload: Callable[[], None],
        on_prediction_request: Callable[[], None],
        on_prediction_reset: Callable[[], None],
    ) -> None:
        """Build a compact control panel with typed callback hooks."""
        super().__init__(master)
        self._on_method_change = on_method_change
        self._on_toggle_run = on_toggle_run
        self._on_reset = on_reset
        self._on_speed_change = on_speed_change
        self._on_validation_user_change = on_validation_user_change
        self._on_validation_start_change = on_validation_start_change
        self._on_validation_end_change = on_validation_end_change
        self._on_validation_preload = on_validation_preload
        self._on_prediction_request = on_prediction_request
        self._on_prediction_reset = on_prediction_reset
        self._prediction_mode = "interstitium"

        self.grid_columnconfigure(0, weight=1)
        self._build_runtime_controls()
        self._build_prediction_controls()
        self._build_validation_controls()

    def _build_runtime_controls(self) -> None:
        """Create runtime controls for the simulation loop."""
        self.run_button = ctk.CTkButton(
            self,
            text="Run",
            command=self._on_toggle_run,
            fg_color="#1F7A1F",
            hover_color="#155B15",
            font=ctk.CTkFont(weight="bold", size=14),
            height=38,
        )
        self.run_button.grid(
            row=0, column=0, sticky="ew", padx=12, pady=(12, 8)
        )

        self.reset_button = ctk.CTkButton(
            self,
            text="Reset",
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_reset,
        )
        self.reset_button.grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

        ctk.CTkLabel(self, text="Speed (steps/sec)").grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.speed_value_label = ctk.CTkLabel(self, text="500")
        self.speed_value_label.grid(
            row=3, column=0, sticky="e", padx=12, pady=(0, 4)
        )
        self.speed_slider = ctk.CTkSlider(
            self,
            from_=1,
            to=1000,
            number_of_steps=999,
            command=self._handle_speed_change,
        )
        self.speed_slider.set(500)
        self.speed_slider.grid(
            row=4, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

        ctk.CTkLabel(self, text="Integrator method").grid(
            row=5, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.integrator_method_menu = ctk.CTkOptionMenu(
            self,
            values=["RK45", "DOP853", "BDF"],
            command=self._on_method_change,
        )
        self.integrator_method_menu.set("RK45")
        self.integrator_method_menu.grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 14)
        )

    def _build_prediction_controls(self) -> None:
        """Create a compact what-if prediction card."""
        self.prediction_frame = ctk.CTkFrame(self)
        self.prediction_frame.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        self.prediction_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.prediction_frame,
            text="Prediction (what-if)",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        ctk.CTkLabel(self.prediction_frame, text="Horizon (min)").grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.prediction_horizon_entry = ctk.CTkEntry(self.prediction_frame)
        self.prediction_horizon_entry.insert(0, "120")
        self.prediction_horizon_entry.grid(
            row=2, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(self.prediction_frame, text="Meal carbs (g)").grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.prediction_meal_entry = ctk.CTkEntry(self.prediction_frame)
        self.prediction_meal_entry.insert(0, "0")
        self.prediction_meal_entry.grid(
            row=4, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(self.prediction_frame, text="Bolus (U)").grid(
            row=5, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.prediction_bolus_entry = ctk.CTkEntry(self.prediction_frame)
        self.prediction_bolus_entry.insert(0, "0")
        self.prediction_bolus_entry.grid(
            row=6, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(self.prediction_frame, text="Prediction source").grid(
            row=7, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.prediction_mode_switch = ctk.CTkSegmentedButton(
            self.prediction_frame,
            values=["Interstitium", "Plasma"],
            command=self._handle_prediction_mode_change,
        )
        self.prediction_mode_switch.set("Interstitium")
        self.prediction_mode_switch.grid(
            row=8, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        self.prediction_button = ctk.CTkButton(
            self.prediction_frame,
            text="Predict",
            command=self._on_prediction_request,
        )
        self.prediction_button.grid(
            row=9, column=0, sticky="ew", padx=8, pady=(0, 8)
        )
        self.prediction_reset_button = ctk.CTkButton(
            self.prediction_frame,
            text="Reset Prediction",
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_prediction_reset,
        )
        self.prediction_reset_button.grid(
            row=10, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

    def _build_validation_controls(self) -> None:
        """Create GlucoBench validation card and selectors."""
        self.validation_frame = ctk.CTkFrame(self)
        self.validation_frame.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        self.validation_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.validation_frame,
            text="Preload Data",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        ctk.CTkLabel(self.validation_frame, text="User ID").grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.validation_user_menu = ctk.CTkOptionMenu(
            self.validation_frame,
            values=["No data"],
            command=self._handle_validation_user_change,
        )
        self.validation_user_menu.set("No data")
        self.validation_user_menu.grid(
            row=2, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(self.validation_frame, text="Start day").grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.validation_start_menu = ctk.CTkOptionMenu(
            self.validation_frame,
            values=["No data"],
            command=self._handle_validation_start_change,
        )
        self.validation_start_menu.set("No data")
        self.validation_start_menu.grid(
            row=4, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(self.validation_frame, text="End day").grid(
            row=5, column=0, sticky="w", padx=8, pady=(0, 4)
        )
        self.validation_end_menu = ctk.CTkOptionMenu(
            self.validation_frame,
            values=["No data"],
            command=self._handle_validation_end_change,
        )
        self.validation_end_menu.set("No data")
        self.validation_end_menu.grid(
            row=6, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        self.validation_preload_button = ctk.CTkButton(
            self.validation_frame,
            text="Preload",
            command=self._on_validation_preload,
        )
        self.validation_preload_button.grid(
            row=7, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        self.validation_status_label = ctk.CTkLabel(
            self.validation_frame,
            text="",
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self.validation_status_label.grid(
            row=8, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        # Detected user profile display (empty until preload)
        self.user_profile_label = ctk.CTkLabel(
            self.validation_frame,
            text="User profile: unknown",
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self.user_profile_label.grid(
            row=9, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

    def get_prediction_inputs(self) -> tuple[float, float, float]:
        """Return the current prediction scenario inputs from the form."""
        try:
            horizon_minutes = float(self.prediction_horizon_entry.get())
            meal_carbs = float(self.prediction_meal_entry.get())
            bolus_units = float(self.prediction_bolus_entry.get())
        except ValueError as exc:
            raise ValueError("Prediction inputs must be numeric") from exc

        return horizon_minutes, meal_carbs, bolus_units

    def get_prediction_mode(self) -> str:
        """Return the selected prediction glucose source."""
        return self._prediction_mode

    def set_validation_users(self, user_ids: list[str]) -> None:
        """Populate user selector and trigger dependent refresh."""
        if not user_ids:
            self.validation_user_menu.configure(values=["No data"])
            self.validation_user_menu.set("No data")
            self.set_validation_days([])
            return

        self.validation_user_menu.configure(values=user_ids)
        self.validation_user_menu.set(user_ids[0])
        self._on_validation_user_change(user_ids[0])

    def set_validation_days(self, days: list[str]) -> None:
        """Populate both start and end menus from one day list."""
        if not days:
            self.validation_start_menu.configure(values=["No data"])
            self.validation_end_menu.configure(values=["No data"])
            self.validation_start_menu.set("No data")
            self.validation_end_menu.set("No data")
            return

        self.validation_start_menu.configure(values=days)
        self.validation_end_menu.configure(values=days)
        self.validation_start_menu.set(days[0])
        self.validation_end_menu.set(days[0])
        self._on_validation_start_change(days[0])
        self._on_validation_end_change(days[0])

    def set_validation_end_days(self, days: list[str]) -> None:
        """Update end-day selector while preserving current value."""
        if not days:
            self.validation_end_menu.configure(values=["No data"])
            self.validation_end_menu.set("No data")
            self._on_validation_end_change("No data")
            return

        current_end = self.validation_end_menu.get()
        self.validation_end_menu.configure(values=days)
        if current_end in days:
            selected_end = current_end
        else:
            selected_end = days[-1]
        self.validation_end_menu.set(selected_end)
        self._on_validation_end_change(selected_end)

    def set_validation_status(self, message: str) -> None:
        """Display a short validation status string in the card."""
        self.validation_status_label.configure(text=message)

    def set_user_profile(
        self, profile_text: str, color: str | None = None
    ) -> None:
        """Show detected user profile with optional color hint."""
        self.user_profile_label.configure(text=f"User profile: {profile_text}")
        if color is not None:
            try:
                self.user_profile_label.configure(fg_color=color)
            except TclError:
                pass

    def set_validation_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable all validation widgets as a group."""
        state = "normal" if enabled else "disabled"
        self.validation_user_menu.configure(state=state)
        self.validation_start_menu.configure(state=state)
        self.validation_end_menu.configure(state=state)
        self.validation_preload_button.configure(state=state)

    def set_running(self, running: bool) -> None:
        """Update run button label to reflect simulation state."""
        self.run_button.configure(text="Pause" if running else "Run")

    def set_speed_value(self, value: int) -> None:
        """Update speed label and slider position."""
        self.speed_value_label.configure(text=str(value))
        self.speed_slider.set(value)

    def get_validation_selection(self) -> tuple[str, str, str]:
        """Return selected user/start/end values from validation controls."""
        return (
            self.validation_user_menu.get(),
            self.validation_start_menu.get(),
            self.validation_end_menu.get(),
        )

    def _handle_validation_user_change(self, selected_user: str) -> None:
        """Dispatch user selector callback."""
        self._on_validation_user_change(selected_user)

    def _handle_validation_start_change(self, selected_start: str) -> None:
        """Dispatch start selector callback."""
        self._on_validation_start_change(selected_start)

    def _handle_validation_end_change(self, selected_end: str) -> None:
        """Dispatch end selector callback."""
        self._on_validation_end_change(selected_end)

    def _handle_speed_change(self, value: float) -> None:
        """Dispatch speed change with integer steps per second."""
        speed_steps = max(1, int(round(value)))
        self.set_speed_value(speed_steps)
        self._on_speed_change(speed_steps)

    def _handle_prediction_mode_change(self, value: str) -> None:
        """Store the selected prediction glucose source."""
        normalized_value = value.lower()
        if normalized_value not in {"interstitium", "plasma"}:
            return
        self._prediction_mode = normalized_value
