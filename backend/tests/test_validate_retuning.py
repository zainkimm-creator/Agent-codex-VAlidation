import csv
import json
from pathlib import Path

from backend.validation.validate_retuning import run_retuning_validation


def test_retuning_validation_writes_dashboard_outputs(tmp_path: Path):
    result = run_retuning_validation(output_root=tmp_path)

    csv_path = Path(result["csv_path"])
    figure_path = Path(result["figure_path"])
    summary_path = Path(result["summary_path"])

    assert csv_path == tmp_path / "csv" / "retuning_results.csv"
    assert figure_path == tmp_path / "figures" / "retuning_cost.svg"
    assert summary_path == tmp_path / "validation_runs" / "latest" / "retuning_validation.json"
    assert csv_path.exists()
    assert figure_path.exists()
    assert summary_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["method"] for row in rows} == {"CS-BO(30)", "HGS-only", "HGS+BO(5)", "HGS+BO(10)"}

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["supports_HGS_BO5_fewer_real_evaluations_than_CS_BO30"] is True
    assert summary["pass_fail_status"] == "pass"
