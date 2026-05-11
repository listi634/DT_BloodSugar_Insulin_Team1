"""Data access helpers for GlucoBench validation runs."""

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from pathlib import Path

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DAY_FORMAT = "%Y-%m-%d"
MGDL_PER_MMOLL = 18.0


@dataclass(frozen=True)
class BenchmarkRow:
    """Normalized row extracted from the benchmark dataset."""

    user_id: str
    timestamp: datetime
    glucose_mmol_l: float
    insulin_basal_units: float
    carbs_grams: float
    insulin_bolus_units: float


@dataclass(frozen=True)
class ValidationWindowData:
    """Prepared reference payload for a single validation window."""

    user_id: str
    start_timestamp: str
    end_timestamp: str
    initial_glucose_mmol_l: float
    duration_minutes: float
    glucose_reference: list[tuple[float, float]]
    measurement_reference: list[tuple[float, float]]
    carb_reference: list[tuple[float, float]]
    carb_replay_events: list[tuple[float, float]]
    insulin_basal_reference: list[tuple[float, float]]
    insulin_reference: list[tuple[float, float]]


class GlucoBenchLoader:
    """Loads and filters benchmark data for GUI validation workflows."""

    _REQUIRED_COLUMNS = {
        "user_id",
        "timestamp",
        "glucose",
        "carbs",
        "insulin_basal",
    }

    def __init__(self, csv_path: str | Path) -> None:
        """Read and validate benchmark data from CSV file.

        Args:
            csv_path: File path to the GlucoBench CSV dataset.

        Raises:
            FileNotFoundError: If the CSV file cannot be found.
            ValueError: If required columns are missing or rows are invalid.
        """
        resolved_path = Path(csv_path)
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"Benchmark CSV not found: {resolved_path}"
            )

        rows = self._read_rows(resolved_path)
        if not rows:
            raise ValueError("Benchmark dataset is empty")

        self._rows_by_user: dict[str, list[BenchmarkRow]] = defaultdict(list)
        for row in sorted(
            rows, key=lambda item: (item.user_id, item.timestamp)
        ):
            self._rows_by_user[row.user_id].append(row)

    def get_user_ids(self) -> list[str]:
        """Return all available user identifiers in ascending order."""
        return sorted(self._rows_by_user.keys())

    def get_user_days(self, user_id: str) -> list[str]:
        """Return distinct days for one user in ascending order.

        Args:
            user_id: User identifier to query.

        Returns:
            Day strings formatted as YYYY-mm-dd.

        Raises:
            ValueError: If user_id does not exist in dataset.
        """
        rows = self._get_rows_for_user(user_id)
        days = {row.timestamp.date() for row in rows}
        return [day_value.strftime(DAY_FORMAT) for day_value in sorted(days)]

    def get_valid_end_days(
        self,
        user_id: str,
        start_day: str,
    ) -> list[str]:
        """Return valid end days for a user constrained by start day.

        Args:
            user_id: User identifier to query.
            start_day: Selected window start day.

        Returns:
            Day list at or after the selected start.

        Raises:
            ValueError: If inputs are invalid.
        """
        start_date = self._parse_day(start_day, field_name="start")
        days = self.get_user_days(user_id)
        filtered = [
            day_text
            for day_text in days
            if self._parse_day(day_text, field_name="day") >= start_date
        ]
        if not filtered:
            raise ValueError("No end days available for selected start day")
        return filtered

    def build_validation_window_for_days(
        self,
        user_id: str,
        start_day: str,
        end_day: str,
    ) -> ValidationWindowData:
        """Extract validation data for full-day inclusive date boundaries.

        Args:
            user_id: User identifier selected in GUI.
            start_day: Inclusive start day in YYYY-mm-dd format.
            end_day: Inclusive end day in YYYY-mm-dd format.

        Returns:
            ValidationWindowData containing references and replay events.

        Raises:
            ValueError:
                If user, day ordering, or selected day range is invalid.
        """
        start_date = self._parse_day(start_day, field_name="start")
        end_date = self._parse_day(end_day, field_name="end")
        if end_date < start_date:
            raise ValueError("End day must be at or after start day")

        start_timestamp = datetime.combine(start_date, time.min)
        end_timestamp = datetime.combine(end_date, time.max)
        return self.build_validation_window(
            user_id=user_id,
            start_timestamp=start_timestamp.strftime(TIMESTAMP_FORMAT),
            end_timestamp=end_timestamp.strftime(TIMESTAMP_FORMAT),
        )

    def build_validation_window(
        self,
        user_id: str,
        start_timestamp: str,
        end_timestamp: str,
    ) -> ValidationWindowData:
        """Extract glucose references and carb replay events for a window.

        Args:
            user_id: User identifier selected in GUI.
            start_timestamp: Inclusive start timestamp.
            end_timestamp: Inclusive end timestamp.

        Returns:
            ValidationWindowData containing references and replay events.

        Raises:
            ValueError: If user, timestamps, or selected window are invalid.
        """
        start_dt = self._parse_timestamp(start_timestamp, field_name="start")
        end_dt = self._parse_timestamp(end_timestamp, field_name="end")
        if end_dt < start_dt:
            raise ValueError("End timestamp must be at or after start")

        rows = self._get_rows_for_user(user_id)
        window_rows = [
            row for row in rows if start_dt <= row.timestamp <= end_dt
        ]
        if not window_rows:
            raise ValueError("Selected timestamp window contains no rows")

        glucose_reference: list[tuple[float, float]] = []
        measurement_reference: list[tuple[float, float]] = []
        carb_reference: list[tuple[float, float]] = []
        carb_replay_events: list[tuple[float, float]] = []
        insulin_basal_reference: list[tuple[float, float]] = []
        insulin_reference: list[tuple[float, float]] = []
        for row in window_rows:
            elapsed_minutes = (row.timestamp - start_dt).total_seconds() / 60.0
            reference_point = (elapsed_minutes, row.glucose_mmol_l)
            glucose_reference.append(reference_point)
            measurement_reference.append(reference_point)
            insulin_basal_reference.append(
                (elapsed_minutes, row.insulin_basal_units)
            )
            if row.carbs_grams > 0.0:
                carb_point = (elapsed_minutes, row.carbs_grams)
                carb_reference.append(carb_point)
                carb_replay_events.append(carb_point)
            insulin_bolus_units = row.insulin_bolus_units
            if insulin_bolus_units > 0.0:
                insulin_reference.append(
                    (elapsed_minutes, row.insulin_bolus_units)
                )

        return ValidationWindowData(
            user_id=user_id,
            start_timestamp=start_dt.strftime(TIMESTAMP_FORMAT),
            end_timestamp=end_dt.strftime(TIMESTAMP_FORMAT),
            initial_glucose_mmol_l=glucose_reference[0][1],
            duration_minutes=(end_dt - start_dt).total_seconds() / 60.0,
            glucose_reference=glucose_reference,
            measurement_reference=measurement_reference,
            carb_reference=carb_reference,
            carb_replay_events=carb_replay_events,
            insulin_basal_reference=insulin_basal_reference,
            insulin_reference=insulin_reference,
        )

    def _get_rows_for_user(self, user_id: str) -> list[BenchmarkRow]:
        """Resolve and validate user rows from internal lookup."""
        normalized_user_id = user_id.strip()
        if normalized_user_id not in self._rows_by_user:
            raise ValueError(f"Unknown user_id: {user_id}")
        return self._rows_by_user[normalized_user_id]

    @classmethod
    def _read_rows(cls, csv_path: Path) -> list[BenchmarkRow]:
        """Read and normalize benchmark rows from CSV file."""
        parsed_rows: list[BenchmarkRow] = []
        with csv_path.open(mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fieldnames = set(reader.fieldnames or [])
            missing_columns = cls._REQUIRED_COLUMNS.difference(fieldnames)
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(
                    "Benchmark CSV missing required columns: " f"{missing}"
                )

            for line_number, row in enumerate(reader, start=2):
                user_id = (row.get("user_id") or "").strip()
                if not user_id:
                    raise ValueError(
                        "Invalid empty user_id at " f"line {line_number}"
                    )

                timestamp_text = (row.get("timestamp") or "").strip()
                timestamp = cls._parse_timestamp(
                    timestamp_text,
                    field_name="timestamp",
                    line_number=line_number,
                )

                glucose_mg_dl = cls._parse_float(
                    row.get("glucose"),
                    field_name="glucose",
                    line_number=line_number,
                )
                carbs_grams = cls._parse_float(
                    row.get("carbs"),
                    field_name="carbs",
                    line_number=line_number,
                )

                if glucose_mg_dl < 0.0:
                    raise ValueError(
                        "Invalid glucose value at "
                        f"line {line_number}: must be non-negative"
                    )
                if carbs_grams < 0.0:
                    raise ValueError(
                        "Invalid carbs value at "
                        f"line {line_number}: must be non-negative"
                    )

                parsed_rows.append(
                    BenchmarkRow(
                        user_id=user_id,
                        timestamp=timestamp,
                        glucose_mmol_l=glucose_mg_dl / MGDL_PER_MMOLL,
                        insulin_basal_units=cls._parse_float(
                            row.get("insulin_basal"),
                            field_name="insulin_basal",
                            line_number=line_number,
                        ),
                        carbs_grams=carbs_grams,
                        insulin_bolus_units=cls._parse_float(
                            row.get("insulin_bolus"),
                            field_name="insulin_bolus",
                            line_number=line_number,
                        ),
                    )
                )
        return parsed_rows

    @staticmethod
    def _parse_timestamp(
        timestamp_text: str,
        field_name: str,
        line_number: int | None = None,
    ) -> datetime:
        """Parse a dataset timestamp with contextual error reporting."""
        try:
            return datetime.strptime(timestamp_text, TIMESTAMP_FORMAT)
        except ValueError as exc:
            detail = (
                f"Invalid {field_name} timestamp at line {line_number}"
                if line_number is not None
                else f"Invalid {field_name} timestamp"
            )
            raise ValueError(f"{detail}: {timestamp_text}") from exc

    @staticmethod
    def _parse_day(day_text: str, field_name: str) -> date:
        """Parse a day value in YYYY-mm-dd format."""
        try:
            return datetime.strptime(day_text, DAY_FORMAT).date()
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name} day: {day_text}") from exc

    @staticmethod
    def _parse_float(
        raw_value: str | None,
        field_name: str,
        line_number: int,
    ) -> float:
        """Parse numeric value with contextual row-level errors."""
        text = (raw_value or "").strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid {field_name} value at line {line_number}: {text}"
            ) from exc
