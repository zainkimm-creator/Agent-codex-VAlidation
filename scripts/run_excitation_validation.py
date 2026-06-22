from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.validation.validate_excitation import DEFAULT_OUTPUT_ROOT, run_excitation_validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run excitation-profile validation.")
    parser.add_argument("--plant-id", default="P01")
    parser.add_argument("--duration-s", type=float, default=None)
    parser.add_argument("--case", action="append", choices=["NF", "SN"], dest="cases")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    result = run_excitation_validation(
        plant_id=args.plant_id,
        validation_cases=args.cases or ("NF", "SN"),
        duration_override_s=args.duration_s,
        output_root=args.output_root,
    )
    print(f"excitation_csv={result['csv_path']}")
    print(f"excitation_figure={result['figure_path']}")
    print(f"excitation_summary={result['summary_path']}")


if __name__ == "__main__":
    main()
