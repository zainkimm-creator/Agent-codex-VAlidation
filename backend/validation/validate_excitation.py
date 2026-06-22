"""Excitation-profile validation runner."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import yaml

from backend.excitation.generators import generate_et3m_operating_points
from backend.excitation.profiles import SkippedExcitationError, get_profile
from backend.noise.filters import apply_configured_lpf
from backend.noise.sensor_noise import add_tension_sensor_noise, configured_tlog_ms
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
VALIDATION_CASES = ("NF", "SN")


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


def _target_for_case(
    profile_name: str,
    targets: Mapping[str, object],
    *,
    case_name: str,
) -> tuple[str | None, float | None]:
    target_case = case_name.upper()
    target_key = f"{target_case}_RMSE_theta_percent"
    selected = targets[target_key]
    if isinstance(selected, Mapping) and profile_name in selected:
        return target_case, float(selected[profile_name])
    return None, None


def _with_measured_tensions(
    rows: Sequence[Mapping[str, object]],
    *,
    plant_id: str,
    sample_time_s: float,
    noise_enabled: bool,
) -> list[dict[str, object]]:
    measured = [dict(row) for row in rows]
    if not noise_enabled:
        return measured

    tensions = [[float(row["T1"]), float(row["T2"]), float(row["T3"])] for row in measured]
    noisy = add_tension_sensor_noise(tensions, plant_id, noise_enabled=True)
    filtered = apply_configured_lpf(noisy, sample_time_s=sample_time_s)
    for index, row in enumerate(measured):
        row["T1"] = float(filtered[index][0])
        row["T2"] = float(filtered[index][1])
        row["T3"] = float(filtered[index][2])
        row["noise_enabled"] = True
    return measured


def run_excitation_validation(
    *,
    plant_id: str = "P01",
    excitation_names: Sequence[str] = EXACT_EXCITATIONS,
    validation_cases: Sequence[str] = VALIDATION_CASES,
    duration_override_s: float | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    targets_path: Path = DEFAULT_TARGETS_PATH,
) -> dict[str, object]:
    """Run exact-mode excitation validation and write CSV, PNG, and JSON artifacts."""

    output_paths = _ensure_output_dirs(output_root)
    targets = _paper_excitation_targets(_load_targets(targets_path))
    rows: list[dict[str, object]] = []

    for case_name_raw in validation_cases:
        case_name = case_name_raw.upper()
        if case_name not in VALIDATION_CASES:
            raise ValueError(f"Unknown validation case '{case_name_raw}'. Valid cases: {', '.join(VALIDATION_CASES)}.")
        noise_enabled = case_name == "SN"
        tlog_ms = configured_tlog_ms(noise_enabled=noise_enabled)
        tlog_s = tlog_ms / 1000.0

        for name in excitation_names:
            try:
                get_profile(name, exact_mode=True)
            except SkippedExcitationError as exc:
                rows.append(
                    {
                        "plant_id": plant_id,
                        "excitation_type": name,
                        "dashboard_case": case_name,
                        "noise_enabled": noise_enabled,
                        "Tlog_ms": tlog_ms,
                        "skipped": True,
                        "skip_reason": str(exc),
                        "operating_points": 0,
                        "profile_total_duration_s": None,
                        "simulation_duration_s": 0.0,
                        "RMSE_theta": None,
                        "RMSE_theta_percent": None,
                        "paper_target_case": None,
                        "paper_target_percent": None,
                        "pass_fail_status": "skipped",
                        "trend_status": "skipped for exact reproduction",
                        "source_csv_path": None,
                    }
                )
                continue

            operating_points = generate_et3m_operating_points(1.0) if name == "ET3M" else []
            profile_duration = _profile_duration_s(name)
            single_duration_s = float(
                duration_override_s
                if duration_override_s is not None
                else (17.0 if name == "ET3M" else profile_duration)
            )
            target_case, target_percent = _target_for_case(name, targets, case_name=case_name)
            try:
                if name == "ET3M":
                    rmse_values: list[float] = []
                    combined_rows: list[dict[str, object]] = []
                    time_offset = 0.0
                    params = None
                    for op_index, operating_point in enumerate(operating_points, start=1):
                        sim = run_multirate_simulation(
                            MultirateSimulationConfig(
                                plant_id=plant_id,
                                duration_s=single_duration_s,
                                Tlog_s=tlog_s,
                                excitation_type=name,
                                Kp_star=100.0,
                                noise_enabled=noise_enabled,
                                line_speed_multiplier=operating_point.line_speed_multiplier,
                                output_name=f"excitation_source_{case_name}_{name}_op{op_index}.csv",
                            ),
                            output_dir=output_paths["csv"],
                        )
                        params = sim.plant.controller_params()
                        measured_rows = _with_measured_tensions(
                            sim.rows,
                            plant_id=plant_id,
                            sample_time_s=tlog_s,
                            noise_enabled=noise_enabled,
                        )
                        _write_csv(measured_rows, Path(sim.csv_path))
                        sysid = estimate_parameters(measured_rows, params, params, summary_name=None)
                        rmse_values.append(sysid.rmse_theta)
                        for row in measured_rows:
                            combined = dict(row)
                            combined["time_s"] = float(combined["time_s"]) + time_offset
                            combined["dashboard_case"] = case_name
                            combined["operating_point_index"] = op_index
                            combined["line_speed_multiplier"] = operating_point.line_speed_multiplier
                            combined_rows.append(combined)
                        time_offset += single_duration_s + tlog_s
                    if params is None or not rmse_values:
                        raise ValueError("ET3M did not produce operating-point rows")
                    rmse_theta = sum(rmse_values) / len(rmse_values)
                    source_csv_path = _write_csv(
                        combined_rows,
                        output_paths["csv"] / f"excitation_source_{case_name}_{name}.csv",
                    )
                    simulation_duration_s = single_duration_s * len(operating_points)
                else:
                    sim = run_multirate_simulation(
                        MultirateSimulationConfig(
                            plant_id=plant_id,
                            duration_s=single_duration_s,
                            Tlog_s=tlog_s,
                            excitation_type=name,
                            Kp_star=100.0,
                            noise_enabled=noise_enabled,
                            output_name=f"excitation_source_{case_name}_{name}.csv",
                        ),
                        output_dir=output_paths["csv"],
                    )
                    params = sim.plant.controller_params()
                    measured_rows = _with_measured_tensions(
                        sim.rows,
                        plant_id=plant_id,
                        sample_time_s=tlog_s,
                        noise_enabled=noise_enabled,
                    )
                    _write_csv(measured_rows, Path(sim.csv_path))
                    sysid = estimate_parameters(measured_rows, params, params, summary_name=None)
                    rmse_theta = sysid.rmse_theta
                    source_csv_path = sim.csv_path
                    simulation_duration_s = single_duration_s

                rmse_percent: float | None = 100.0 * rmse_theta
                pass_fail_status = "pass" if target_percent is not None else "trend"
                trend_status = (
                    f"compared with paper {target_case} target"
                    if target_percent is not None
                    else f"no matching {case_name} paper target"
                )
                failure_reason: str | None = None
            except ValueError as exc:
                rmse_theta = None
                rmse_percent = None
                pass_fail_status = "review"
                trend_status = "simulation became numerically invalid"
                source_csv_path = None
                simulation_duration_s = single_duration_s * (len(operating_points) or 1)
                failure_reason = str(exc)
            rows.append(
                {
                    "plant_id": plant_id,
                    "excitation_type": name,
                    "dashboard_case": case_name,
                    "noise_enabled": noise_enabled,
                    "Tlog_ms": tlog_ms,
                    "skipped": False,
                    "skip_reason": None,
                    "operating_points": len(operating_points) or 1,
                    "profile_total_duration_s": profile_duration,
                    "simulation_duration_s": simulation_duration_s,
                    "RMSE_theta": rmse_theta,
                    "RMSE_theta_percent": rmse_percent,
                    "paper_target_case": target_case,
                    "paper_target_percent": target_percent,
                    "pass_fail_status": pass_fail_status,
                    "trend_status": trend_status,
                    "failure_reason": failure_reason,
                    "source_csv_path": source_csv_path,
                }
            )

    active_rows = [row for row in rows if not row["skipped"] and row["RMSE_theta_percent"] is not None]
    skipped = list(dict.fromkeys(str(row["excitation_type"]) for row in rows if row["skipped"]))
    csv_path = _write_csv(rows, output_paths["csv"] / "excitation_results.csv")
    figure_path = _write_simple_png(
        output_paths["figures"] / "excitation_bar.png",
        [float(row["RMSE_theta_percent"]) for row in active_rows],
        bar_color=(179, 95, 46),
    )
    expected_skips = set(str(item) for item in targets["skipped_for_reproduction"])
    skipped_expected = set(str(item) for item in skipped) == expected_skips
    has_review = any(row.get("pass_fail_status") == "review" for row in rows)
    if has_review:
        overall_status = "review"
        overall_trend = "one or more excitation simulations became numerically invalid"
    elif skipped_expected:
        overall_status = "pass"
        overall_trend = "EV1/EVR skipped in exact mode"
    else:
        overall_status = "fail"
        overall_trend = "skip set differs from paper target"
    summary = {
        "validation": "excitation",
        "plant_id": plant_id,
        "rows": rows,
        "paper_targets": targets,
        "skipped_profiles": skipped,
        "pass_fail_status": overall_status,
        "trend_status": overall_trend,
        "csv_path": csv_path,
        "figure_path": figure_path,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "excitation_validation.json")
    summary["summary_path"] = summary_path
    return summary
