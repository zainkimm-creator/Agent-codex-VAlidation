from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.validation.validate_logging import DEFAULT_OUTPUT_ROOT, run_logging_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run logging-rate validation.")
    parser.add_argument("--plant-id", default="P01")
    parser.add_argument("--duration-s", type=float, default=0.2)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    result = run_logging_validation(
        plant_id=args.plant_id,
        duration_s=args.duration_s,
        output_root=args.output_root,
    )
    print(f"logging_csv={result['csv_path']}")
    print(f"logging_figure={result['figure_path']}")
    print(f"logging_summary={result['summary_path']}")


if __name__ == "__main__":
    main()
