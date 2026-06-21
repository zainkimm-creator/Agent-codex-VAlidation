"""Seven-parameter one-step prediction-error SysID estimator."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import yaml
from scipy.optimize import least_squares

from backend.models.equations import INPUT_NAMES, PARAMETER_NAMES, R2RParameters
from backend.sysid.cost import (
    one_step_prediction_cost,
    one_step_prediction_residuals,
    surface_velocity,
    theta_array,
    theta_dict,
    theta_from_params,
    time_steps,
    validate_sysid_rows,
)
from backend.sysid.metrics import parameter_error_table, rmse_theta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUMMARY_DIR = PROJECT_ROOT / "reports" / "validation_summary"
DEFAULT_PLANT_CONFIG = PROJECT_ROOT / "configs" / "plants_p01_p10.yaml"


@dataclass
class SysIDResult:
    theta_est: dict[str, float]
    rmse_theta: float
    error_table: list[dict[str, float | str]]
    convergence_status: str
    success: bool
    cost: float
    nfev: int
    summary_path: str | None = None

    @property
    def estimates(self) -> dict[str, float]:
        """Backward-compatible alias used by the API and older tests."""

        return self.theta_est

    def to_dict(self) -> dict[str, object]:
        return {
            "theta_est": self.theta_est,
            "estimates": self.estimates,
            "RMSE_theta": self.rmse_theta,
            "error_table": self.error_table,
            "convergence_status": self.convergence_status,
            "success": self.success,
            "cost": self.cost,
            "nfev": self.nfev,
            "summary_path": self.summary_path,
        }


def load_rows_from_csv(path: str | Path) -> list[dict[str, float]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: float(value) for key, value in row.items()} for row in reader]


def load_parameters_from_config(
    plant_id: str = "P01",
    config_path: Path = DEFAULT_PLANT_CONFIG,
) -> R2RParameters:
    """Load plant parameters from `configs/plants_p01_p10.yaml`."""

    target = Path(config_path)
    if not target.exists():
        raise FileNotFoundError(f"Plant config not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    plants = payload.get("plants", {}) if isinstance(payload, Mapping) else {}
    if plant_id not in plants:
        valid = ", ".join(sorted(str(key) for key in plants))
        raise ValueError(f"Unknown plant_id '{plant_id}'. Valid plants: {valid}.")
    row = plants[plant_id]
    return R2RParameters(
        span_length_m=tuple(float(value) for value in row["L_m"]),
        roller_radius_m=tuple(float(value) for value in row["R_m"]),
        inertia_kg_m2=tuple(float(value) for value in row["J_kgm2"]),
        tension_ref_N=(float(row["T_ref_N"]),) * 3,
        kf_UW=float(row["f_Nms_per_rad"][0]),
        kf_Nip=float(row["f_Nms_per_rad"][1]),
        kf_RW=float(row["f_Nms_per_rad"][2]),
        EA=float(row["EA_N"]),
        feeder_velocity_m_s=float(row["v_ref_mps"]),
    )


def _solve_linear_seed(rows: Sequence[Mapping[str, float]], params: R2RParameters) -> dict[str, float]:
    """Compute a deterministic linear least-squares seed for TRF."""

    validate_sysid_rows(rows, params)
    dt_values = time_steps(rows)
    kt_estimates: list[float] = []
    kf_estimates: list[float] = []

    for roller in range(3):
        design: list[list[float]] = []
        target: list[float] = []
        radius = params.roller_radius_m[roller]
        for index, dt in enumerate(dt_values):
            row = rows[index]
            next_row = rows[index + 1]
            velocity = surface_velocity(row, roller, params)
            next_velocity = surface_velocity(next_row, roller, params)
            if roller == 0:
                tension_delta = float(row["T2"]) - float(row["T1"])
            elif roller == 1:
                tension_delta = float(row["T3"]) - float(row["T2"])
            else:
                tension_delta = -float(row["T3"])
            design.append([tension_delta + float(row[INPUT_NAMES[roller]]) / radius, -velocity])
            target.append((next_velocity - velocity) / dt)
        solution, *_ = np.linalg.lstsq(np.asarray(design), np.asarray(target), rcond=None)
        kt_estimates.append(max(1e-9, float(solution[0])))
        kf_estimates.append(max(1e-9, float(solution[1])))

    ea_design: list[float] = []
    ea_target: list[float] = []
    for index, dt in enumerate(dt_values):
        row = rows[index]
        next_row = rows[index + 1]
        velocities = tuple(surface_velocity(row, roller, params) for roller in range(3))
        velocity_prev = (params.feeder_velocity_m_s, velocities[0], velocities[1])
        tensions = (float(row["T1"]), float(row["T2"]), float(row["T3"]))
        tension_prev = (0.0, tensions[0], tensions[1])
        next_tensions = (float(next_row["T1"]), float(next_row["T2"]), float(next_row["T3"]))
        for span in range(3):
            length = params.span_length_m[span]
            observed_dT = (next_tensions[span] - tensions[span]) / dt
            convective = (tension_prev[span] * velocity_prev[span] - tensions[span] * velocities[span]) / length
            ea_design.append((velocities[span] - velocity_prev[span]) / length)
            ea_target.append(observed_dT - convective)
    design = np.asarray(ea_design).reshape(-1, 1)
    target = np.asarray(ea_target)
    if float(np.dot(design[:, 0], design[:, 0])) > 1e-18:
        ea_solution, *_ = np.linalg.lstsq(design, target, rcond=None)
        ea_estimate = max(1e-9, float(ea_solution[0]))
    else:
        ea_estimate = params.EA

    return {
        "kt_UW": kt_estimates[0],
        "kt_Nip": kt_estimates[1],
        "kt_RW": kt_estimates[2],
        "kf_UW": kf_estimates[0],
        "kf_Nip": kf_estimates[1],
        "kf_RW": kf_estimates[2],
        "EA": ea_estimate,
    }


def estimate_parameters(
    rows: Sequence[Mapping[str, float]],
    nominal_params: R2RParameters | None = None,
    true_params: R2RParameters | None = None,
    summary_name: str | None = "sysid_result.json",
    summary_dir: Path | None = None,
    *,
    plant_id: str | None = None,
    config_path: Path | None = None,
    max_nfev: int = 40,
) -> SysIDResult:
    """Estimate the seven paper SysID parameters with SciPy TRF least squares."""

    if nominal_params is not None:
        params = nominal_params
    elif plant_id is not None or config_path is not None:
        params = load_parameters_from_config(plant_id or "P01", config_path or DEFAULT_PLANT_CONFIG)
    else:
        params = R2RParameters()

    validate_sysid_rows(rows, params)
    truth = true_params or params
    theta_true = theta_from_params(truth)

    try:
        initial = theta_array(_solve_linear_seed(rows, params))
    except (ValueError, np.linalg.LinAlgError):
        initial = theta_array(theta_from_params(params))

    lower_bounds = np.full(7, 1e-9)
    upper_bounds = np.full(7, np.inf)
    result = least_squares(
        one_step_prediction_residuals,
        initial,
        args=(rows, params),
        bounds=(lower_bounds, upper_bounds),
        method="trf",
        x_scale=np.maximum(np.abs(initial), 1.0),
        max_nfev=max_nfev,
    )

    theta_est = theta_dict(result.x)
    errors = parameter_error_table(theta_est, theta_true)
    rmse = rmse_theta(theta_est, theta_true)
    convergence_status = f"{result.status}: {result.message}"
    final_cost = one_step_prediction_cost(theta_est, rows, params)

    summary_path = None
    if summary_name:
        target_dir = summary_dir or DEFAULT_SUMMARY_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / summary_name
        target_path.write_text(
            json.dumps(
                {
                    "theta_est": theta_est,
                    "estimates": theta_est,
                    "RMSE_theta": rmse,
                    "error_table": errors,
                    "convergence_status": convergence_status,
                    "success": bool(result.success),
                    "cost": final_cost,
                    "nfev": int(result.nfev),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        summary_path = str(target_path)

    return SysIDResult(
        theta_est=theta_est,
        rmse_theta=rmse,
        error_table=errors,
        convergence_status=convergence_status,
        success=bool(result.success),
        cost=final_cost,
        nfev=int(result.nfev),
        summary_path=summary_path,
    )
