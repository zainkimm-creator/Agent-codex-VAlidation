from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.validation.validate_drift import run_drift_validation


if __name__ == "__main__":
    result = run_drift_validation()
    print(f"drift_csv={result['csv_path']}")
    print(f"drift_figure={result['figure_path']}")
    print(f"drift_summary={result['summary_path']}")
