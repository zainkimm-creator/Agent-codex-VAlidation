from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.validation.validate_noise_lpf import run_noise_lpf_validation


if __name__ == "__main__":
    result = run_noise_lpf_validation()
    print(f"noise_lpf_csv={result['csv_path']}")
    print(f"noise_lpf_summary={result['summary_path']}")
