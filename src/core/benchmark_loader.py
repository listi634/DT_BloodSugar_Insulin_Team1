"""Data access helpers for GlucoBench validation runs."""

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from pathlib import Path
from typing import Any

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DAY_FORMAT = "%Y-%m-%d"
MGDL_PER_MMOLL = 18.0


@dataclass(frozen=True)
class BenchmarkRow:
    """Normalized row extracted from the benchmark dataset."""

    user_id: str
    timestamp: datetime
    glucose_mmol_l: float
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
    insulin_reference: list[tuple[float, float]]


class GlucoBenchLoader:
    """Loads and filters benchmark data for GUI validation workflows."""

    _REQUIRED_COLUMNS = {"user_id", "timestamp", "glucose", "carbs"}

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
        insulin_reference: list[tuple[float, float]] = []
        for row in window_rows:
            elapsed_minutes = (row.timestamp - start_dt).total_seconds() / 60.0
            reference_point = (elapsed_minutes, row.glucose_mmol_l)
            glucose_reference.append(reference_point)
            measurement_reference.append(reference_point)
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

    def compute_user_statistics(self, user_id: str) -> dict[str, Any]:
        """Compute baseline statistics for a single user.

        Computes median glucose, percentiles, mean meal size, and mean
        insulin bolus from all available historical data for the user.

        Args:
            user_id: User identifier to analyze.

        Returns:
            Dictionary with keys:
                - 'user_id': str
                - 'baseline_glucose': float (median glucose in mmol/L)
                - 'percentile_10': float
                - 'percentile_25': float
                - 'percentile_75': float
                - 'percentile_90': float
                - 'mean_meal_grams': float (mean carb intake when >0)
                - 'mean_bolus_units': float (mean insulin bolus when >0)
                - 'num_rows': int (total data points)

        Raises:
            ValueError: If user_id does not exist in dataset.
        """
        rows = self._get_rows_for_user(user_id)

        glucose_values = [row.glucose_mmol_l for row in rows]
        carb_values = [
            row.carbs_grams for row in rows if row.carbs_grams > 0.0
        ]
        bolus_values = [
            row.insulin_bolus_units
            for row in rows
            if row.insulin_bolus_units > 0.0
        ]

        # Compute percentiles (using sorted list, not numpy for simplicity)
        glucose_sorted = sorted(glucose_values)
        n = len(glucose_sorted)

        def percentile_value(values: list[float], p: float) -> float:
            """Compute percentile using linear interpolation."""
            if not values:
                return 0.0
            idx = (p / 100.0) * (len(values) - 1)
            lower_idx = int(idx)
            upper_idx = min(lower_idx + 1, len(values) - 1)
            if lower_idx == upper_idx:
                return values[lower_idx]
            fraction = idx - lower_idx
            return (
                values[lower_idx] * (1 - fraction)
                + values[upper_idx] * fraction
            )

        median_glucose = percentile_value(glucose_sorted, 50.0)
        mean_meal = sum(carb_values) / len(carb_values) if carb_values else 0.0
        mean_bolus = (
            sum(bolus_values) / len(bolus_values) if bolus_values else 0.0
        )

        return {
            "user_id": user_id,
            "baseline_glucose": median_glucose,
            "percentile_10": percentile_value(glucose_sorted, 10.0),
            "percentile_25": percentile_value(glucose_sorted, 25.0),
            "percentile_75": percentile_value(glucose_sorted, 75.0),
            "percentile_90": percentile_value(glucose_sorted, 90.0),
            "mean_meal_grams": mean_meal,
            "mean_bolus_units": mean_bolus,
            "num_rows": n,
        }

    def get_all_user_stats(self) -> dict[str, dict[str, Any]]:
        """Compute statistics for all users in the dataset.

        Returns:
            Dictionary mapping user_id to their statistics dict.
        """
        all_stats = {}
        for user_id in self.get_user_ids():
            all_stats[user_id] = self.compute_user_statistics(user_id)
        return all_stats

    def print_user_stats_table(self) -> None:
        """Print a formatted table of user statistics to stdout."""
        stats = self.get_all_user_stats()
        if not stats:
            print("No user statistics available")
            return

        print("\n" + "=" * 120)
        print(
            f"{'User ID':>8} | "
            f"{'Baseline':>10} | "
            f"{'P10':>8} | "
            f"{'P25':>8} | "
            f"{'P75':>8} | "
            f"{'P90':>8} | "
            f"{'Mean Meal':>10} | "
            f"{'Mean Bolus':>10} | "
            f"{'Rows':>6}"
        )
        print("-" * 120)

        for user_id in sorted(stats.keys()):
            stat = stats[user_id]
            print(
                f"{stat['user_id']:>8} | "
                f"{stat['baseline_glucose']:>10.2f} | "
                f"{stat['percentile_10']:>8.2f} | "
                f"{stat['percentile_25']:>8.2f} | "
                f"{stat['percentile_75']:>8.2f} | "
                f"{stat['percentile_90']:>8.2f} | "
                f"{stat['mean_meal_grams']:>10.2f} | "
                f"{stat['mean_bolus_units']:>10.2f} | "
                f"{stat['num_rows']:>6}"
            )

        print("=" * 120 + "\n")

    def save_user_stats_to_csv(self, output_path: str | Path) -> None:
        """Export user statistics to a CSV file.

        Args:
            output_path: File path where CSV will be written.
        """
        stats = self.get_all_user_stats()
        if not stats:
            raise ValueError("No statistics to save")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open(mode="w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "user_id",
                "baseline_glucose",
                "percentile_10",
                "percentile_25",
                "percentile_75",
                "percentile_90",
                "mean_meal_grams",
                "mean_bolus_units",
                "num_rows",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for user_id in sorted(stats.keys()):
                writer.writerow(stats[user_id])

    def get_best_validation_windows(
        self, num_users: int = 2, num_windows_per_user: int = 2
    ) -> list[tuple[str, str, str]]:
        """Find best validation windows (user, start_day, end_day).

        Selects windows with:
        - Continuous data (no large gaps)
        - Multiple meals (≥3)
        - Multiple bolus events (≥2)

        Args:
            num_users: Number of users to select.
            num_windows_per_user: Number of windows per user to find.

        Returns:
            List of tuples (user_id, start_day, end_day) in YYYY-mm-dd format.
        """
        selected_windows: list[tuple[str, str, str]] = []
        user_ids = self.get_user_ids()[:num_users]

        for user_id in user_ids:
            windows_for_user = 0
            days = self.get_user_days(user_id)

            for start_idx, start_day in enumerate(days):
                if windows_for_user >= num_windows_per_user:
                    break

                # Try one- or two-day windows
                for end_offset in [0, 1]:
                    if windows_for_user >= num_windows_per_user:
                        break

                    end_idx = start_idx + end_offset
                    if end_idx >= len(days):
                        continue

                    end_day = days[end_idx]

                    try:
                        window = self.build_validation_window_for_days(
                            user_id, start_day, end_day
                        )

                        # Count meals and boluses
                        num_meals = len(
                            [x for x in window.carb_replay_events if x[1] > 0]
                        )
                        num_boluses = len(
                            [x for x in window.insulin_reference if x[1] > 0]
                        )

                        # Accept if criteria met
                        if num_meals >= 3 and num_boluses >= 2:
                            selected_windows.append(
                                (user_id, start_day, end_day)
                            )
                            windows_for_user += 1

                    except ValueError:
                        # Skip invalid windows silently
                        continue

        return selected_windows

    def print_validation_windows(self) -> None:
        """Print a list of selected validation windows."""
        windows = self.get_best_validation_windows()
        if not windows:
            print("No suitable validation windows found")
            return

        print("\n" + "=" * 70)
        print(f"{'User':>8} | {'Start Day':>12} | {'End Day':>12} | Notes")
        print("-" * 70)

        for user_id, start_day, end_day in windows:
            try:
                window = self.build_validation_window_for_days(
                    user_id, start_day, end_day
                )
                num_meals = len(
                    [x for x in window.carb_replay_events if x[1] > 0]
                )
                num_boluses = len(
                    [x for x in window.insulin_reference if x[1] > 0]
                )
                duration_h = window.duration_minutes / 60.0

                notes = (
                    f"{num_meals} meals, {num_boluses} boluses, "
                    f"{duration_h:.1f}h"
                )
                print(
                    f"{user_id:>8} | {start_day:>12} | "
                    f"{end_day:>12} | {notes}"
                )
            except ValueError:
                pass

        print("=" * 70 + "\n")

    def save_validation_windows_to_file(self, output_path: str | Path) -> None:
        """Save selected validation windows to a text file.

        Args:
            output_path: File path where window list will be written.
        """
        windows = self.get_best_validation_windows()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open(mode="w", encoding="utf-8") as f:
            f.write("Phase 1 Validation Windows\n")
            f.write("=" * 70 + "\n\n")

            for user_id, start_day, end_day in windows:
                try:
                    window = self.build_validation_window_for_days(
                        user_id, start_day, end_day
                    )
                    num_meals = len(
                        [x for x in window.carb_replay_events if x[1] > 0]
                    )
                    num_boluses = len(
                        [x for x in window.insulin_reference if x[1] > 0]
                    )
                    duration_h = window.duration_minutes / 60.0

                    f.write(f"User: {user_id}\n")
                    f.write(
                        f"Date Range: {start_day} to {end_day} "
                        f"({duration_h:.1f} hours)\n"
                    )
                    f.write(
                        f"Dynamics: {num_meals} meals, {num_boluses} boluses\n"
                    )
                    f.write(
                        f"Initial glucose: "
                        f"{window.initial_glucose_mmol_l:.2f} mmol/L\n"
                    )
                    f.write("\n")

                except ValueError:
                    pass
