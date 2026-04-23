"""Control panel widgets for user actions."""

from collections.abc import Callable

import customtkinter as ctk


class ControlPanel(ctk.CTkFrame):
    """Input controls for meal, sport, and simulator workflow."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_meal: Callable[[float], None],
        on_sport: Callable[[float, float], None],
        on_method_change: Callable[[str], None],
        on_toggle_run: Callable[[], None],
        on_reset: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Build a compact control panel with typed callback hooks."""
        super().__init__(master)
        self._on_meal = on_meal
        self._on_sport = on_sport
        self._on_method_change = on_method_change
        self._on_toggle_run = on_toggle_run
        self._on_reset = on_reset
        self._on_error = on_error

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Meal (carbs in g)").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.meal_entry = ctk.CTkEntry(self)
        self.meal_entry.insert(0, "40")
        self.meal_entry.grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        self.meal_button = ctk.CTkButton(
            self,
            text="Add Meal",
            command=self._handle_meal,
        )
        self.meal_button.grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

        ctk.CTkLabel(self, text="Sport multiplier").grid(
            row=3, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.sport_multiplier_entry = ctk.CTkEntry(self)
        self.sport_multiplier_entry.insert(0, "1.4")
        self.sport_multiplier_entry.grid(
            row=4, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        ctk.CTkLabel(self, text="Sport duration (min)").grid(
            row=5, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.sport_duration_entry = ctk.CTkEntry(self)
        self.sport_duration_entry.insert(0, "30")
        self.sport_duration_entry.grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        self.sport_button = ctk.CTkButton(
            self,
            text="Start Sport",
            command=self._handle_sport,
        )
        self.sport_button.grid(
            row=7, column=0, sticky="ew", padx=12, pady=(0, 14)
        )

        ctk.CTkLabel(self, text="Integrator method").grid(
            row=8, column=0, sticky="w", padx=12, pady=(0, 4)
        )
        self.integrator_method_menu = ctk.CTkOptionMenu(
            self,
            values=["RK45", "DOP853", "BDF"],
            command=self._on_method_change,
        )
        self.integrator_method_menu.set("RK45")
        self.integrator_method_menu.grid(
            row=9, column=0, sticky="ew", padx=12, pady=(0, 14)
        )

        self.run_button = ctk.CTkButton(
            self,
            text="Run",
            command=self._on_toggle_run,
        )
        self.run_button.grid(
            row=10, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        self.reset_button = ctk.CTkButton(
            self,
            text="Reset",
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_reset,
        )
        self.reset_button.grid(
            row=11, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

    def set_running(self, running: bool) -> None:
        """Update run button label to reflect simulation state."""
        self.run_button.configure(text="Pause" if running else "Run")

    def _handle_meal(self) -> None:
        """Parse and dispatch meal input from entry widget."""
        try:
            carbs = float(self.meal_entry.get())
            self._on_meal(carbs)
        except ValueError:
            self._on_error("Meal must be a positive number.")

    def _handle_sport(self) -> None:
        """Parse and dispatch sport input from entry widgets."""
        try:
            multiplier = float(self.sport_multiplier_entry.get())
            duration = float(self.sport_duration_entry.get())
            self._on_sport(multiplier, duration)
        except ValueError:
            self._on_error("Sport values must be numeric.")
