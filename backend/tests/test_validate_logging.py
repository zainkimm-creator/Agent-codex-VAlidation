import csv
import json
from pathlib import Path

from backend.validation.validate_logging import run_logging_validation


def test_logging_validation_writes_required_outputs(tmp_path: Path):
    result = run_logging_validation(
        tlog_ms_values=[1, 2, 5],
        duration_s=0.03,
        output_root=tmp_path,
    )

    csv_path = Path(result["csv_path"])
    figure_path = Path(result["figure_path"])
    summary_path = Path(result["summary_path"])
    assert csv_path == tmp_path / "csv" / "logging_results.csv"
    assert figure_path == tmp_path / "figures" / "tlog_vs_rmse.png"
    assert summary_path == tmp_path / "validation_runs" / "latest" / "logging_validation.json"
    assert csv_path.exists()
    assert figure_path.read_bytes().startswith(b"\x89PNG")
    assert summary_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert {row["dashboard_case"] for row in rows} == {"NF", "SN"}
    for case_name in ("NF", "SN"):
        case_rows = [row for row in rows if row["dashboard_case"] == case_name]
        assert [int(row["Tlog_ms"]) for row in case_rows] == [1, 2, 5]
        assert {row["noise_enabled"] for row in case_rows} == {"True" if case_name == "SN" else "False"}
    assert "pass_fail_status" in rows[0]
    assert "trend_status" in rows[0]

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["paper_targets"]["sweep_ms"]
    assert "best_SN_Tlog_ms" in summary
    assert summary["pass_fail_status"] in {"pass", "fail"}
