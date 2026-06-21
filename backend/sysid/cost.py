"""One-step prediction-error cost for seven-parameter R2R SysID."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from backend.models.equations import INPUT_NAMES, PARAMETER_NAMES, R2RParameters, STATE_NAMES

VELOCITY_COLUMN_OPTIONS = (
    ("v_UW_m_s", "v_UW"),
    ("v_Nip_m_s", "v_Nip"),
    ("v_RW_m_s", "v_RW"),
)


def theta_from_params(params: R2RParameters) -> dict[str, float]:
    """Return true paper ratio parameters from physical model parameters."""

    kt = tuple(
        radius * radius / inertia
        for radius, inertia in zip(params.roller_radius_m, params.inertia_kg_m2, strict=True)
    )
    kf = tuple(
        friction / inertia
        for friction, inertia in zip(params.kf, params.inertia_kg_m2, strict=True)
    )
    return {
        "kt_UW": kt[0],
        "kt_Nip": kt[1],
        "kt_RW": kt[2],
        "kf_UW": kf[0],
        "kf_Nip": kf[1],
        "kf_RW": kf[2],
        "EA": float(params.EA),
    }


def theta_array(theta: Mapping[str, float] | Sequence[float]) -> np.ndarray:
    """Return theta as `[kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]`."""

    if isinstance(theta, Mapping):
        return np.array([float(theta[name]) for name in PARAMETER_NAMES], dtype=float)
    values = np.asarray(theta, dtype=float)
    if values.shape != (7,):
        raise ValueError("theta must contain exactly 7 parameters")
    return values


def theta_dict(theta: Mapping[str, float] | Sequence[float]) -> dict[str, float]:
    """Return theta as a named dictionary in paper parameter order."""

    values = theta_array(theta)
    return {name: float(value) for name, value in zip(PARAMETER_NAMES, values, strict=True)}


def _row_value(row: Mapping[str, float], key: str) -> float:
    try:
        return float(row[key])
    except KeyError as exc:
        raise ValueError(f"SysID row is missing required column '{key}'") from exc


def surface_velocity(row: Mapping[str, float], roller_index: int, params: R2RParameters) -> float:
    """Read or derive one roller surface velocity from a logged row."""

    for column in VELOCITY_COLUMN_OPTIONS[roller_index]:
        if column in row:
            return float(row[column])
    omega_name = STATE_NAMES[3 + roller_index]
    if omega_name in row:
        return float(row[omega_name]) * params.roller_radius_m[roller_index]
    expected = ", ".join((*VELOCITY_COLUMN_OPTIONS[roller_index], omega_name))
    raise ValueError(f"SysID row is missing velocity data for roller {roller_index}; expected one of {expected}")


def state_from_row(row: Mapping[str, float]) -> tuple[float, float, float, float, float, float]:
    """Return state vector values from one logged row."""

    return tuple(_row_value(row, name) for name in STATE_NAMES)  # type: ignore[return-value]


def validate_sysid_rows(rows: Sequence[Mapping[str, float]], params: R2RParameters) -> None:
    """Validate the minimum columns needed for one-step prediction residuals."""

    if len(rows) < 3:
        raise ValueError("at least 3 logged rows are required for SysID")
    for row in rows:
        _row_value(row, "time_s")
        for name in (*STATE_NAMES[:3], *INPUT_NAMES):
            _row_value(row, name)
        for roller_index in range(3):
            surface_velocity(row, roller_index, params)


def time_steps(rows: Sequence[Mapping[str, float]]) -> list[float]:
    """Return strictly positive row-to-row sample periods."""

    steps = [float(rows[index + 1]["time_s"]) - float(rows[index]["time_s"]) for index in range(len(rows) - 1)]
    if any(step <= 0 or not math.isfinite(step) for step in steps):
        raise ValueError("row time_s values must be strictly increasing and finite")
    return steps


def _tension_delta(row: Mapping[str, float], roller_index: int) -> float:
    tensions = (float(row["T1"]), float(row["T2"]), float(row["T3"]))
    if roller_index == 0:
        return tensions[1] - tensions[0]
    if roller_index == 1:
        return tensions[2] - tensions[1]
    return -tensions[2]


def one_step_prediction_residuals(
    theta: Mapping[str, float] | Sequence[float],
    rows: Sequence[Mapping[str, float]],
    params: R2RParameters,
) -> np.ndarray:
    """Return finite-difference one-step prediction residuals.

    Roller residuals use:
        dv_i/dt = kt_i*(T_{i+1} - T_i + u_i/R_i) - kf_i*v_i

    Tension residuals use:
        dT_i/dt = EA/L_i*(v_i - v_{i-1}) + (T_{i-1}v_{i-1} - T_i*v_i)/L_i
    """

    validate_sysid_rows(rows, params)
    values = theta_array(theta)
    kt = values[:3]
    kf = values[3:6]
    ea = float(values[6])
    residuals: list[float] = []
    dt_values = time_steps(rows)

    for index, dt in enumerate(dt_values):
        row = rows[index]
        next_row = rows[index + 1]
        velocities = tuple(surface_velocity(row, roller, params) for roller in range(3))
        next_velocities = tuple(surface_velocity(next_row, roller, params) for roller in range(3))

        for roller in range(3):
            observed_dv = (next_velocities[roller] - velocities[roller]) / dt
            radius = params.roller_radius_m[roller]
            predicted_dv = kt[roller] * (_tension_delta(row, roller) + _row_value(row, INPUT_NAMES[roller]) / radius)
            predicted_dv -= kf[roller] * velocities[roller]
            residuals.append(observed_dv - predicted_dv)

        tensions = (float(row["T1"]), float(row["T2"]), float(row["T3"]))
        next_tensions = (float(next_row["T1"]), float(next_row["T2"]), float(next_row["T3"]))
        tension_prev = (0.0, tensions[0], tensions[1])
        velocity_prev = (params.feeder_velocity_m_s, velocities[0], velocities[1])
        for span in range(3):
            observed_dT = (next_tensions[span] - tensions[span]) / dt
            length = params.span_length_m[span]
            predicted_dT = ea / length * (velocities[span] - velocity_prev[span])
            predicted_dT += (tension_prev[span] * velocity_prev[span] - tensions[span] * velocities[span]) / length
            residuals.append(observed_dT - predicted_dT)

    return np.asarray(residuals, dtype=float)


def one_step_prediction_cost(
    theta: Mapping[str, float] | Sequence[float],
    rows: Sequence[Mapping[str, float]],
    params: R2RParameters,
) -> float:
    """Return `0.5 * sum(residual_i^2)` for one-step prediction residuals."""

    residuals = one_step_prediction_residuals(theta, rows, params)
    return float(0.5 * np.dot(residuals, residuals))
