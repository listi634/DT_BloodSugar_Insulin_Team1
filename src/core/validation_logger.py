"""Structured validation replay logging for AI-friendly analysis."""

from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from src.core.benchmark_loader import ValidationWindowData
from src.core.state import ModelConfig
from src.core.state import SimulationSnapshot
from src.core.state import SimulationState


@dataclass
class ValidationReplayLogger:
    """Write validation replay records to a structured JSONL file.

    The log is designed to be easy to inspect later by a human or by an AI
    assistant. The first line describes the session and the remaining lines
    store one step per record.
    """

    output_dir: Path
    window: ValidationWindowData
    model_config: ModelConfig
    initial_state: SimulationState
    controller_config: object | None = None
    _path: Path = field(init=False)
    _handle: Any = field(init=False, default=None)
    _record_count: int = field(init=False, default=0)
    _started_at: datetime = field(init=False)
    _closed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        """Create the log file and write the session header."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.output_dir / self._build_filename(self.window)
        self._started_at = datetime.now()
        self._handle = self._path.open(mode="w", encoding="utf-8", newline="")
        self._write_json_line(self._build_session_header())

    @property
    def path(self) -> Path:
        """Return the log file path."""
        return self._path

    def record_step(
        self,
        snapshot: SimulationSnapshot,
        mode: str,
        measured_glucose_mmol_l: float | None = None,
        due_carb_grams: float = 0.0,
        due_bolus_units: float = 0.0,
    ) -> None:
        """Append one simulated step with relevant benchmark context."""
        if self._closed:
            return

        record = {
            "type": "step",
            "step_index": self._record_count,
            "mode": mode,
            "measured_glucose_mmol_l": measured_glucose_mmol_l,
            "due_carb_grams": due_carb_grams,
            "due_bolus_units": due_bolus_units,
            "simulation_state": asdict(snapshot),
            "state_notes": {
                "plasma_glucose": "simulation_state.glucose",
                "interstitium": "simulation_state.interstitium",
                "plasma_insulin": "simulation_state.insulin",
                "insulin_rate": "simulation_state.insulin_rate",
            },
        }
        self._write_json_line(record)
        self._record_count += 1

    def close(self) -> None:
        """Write a footer and close the file handle once."""
        if self._closed:
            return

        self._write_json_line(
            {
                "type": "footer",
                "record_count": self._record_count,
                "closed_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        if self._handle is not None:
            self._handle.close()
        self._closed = True

    def _build_session_header(self) -> dict[str, Any]:
        """Build the first JSONL line with human-readable context."""
        return {
            "type": "session",
            "schema_version": "dt.validation_replay_log.v1",
            "started_at": self._started_at.isoformat(timespec="seconds"),
            "window": {
                "user_id": self.window.user_id,
                "start_timestamp": self.window.start_timestamp,
                "end_timestamp": self.window.end_timestamp,
                "duration_minutes": self.window.duration_minutes,
                "initial_glucose_mmol_l": self.window.initial_glucose_mmol_l,
            },
            "input_interpretation": {
                "plasma_glucose_field": "simulation_state.glucose",
                "interstitium_field": "simulation_state.interstitium",
                "insulin_field": "simulation_state.insulin",
                "measured_glucose_field": (
                    "measured_glucose_mmol_l from benchmark CGM"
                ),
                "event_fields": ["due_carb_grams", "due_bolus_units"],
            },
            "model_config": asdict(self.model_config),
            "controller_config": (
                asdict(self.controller_config)
                if hasattr(self.controller_config, "__dataclass_fields__")
                else self.controller_config
            ),
            "initial_state": asdict(self.initial_state),
            "notes": [
                "Each step record stores the full simulated state snapshot.",
                "Plasma glucose is the model blood glucose state used by the ODE.",
                "Interstitium is the CGM-like state assimilated by the replay estimator.",
                "Measured glucose is the benchmark value used when available.",
                "mode=replay means the step was part of the validation run.",
                "mode=prediction means the step came from a temporary what-if overlay.",
            ],
        }

    def _write_json_line(self, payload: Mapping[str, Any]) -> None:
        """Serialize one JSON object as a newline-delimited record."""
        if self._handle is None:
            return
        self._handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
        self._handle.flush()

    @staticmethod
    def _build_filename(window: ValidationWindowData) -> str:
        """Create a stable filename for a validation replay log."""
        safe_user = re.sub(r"[^A-Za-z0-9._-]+", "_", window.user_id.strip())
        safe_start = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            window.start_timestamp.strip().replace(":", "-"),
        )
        safe_end = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            window.end_timestamp.strip().replace(":", "-"),
        )
        return f"{safe_user}_{safe_start}_to_{safe_end}_replay.jsonl"
