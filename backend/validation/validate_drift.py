"""Drift validation runner that writes dashboard-facing artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from backend.validation.studies import drift_study
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


def run_drift_validation(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, object]:
    """Run drift study and save CSV, SVG, and JSON outputs for the dashboard."""

    output_paths = _ensure_output_dirs(output_root)
    result = drift_study()
    payload = result["metrics"]
    if not isinstance(payload, Mapping):
        raise ValueError("drift_study returned invalid metrics payload")

    rows = list(payload.get("metrics", []))
    csv_path = _write_csv(rows, output_paths["csv"] / "drift_results.csv")
    figure_path = _copy_artifact(
        str(payload.get("plot_path") or result.get("plot_path") or ""),
        output_paths["figures"] / "drift_degradation.svg",
    )
    supports_j = bool(payload.get("supports_J_drift_dominance"))
    summary = {
        "validation": "drift",
        "rows": rows,
        "dominant_degradation_source": payload.get("dominant_degradation_source"),
        "supports_J_drift_dominance": supports_j,
        "EA_drift_note": payload.get("EA_drift_note"),
        "pass_fail_status": "pass" if supports_j else "review",
        "trend_status": "J drift dominant" if supports_j else "J drift not dominant",
        "csv_path": csv_path,
        "figure_path": figure_path,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "drift_validation.json")
    summary["summary_path"] = summary_path
    return summary
