import csv
import json
from pathlib import Path

from backend.validation.validate_drift import run_drift_validation


def test_drift_validation_writes_dashboard_outputs(tmp_path: Path):
    result = run_drift_validation(output_root=tmp_path)

    csv_path = Path(result["csv_path"])
    figure_path = Path(result["figure_path"])
    summary_path = Path(result["summary_path"])

    assert csv_path == tmp_path / "csv" / "drift_results.csv"
    assert figure_path == tmp_path / "figures" / "drift_degradation.svg"
    assert summary_path == tmp_path / "validation_runs" / "latest" / "drift_validation.json"
    assert csv_path.exists()
    assert figure_path.exists()
    assert summary_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["scenario"] for row in rows} == {"EA", "f", "J"}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["dominant_degradation_source"] == "J"
    assert summary["pass_fail_status"] == "pass"
