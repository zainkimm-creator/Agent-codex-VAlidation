import csv
import json
from pathlib import Path

from backend.validation.validate_excitation import run_excitation_validation


def test_excitation_validation_writes_outputs_and_skips_exact_profiles(tmp_path: Path):
    result = run_excitation_validation(
        duration_override_s=0.05,
        output_root=tmp_path,
    )

    csv_path = Path(result["csv_path"])
    figure_path = Path(result["figure_path"])
    summary_path = Path(result["summary_path"])
    assert csv_path == tmp_path / "csv" / "excitation_results.csv"
    assert figure_path == tmp_path / "figures" / "excitation_bar.png"
    assert summary_path == tmp_path / "validation_runs" / "latest" / "excitation_validation.json"
    assert csv_path.exists()
    assert figure_path.read_bytes().startswith(b"\x89PNG")
    assert summary_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_name = {row["excitation_type"]: row for row in rows}
    cases = {row["dashboard_case"] for row in rows}
    assert {"ET1", "ET3", "ET6", "ET3M", "EV1", "EVR"}.issubset(by_name)
    assert cases == {"NF", "SN"}
    assert by_name["ET1"]["skipped"] == "False"
    assert by_name["ET3"]["skipped"] == "False"
    assert by_name["ET6"]["skipped"] == "False"
    assert by_name["ET3M"]["operating_points"] == "3"
    assert by_name["EV1"]["skipped"] == "True"
    assert by_name["EVR"]["skipped"] == "True"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["skipped_profiles"] == ["EV1", "EVR"]
    assert summary["pass_fail_status"] == "pass"
