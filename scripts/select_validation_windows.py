#!/usr/bin/env python3
"""Select best validation windows from GlucoBench data.

Finds full-day windows with sufficient dynamics (multiple meals and boluses)
for use in model validation and tuning.

Usage:
    python scripts/select_validation_windows.py
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.benchmark_loader import GlucoBenchLoader


def main() -> None:
    """Load data and select validation windows."""
    data_path = project_root / "data" / "GlucoBench_benchmark_dataset.csv"

    if not data_path.exists():
        print(f"Error: GlucoBench data not found at {data_path}")
        sys.exit(1)

    print(f"Loading GlucoBench data from: {data_path}")
    loader = GlucoBenchLoader(data_path)

    print(f"Found {len(loader.get_user_ids())} users in dataset\n")

    # Find and display validation windows
    print("Searching for validation windows...")
    print("Criteria: ≥3 meals, ≥2 boluses, contiguous data\n")
    loader.print_validation_windows()

    # Save to file
    output_txt = (
        project_root / "project_files" / "phase1_validation_windows.txt"
    )
    print(f"Saving validation windows to: {output_txt}")
    loader.save_validation_windows_to_file(output_txt)
    print("✅ Done!")


if __name__ == "__main__":
    main()
