"""Closed-loop multirate R2R simulator.

The simulator uses a fixed 1 ms RK4 plant step, a 10 ms controller sample
period, zero-order-held motor torque between controller updates, and a
configurable logging period.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

import yaml

from backend.excitation.generators import tension_reference_delta
from backend.excitation.profiles import SkippedExcitationError
from backend.models.controller import CascadePIController, ControllerConfig
from backend.models.equations import R2RParameters
from backend.models.r2r_dynamics import R2RDynamicsParams, r2r_derivatives, surface_velocities
from backend.models.rk4 import rk4_step

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLANT_CONFIG = PROJECT_ROOT / "configs" / "plants_p01_p10.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

REQUIRED_COLUMNS = (
    "time_s",
    "T1",
    "T2",
    "T3",
    "omega_UW",
    "omega_Nip",
    "omega_RW",
    "v_UW",
    "v_Nip",
    "v_RW",
    "u_UW",
    "u_Nip",
    "u_RW",
    "Tref1",
    "Tref2",
    "Tref3",
    "plant_id",
    "excitation_type",
    "Tlog_ms",
    "Kp_star",
    "noise_enabled",
)


@dataclass(frozen=True)
class PlantConfig:
    """Plant values loaded from `configs/plants_p01_p10.yaml`."""

    plant_id: str
    EA_N: float
    v_ref_mps: float
    T_ref_N: float
    R_m: tuple[float, float, float]
    J_kgm2: tuple[float, float, float]
    f_Nms_per_rad: tuple[float, float, float]
    L_m: tuple[float, float, float]

    @property
    def target_tensions_N(self) -> tuple[float, float, float]:
        return (self.T_ref_N, self.T_ref_N, self.T_ref_N)

    def dynamics_params(self) -> R2RDynamicsParams:
        return R2RDynamicsParams(
            EA_N=self.EA_N,
            L_m=self.L_m,
            R_m=self.R_m,
            J_kgm2=self.J_kgm2,
            f_Nms_per_rad=self.f_Nms_per_rad,
            v_ref_mps=self.v_ref_mps,
        )

    def controller_params(self) -> R2RParameters:
        return R2RParameters(
            span_length_m=self.L_m,
            roller_radius_m=self.R_m,
            inertia_kg_m2=self.J_kgm2,
            tension_ref_N=self.target_tensions_N,
            kf_UW=self.f_Nms_per_rad[0],
            kf_Nip=self.f_Nms_per_rad[1],
            kf_RW=self.f_Nms_per_rad[2],
            EA=self.EA_N,
            feeder_velocity_m_s=self.v_ref_mps,
        )


@dataclass(frozen=True)
class MultirateSimulationConfig:
    """Closed-loop multirate simulation settings."""

    plant_id: str = "P01"
    duration_s: float = 0.2
    dt_s: float = 0.001
    Ts_s: float = 0.010
    Tlog_s: float = 0.020
    Kp_star: float = 0.0525
    excitation_type: str = "none"
    noise_enabled: bool = False
    output_name: str = "multirate_simulation.csv"
    plant_config_path: Path = DEFAULT_PLANT_CONFIG

    def __post_init__(self) -> None:
        for name in ("duration_s", "dt_s", "Ts_s", "Tlog_s"):
            value = getattr(self, name)
            if value <= 0 or not math.isfinite(value):
                raise ValueError(f"{name} must be finite and positive")
        if abs(round(self.Ts_s / self.dt_s) - (self.Ts_s / self.dt_s)) > 1e-9:
            raise ValueError("Ts_s must be an integer multiple of dt_s")
        if abs(round(self.Tlog_s / self.dt_s) - (self.Tlog_s / self.dt_s)) > 1e-9:
            raise ValueError("Tlog_s must be an integer multiple of dt_s")


@dataclass
class MultirateSimulationResult:
    rows: list[dict[str, float | str | bool]]
    csv_path: str
    plant: PlantConfig
    integration_steps_per_control: int
    log_steps: int
    control_update_steps: list[int]


def _tuple3(values: Sequence[object], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly 3 values")
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def load_plant_config(
    plant_id: str = "P01",
    config_path: Path = DEFAULT_PLANT_CONFIG,
) -> PlantConfig:
    """Load one plant from the YAML professor-details config."""

    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    plants = payload.get("plants", {}) if isinstance(payload, Mapping) else {}
    if plant_id not in plants:
        valid = ", ".join(sorted(str(key) for key in plants))
        raise ValueError(f"Unknown plant_id '{plant_id}'. Valid plants: {valid}.")
    row = plants[plant_id]
    return PlantConfig(
        plant_id=plant_id,
        EA_N=float(row["EA_N"]),
        v_ref_mps=float(row["v_ref_mps"]),
        T_ref_N=float(row["T_ref_N"]),
        R_m=_tuple3(row["R_m"], "R_m"),
        J_kgm2=_tuple3(row["J_kgm2"], "J_kgm2"),
        f_Nms_per_rad=_tuple3(row["f_Nms_per_rad"], "f_Nms_per_rad"),
        L_m=_tuple3(row["L_m"], "L_m"),
    )


def _initial_state(plant: PlantConfig) -> tuple[float, ...]:
    omega = tuple(plant.v_ref_mps / radius for radius in plant.R_m)
    return plant.target_tensions_N + omega


def _profile_name_for_simulation(excitation_type: str) -> str | None:
    normalized = excitation_type.strip()
    if not normalized or normalized.lower() == "none":
        return None
    if normalized == "ET3M":
        return "ET3"
    return normalized


def _target_tensions_at_time(
    plant: PlantConfig,
    excitation_type: str,
    time_s: float,
) -> tuple[float, float, float]:
    profile_name = _profile_name_for_simulation(excitation_type)
    if profile_name is None:
        return plant.target_tensions_N
    try:
        delta = tension_reference_delta(profile_name, time_s, plant.target_tensions_N, exact_mode=True)
    except (SkippedExcitationError, ValueError):
        return plant.target_tensions_N
    return tuple(plant.target_tensions_N[i] + delta[i] for i in range(3))  # type: ignore[return-value]


def _write_csv(rows: Sequence[dict[str, float | str | bool]], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def run_multirate_simulation(
    config: MultirateSimulationConfig | None = None,
    output_dir: Path | None = None,
) -> MultirateSimulationResult:
    """Run closed-loop R2R simulation with RK4, sampled control, and ZOH torque."""

    active_config = config or MultirateSimulationConfig()
    plant = load_plant_config(active_config.plant_id, active_config.plant_config_path)
    dynamics_params = plant.dynamics_params()
    controller_params = plant.controller_params()
    controller = CascadePIController(
        ControllerConfig(
            target_tension_N=plant.target_tensions_N,
            line_speed_m_s=plant.v_ref_mps,
            Kp_star=active_config.Kp_star,
        )
    )

    state = _initial_state(plant)
    held_torque = (0.0, 0.0, 0.0)
    rows: list[dict[str, float | str | bool]] = []
    control_update_steps: list[int] = []
    control_interval_steps = int(round(active_config.Ts_s / active_config.dt_s))
    log_interval_steps = int(round(active_config.Tlog_s / active_config.dt_s))
    total_steps = int(round(active_config.duration_s / active_config.dt_s))

    for step in range(total_steps + 1):
        time_s = step * active_config.dt_s
        target_tensions = _target_tensions_at_time(plant, active_config.excitation_type, time_s)
        if step % control_interval_steps == 0:
            controller.config = replace(controller.config, target_tension_N=target_tensions)
            action = controller.update(state, active_config.Ts_s, controller_params)
            held_torque = action.motor_torque_Nm
            control_update_steps.append(step)

        if step % log_interval_steps == 0:
            v_uw, v_nip, v_rw = surface_velocities(state, dynamics_params)
            row = {
                "time_s": time_s,
                "T1": state[0],
                "T2": state[1],
                "T3": state[2],
                "omega_UW": state[3],
                "omega_Nip": state[4],
                "omega_RW": state[5],
                "v_UW": v_uw,
                "v_Nip": v_nip,
                "v_RW": v_rw,
                "u_UW": held_torque[0],
                "u_Nip": held_torque[1],
                "u_RW": held_torque[2],
                "Tref1": target_tensions[0],
                "Tref2": target_tensions[1],
                "Tref3": target_tensions[2],
                "plant_id": plant.plant_id,
                "excitation_type": active_config.excitation_type,
                "Tlog_ms": active_config.Tlog_s * 1000.0,
                "Kp_star": active_config.Kp_star,
                "noise_enabled": active_config.noise_enabled,
            }
            rows.append(row)

        if step < total_steps:
            state = rk4_step(
                r2r_derivatives,
                state,
                held_torque,
                dynamics_params,
                active_config.dt_s,
            )

    csv_path = _write_csv(rows, (output_dir or DEFAULT_OUTPUT_DIR) / active_config.output_name)
    return MultirateSimulationResult(
        rows=rows,
        csv_path=csv_path,
        plant=plant,
        integration_steps_per_control=control_interval_steps,
        log_steps=log_interval_steps,
        control_update_steps=control_update_steps,
    )
