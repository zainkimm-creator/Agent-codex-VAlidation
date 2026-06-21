"""Focused R2R mathematical model for the Model Agent step.

State vector:
    x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]

Input vector:
    u = [u_UW, u_Nip, u_RW]

Units:
    T_i: N
    omega_i: rad/s
    v_i = omega_i * R_i: m/s
    u_i: N*m torque input
    EA: N
    L_i: m
    R_i: m
    J_i: kg*m^2
    f_i: N*m*s/rad
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

STATE_NAMES = ("T1", "T2", "T3", "omega_UW", "omega_Nip", "omega_RW")
INPUT_NAMES = ("u_UW", "u_Nip", "u_RW")
ROLLER_NAMES = ("UW", "Nip", "RW")


def _tuple3(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly 3 values")
    result = tuple(float(value) for value in values)
    if not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def _vector(values: Sequence[float], expected: int, name: str) -> tuple[float, ...]:
    if len(values) != expected:
        raise ValueError(f"{name} must contain exactly {expected} values")
    result = tuple(float(value) for value in values)
    if not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


@dataclass(frozen=True)
class R2RDynamicsParams:
    """Physical parameters for the three-span R2R dynamics."""

    EA_N: float = 3200.0
    L_m: tuple[float, float, float] = (2.0, 3.0, 3.0)
    R_m: tuple[float, float, float] = (0.15, 0.1, 0.15)
    J_kgm2: tuple[float, float, float] = (0.11126, 0.265196, 0.11126)
    f_Nms_per_rad: tuple[float, float, float] = (0.707698, 1.0, 0.707698)
    v_ref_mps: float = 0.5

    def __post_init__(self) -> None:
        object.__setattr__(self, "L_m", _tuple3(self.L_m, "L_m"))
        object.__setattr__(self, "R_m", _tuple3(self.R_m, "R_m"))
        object.__setattr__(self, "J_kgm2", _tuple3(self.J_kgm2, "J_kgm2"))
        object.__setattr__(self, "f_Nms_per_rad", _tuple3(self.f_Nms_per_rad, "f_Nms_per_rad"))

        positive_fields = {
            "EA_N": (self.EA_N,),
            "L_m": self.L_m,
            "R_m": self.R_m,
            "J_kgm2": self.J_kgm2,
            "v_ref_mps": (self.v_ref_mps,),
        }
        for field_name, values in positive_fields.items():
            if any(value <= 0 or not isfinite(value) for value in values):
                raise ValueError(f"{field_name} values must be finite and positive")

        if any(value < 0 or not isfinite(value) for value in self.f_Nms_per_rad):
            raise ValueError("f_Nms_per_rad values must be finite and non-negative")


def surface_velocities(
    state: Sequence[float],
    params: R2RDynamicsParams,
) -> tuple[float, float, float]:
    """Return roller surface velocities `[v_UW, v_Nip, v_RW]` in m/s."""

    _, _, _, omega_uw, omega_nip, omega_rw = _vector(state, 6, "state")
    return (
        omega_uw * params.R_m[0],
        omega_nip * params.R_m[1],
        omega_rw * params.R_m[2],
    )


def r2r_derivatives(
    state: Sequence[float],
    inputs: Sequence[float],
    params: R2RDynamicsParams | None = None,
) -> tuple[float, float, float, float, float, float]:
    """Return `dx/dt` for the R2R state vector.

    Boundary conditions:
        T0 = 0
        T4 = 0
        v0 = params.v_ref_mps
    """

    active_params = params or R2RDynamicsParams()
    x = _vector(state, 6, "state")
    u = _vector(inputs, 3, "inputs")

    tensions = (0.0, x[0], x[1], x[2], 0.0)
    roller_v = surface_velocities(x, active_params)
    velocities = (active_params.v_ref_mps, roller_v[0], roller_v[1], roller_v[2])

    tension_derivatives: list[float] = []
    for span_index in range(3):
        length_m = active_params.L_m[span_index]
        t_prev = tensions[span_index]
        t_i = tensions[span_index + 1]
        v_prev = velocities[span_index]
        v_i = velocities[span_index + 1]
        elastic = active_params.EA_N / length_m * (v_i - v_prev)
        transport = (t_prev * v_prev - t_i * v_i) / length_m
        tension_derivatives.append(elastic + transport)

    omega_derivatives: list[float] = []
    for roller_index in range(3):
        radius_m = active_params.R_m[roller_index]
        inertia_kgm2 = active_params.J_kgm2[roller_index]
        friction = active_params.f_Nms_per_rad[roller_index]
        v_i = roller_v[roller_index]
        t_i = tensions[roller_index + 1]
        t_next = tensions[roller_index + 2]

        dv_dt = (radius_m * radius_m / inertia_kgm2) * (t_next - t_i)
        dv_dt -= (friction / inertia_kgm2) * v_i
        dv_dt += (radius_m / inertia_kgm2) * u[roller_index]
        omega_derivatives.append(dv_dt / radius_m)

    return (
        tension_derivatives[0],
        tension_derivatives[1],
        tension_derivatives[2],
        omega_derivatives[0],
        omega_derivatives[1],
        omega_derivatives[2],
    )
