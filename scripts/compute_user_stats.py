#!/usr/bin/env python3
"""Compute per-user baseline statistics from GlucoBench data.

This script loads the GlucoBench dataset, computes median glucose, percentiles,
and average meal/insulin values for each user, and saves results to CSV.

Usage:
    python scripts/compute_user_stats.py
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.benchmark_loader import GlucoBenchLoader


def main() -> None:
    """Load data, compute statistics, print table, and save CSV."""
    data_path = project_root / "data" / "CGM.csv"

    if not data_path.exists():
        print(f"Error: GlucoBench data not found at {data_path}")
        sys.exit(1)

    print(f"Loading GlucoBench data from: {data_path}")
    loader = GlucoBenchLoader(data_path)

    print(f"Found {len(loader.get_user_ids())} users in dataset")
    print()

    # Compute and display statistics
    loader.print_user_stats_table()

    # Save to CSV
    output_csv = project_root / "project_files" / "user_baselines.csv"
    print(f"Saving user statistics to: {output_csv}")
    loader.save_user_stats_to_csv(output_csv)
    print("✅ Done!")


if __name__ == "__main__":
    main()
