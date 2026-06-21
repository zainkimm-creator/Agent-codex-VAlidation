"""Retuning validation runner that writes dashboard-facing artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from backend.validation.studies import retuning_study
from backend.validation.validate_logging import DEFAULT_OUTPUT_ROOT, _ensure_output_dirs, _write_csv, _write_json


def _copy_artifact(source: str | None, destination: Path) -> str | None:
    if not source:
        return None
    source_path = Path(source)
    if not source_path.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source_path.read_bytes())
    return str(destination)


def run_retuning_validation(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, object]:
    """Run retuning study and save CSV, SVG, and JSON outputs for the dashboard."""

    output_paths = _ensure_output_dirs(output_root)
    result = retuning_study()
    payload = result["metrics"]
    if not isinstance(payload, Mapping):
        raise ValueError("retuning_study returned invalid metrics payload")

    rows = list(payload.get("metrics", []))
    csv_path = _write_csv(rows, output_paths["csv"] / "retuning_results.csv")
    figure_path = _copy_artifact(
        str(payload.get("plot_path") or result.get("plot_path") or ""),
        output_paths["figures"] / "retuning_cost.svg",
    )
    supports_hgs5 = bool(payload.get("supports_HGS_BO5_fewer_real_evaluations_than_CS_BO30"))
    summary = {
        "validation": "retuning",
        "rows": rows,
        "cost_function": payload.get("cost_function"),
        "supports_HGS_BO5_fewer_real_evaluations_than_CS_BO30": supports_hgs5,
        "pass_fail_status": "pass" if supports_hgs5 else "review",
        "trend_status": "HGS+BO(5) uses fewer real evaluations" if supports_hgs5 else "evaluation budget check failed",
        "csv_path": csv_path,
        "figure_path": figure_path,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "retuning_validation.json")
    summary["summary_path"] = summary_path
    return summary
