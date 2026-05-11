"""Control panel widgets for user actions."""

from collections.abc import Callable

import customtkinter as ctk


class ControlPanel(ctk.CTkFrame):
    """Input controls for simulator runtime and GlucoBench workflow."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_method_change: Callable[[str], None],
        on_toggle_run: Callable[[], None],
        on_reset: Callable[[], None],
        on_validation_user_change: Callable[[str], None],
        on_validation_start_change: Callable[[str], None],
        on_validation_end_change: Callable[[str], None],
        on_validation_preload: Callable[[], None],
    ) -> None:
        """Build a compact control panel with typed callback hooks."""
        super().__init__(master)
        self._on_method_change = on_method_change
        self._on_toggle_run = on_toggle_run
        self._on_reset = on_reset
        self._on_validation_user_change = on_validation_user_change
        self._on_validation_start_change = on_validation_start_change
        self._on_validation_end_change = on_validation_end_change
        self._on_validation_preload = on_validation_preload

        self.grid_columnconfigure(0, weight=1)
        self._build_runtime_controls()
        self._build_validation_controls()

    def _build_runtime_controls(self) -> None:
        """Create runtime controls for the simulation loop."""
        ctk.CTkLabel(self, text="Integrator method").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.integrator_method_menu = ctk.CTkOptionMenu(
            self,
            values=["RK45", "DOP853", "BDF"],
            command=self._on_method_change,
        )
        self.integrator_method_menu.set("RK45")
        self.integrator_method_menu.grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 14)
        )

        self.run_button = ctk.CTkButton(
            self,
            text="Run",
            command=self._on_toggle_run,
        )
        self.run_button.grid(
            row=2, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        self.reset_button = ctk.CTkButton(
            self,
            text="Reset",
            fg_color="#555555",
            hover_color="#444444",
            command=self._on_reset,
        )
        self.reset_button.grid(
            row=3, column=0, sticky="ew", padx=12, pady=(0, 12)
        )

    def _build_validation_controls(self) -> None:
        """Create GlucoBench validation card and selectors."""
        self.validation_frame = ctk.CTkFrame(self)
        self.validation_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        self.validation_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.validation_frame,
            text="Validation (GlucoBench)",
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
            text="Preload Dataset Run",
            command=self._on_validation_preload,
        )
        self.validation_preload_button.grid(
            row=7, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

        self.validation_status_label = ctk.CTkLabel(
            self.validation_frame,
            text="No dataset window loaded.",
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self.validation_status_label.grid(
            row=8, column=0, sticky="ew", padx=8, pady=(0, 8)
        )

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
        self.validation_end_menu.set(days[-1])
        self._on_validation_start_change(days[0])
        self._on_validation_end_change(days[-1])

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
