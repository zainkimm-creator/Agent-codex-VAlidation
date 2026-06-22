import csv
import json
from pathlib import Path

from backend.validation.validate_noise_lpf import run_noise_lpf_validation


def test_noise_lpf_validation_writes_dashboard_outputs(tmp_path: Path):
    result = run_noise_lpf_validation(output_root=tmp_path)

    csv_path = Path(result["csv_path"])
    summary_path = Path(result["summary_path"])

    assert csv_path == tmp_path / "csv" / "noise_lpf_results.csv"
    assert summary_path == tmp_path / "validation_runs" / "latest" / "noise_lpf_validation.json"
    assert csv_path.exists()
    assert summary_path.exists()

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    sigma_rows = [row for row in rows if row["section"] == "sigma"]
    checks = {row["check"] for row in rows}

    assert len(sigma_rows) == 10
    assert all(row["status"] == "pass" for row in sigma_rows)
    assert {
        "seed reproducibility",
        "noise shape",
        "torque unchanged",
        "LPF cutoff",
        "LPF minimum",
        "LPF shape",
        "NF Tlog",
        "SN Tlog",
    }.issubset(checks)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["sigma_plants_checked"] == 10
    assert summary["sigma_plants_passed"] == 10
    assert summary["pass_fail_status"] == "pass"
