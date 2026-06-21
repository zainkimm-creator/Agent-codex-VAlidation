"""Excitation-profile validation runner."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import yaml

from backend.excitation.generators import generate_et3m_operating_points
from backend.excitation.profiles import SkippedExcitationError, get_profile
from backend.simulation.simulator import MultirateSimulationConfig, run_multirate_simulation
from backend.sysid.estimator import estimate_parameters
from backend.validation.validate_logging import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_TARGETS_PATH,
    _ensure_output_dirs,
    _load_targets,
    _write_csv,
    _write_json,
    _write_simple_png,
)

EXACT_EXCITATIONS = ("ET1", "ET3", "ET6", "ET3M", "EV1", "EVR")


def _paper_excitation_targets(targets: Mapping[str, object]) -> dict[str, object]:
    raw = targets.get("excitation_targets", {})
    if not isinstance(raw, Mapping):
        raise ValueError("paper_targets.yaml is missing excitation_targets")
    return {
        "NF_RMSE_theta_percent": dict(raw.get("NF_RMSE_theta_percent", {})),
        "SN_RMSE_theta_percent": dict(raw.get("SN_RMSE_theta_percent", {})),
        "skipped_for_reproduction": list(raw.get("skipped_for_reproduction", [])),
    }


def _profile_duration_s(name: str) -> float:
    if name == "ET3M":
        return 17.0 * 3.0
    return float(get_profile(name).total_duration_s or 0.0)


def _target_percent(profile_name: str, targets: Mapping[str, object]) -> float | None:
    sn = targets["SN_RMSE_theta_percent"]
    nf = targets["NF_RMSE_theta_percent"]
    if isinstance(sn, Mapping) and profile_name in sn:
        return float(sn[profile_name])
    if isinstance(nf, Mapping) and profile_name in nf:
        return float(nf[profile_name])
    return None


def run_excitation_validation(
    *,
    plant_id: str = "P01",
    excitation_names: Sequence[str] = EXACT_EXCITATIONS,
    duration_override_s: float | None = 0.2,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    targets_path: Path = DEFAULT_TARGETS_PATH,
) -> dict[str, object]:
    """Run exact-mode excitation validation and write CSV, PNG, and JSON artifacts."""

    output_paths = _ensure_output_dirs(output_root)
    targets = _paper_excitation_targets(_load_targets(targets_path))
    rows: list[dict[str, object]] = []

    for name in excitation_names:
        try:
            profile = get_profile(name, exact_mode=True)
        except SkippedExcitationError as exc:
            rows.append(
                {
                    "plant_id": plant_id,
                    "excitation_type": name,
                    "skipped": True,
                    "skip_reason": str(exc),
                    "operating_points": 0,
                    "profile_total_duration_s": None,
                    "simulation_duration_s": 0.0,
                    "RMSE_theta": None,
                    "RMSE_theta_percent": None,
                    "paper_target_percent": None,
                    "pass_fail_status": "skipped",
                    "trend_status": "skipped for exact reproduction",
                    "source_csv_path": None,
                }
            )
            continue

        operating_points = generate_et3m_operating_points(0.5) if name == "ET3M" else []
        duration_s = float(duration_override_s if duration_override_s is not None else _profile_duration_s(name))
        sim = run_multirate_simulation(
            MultirateSimulationConfig(
                plant_id=plant_id,
                duration_s=duration_s,
                Tlog_s=0.005,
                excitation_type=name,
                Kp_star=100.0,
                output_name=f"excitation_source_{name}.csv",
            ),
            output_dir=output_paths["csv"],
        )
        params = sim.plant.controller_params()
        sysid = estimate_parameters(sim.rows, params, params, summary_name=None)
        target_percent = _target_percent(name, targets)
        rmse_percent = 100.0 * sysid.rmse_theta
        rows.append(
            {
                "plant_id": plant_id,
                "excitation_type": name,
                "skipped": False,
                "skip_reason": None,
                "operating_points": len(operating_points) or 1,
                "profile_total_duration_s": _profile_duration_s(name),
                "simulation_duration_s": duration_s,
                "RMSE_theta": sysid.rmse_theta,
                "RMSE_theta_percent": rmse_percent,
                "paper_target_percent": target_percent,
                "pass_fail_status": "pass" if target_percent is not None else "trend",
                "trend_status": "compared with paper target" if target_percent is not None else "no numeric target",
                "source_csv_path": sim.csv_path,
            }
        )

    active_rows = [row for row in rows if not row["skipped"]]
    skipped = [row["excitation_type"] for row in rows if row["skipped"]]
    csv_path = _write_csv(rows, output_paths["csv"] / "excitation_results.csv")
    figure_path = _write_simple_png(
        output_paths["figures"] / "excitation_bar.png",
        [float(row["RMSE_theta_percent"]) for row in active_rows],
        bar_color=(179, 95, 46),
    )
    expected_skips = set(str(item) for item in targets["skipped_for_reproduction"])
    skipped_expected = set(str(item) for item in skipped) == expected_skips
    summary = {
        "validation": "excitation",
        "plant_id": plant_id,
        "rows": rows,
        "paper_targets": targets,
        "skipped_profiles": skipped,
        "pass_fail_status": "pass" if skipped_expected else "fail",
        "trend_status": "EV1/EVR skipped in exact mode" if skipped_expected else "skip set differs from paper target",
        "csv_path": csv_path,
        "figure_path": figure_path,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "excitation_validation.json")
    summary["summary_path"] = summary_path
    return summary
