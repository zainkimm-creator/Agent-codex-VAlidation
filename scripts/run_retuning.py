from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.validation.validate_retuning import run_retuning_validation


if __name__ == "__main__":
    result = run_retuning_validation()
    print(f"retuning_csv={result['csv_path']}")
    print(f"retuning_figure={result['figure_path']}")
    print(f"retuning_summary={result['summary_path']}")
