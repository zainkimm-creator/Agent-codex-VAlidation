"""Cascade PI plus feedforward controller for the R2R model."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, sqrt
from typing import Sequence

from .equations import R2RParameters, validate_vector


SIGMA = (-1.0, 1.0, 1.0)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class ControllerConfig:
    """Controller gains and setpoints with explicit units."""

    target_tension_N: tuple[float, float, float] = (42.0, 44.0, 43.0)
    line_speed_m_s: float = 1.0
    Kp_star: float = 0.0525
    TI_s: float = 2.00
    alpha: float = 1.4
    feedforward_enabled: bool = True
    Kp_star_m_s_per_N: float = 0.000010
    velocity_Kp_Nm_per_rad_s: float = 0.200
    velocity_TI_s: float = 0.20
    max_voltage_V: float = 24.0

    def __post_init__(self) -> None:
        if len(self.target_tension_N) != 3:
            raise ValueError("target_tension_N must contain exactly 3 values")
        if any(not isfinite(value) for value in self.target_tension_N):
            raise ValueError("target_tension_N must contain finite values")
        if self.line_speed_m_s <= 0 or not isfinite(self.line_speed_m_s):
            raise ValueError("line_speed_m_s must be finite and positive")
        if self.Kp_star < 0 or not isfinite(self.Kp_star):
            raise ValueError("Kp_star must be finite and non-negative")
        if self.TI_s <= 0 or not isfinite(self.TI_s):
            raise ValueError("TI_s must be finite and positive")
        if self.alpha <= 0 or not isfinite(self.alpha):
            raise ValueError("alpha must be finite and positive")
        if self.Kp_star_m_s_per_N < 0 or not isfinite(self.Kp_star_m_s_per_N):
            raise ValueError("Kp_star_m_s_per_N must be finite and non-negative")
        if self.velocity_Kp_Nm_per_rad_s <= 0 or not isfinite(self.velocity_Kp_Nm_per_rad_s):
            raise ValueError("velocity_Kp_Nm_per_rad_s must be finite and positive")
        if self.velocity_TI_s <= 0 or not isfinite(self.velocity_TI_s):
            raise ValueError("velocity_TI_s must be finite and positive")
        if self.max_voltage_V <= 0 or not isfinite(self.max_voltage_V):
            raise ValueError("max_voltage_V must be finite and positive")

    @property
    def effective_Kp_star(self) -> float:
        """Return the active normalized tension gain.

        New controller code should use `Kp_star`. The legacy
        `Kp_star_m_s_per_N` field remains accepted for older validation
        candidates; when it is changed from its historical default and
        `Kp_star` is still the default, map it onto the normalized scale.
        """

        if self.Kp_star == 0.0525 and self.Kp_star_m_s_per_N != 0.000010:
            return self.Kp_star_m_s_per_N * 10_000_000.0
        return self.Kp_star


@dataclass
class ControlAction:
    """Controller output and diagnostics for one sample."""

    motor_torque_Nm: tuple[float, float, float]
    velocity_ref_rad_s: tuple[float, float, float]
    tension_error_N: tuple[float, float, float]
    signed_tension_error_N: tuple[float, float, float]
    tension_integral_N_s: tuple[float, float, float]
    velocity_gain_Nm_per_rad_s: tuple[float, float, float]
    velocity_error_rad_s: tuple[float, float, float]
    feedforward_torque_Nm: tuple[float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "motor_torque_Nm": list(self.motor_torque_Nm),
            "velocity_ref_rad_s": list(self.velocity_ref_rad_s),
            "tension_error_N": list(self.tension_error_N),
            "signed_tension_error_N": list(self.signed_tension_error_N),
            "tension_integral_N_s": list(self.tension_integral_N_s),
            "velocity_gain_Nm_per_rad_s": list(self.velocity_gain_Nm_per_rad_s),
            "velocity_error_rad_s": list(self.velocity_error_rad_s),
            "feedforward_torque_Nm": list(self.feedforward_torque_Nm),
        }


def steady_state_surface_velocities(
    params: R2RParameters,
    line_speed_m_s: float,
    target_tension_N: Sequence[float] | None = None,
) -> tuple[float, float, float]:
    """Return steady surface speeds from Eq. (1) for target tensions.

    At steady state, Eq. (1) gives
    `v_i(EA - T_i) = v_{i-1}(EA - T_{i-1})`, with `T0 = 0`.
    """

    refs = validate_vector(target_tension_N or params.tension_ref_N, 3, "target_tension_N")
    velocities: list[float] = []
    previous_tension = 0.0
    previous_velocity = float(line_speed_m_s)
    for tension in refs:
        denominator = params.EA - tension
        if denominator <= 0:
            raise ValueError("target tension must be less than EA for steady-state speed calculation")
        velocity = previous_velocity * (params.EA - previous_tension) / denominator
        velocities.append(velocity)
        previous_tension = tension
        previous_velocity = velocity
    return tuple(velocities)  # type: ignore[return-value]


def steady_state_omega(
    params: R2RParameters,
    line_speed_m_s: float,
    target_tension_N: Sequence[float] | None = None,
) -> tuple[float, float, float]:
    """Return steady `omega_ss_i` for the target tensions."""

    surface_speeds = steady_state_surface_velocities(params, line_speed_m_s, target_tension_N)
    return tuple(
        surface_speeds[i] / params.roller_radius_m[i]
        for i in range(3)
    )  # type: ignore[return-value]


def velocity_gains(
    params: R2RParameters,
    alpha: float = 1.4,
) -> tuple[float, float, float]:
    """Return `Kvel_i = alpha * J_i * sqrt(EA*R_i^2/(J_i*L_i))`."""

    gains = []
    for radius, inertia, length in zip(
        params.roller_radius_m,
        params.inertia_kg_m2,
        params.span_length_m,
        strict=True,
    ):
        omega_n = sqrt(params.EA * radius * radius / (inertia * length))
        gains.append(alpha * inertia * omega_n)
    return tuple(gains)  # type: ignore[return-value]


def tension_load_feedforward_terms(
    state: Sequence[float],
    params: R2RParameters,
) -> tuple[float, float, float]:
    """Return tension-load compensation torques with isolated sign convention.

    The roller dynamics use the web load `R_i * (T_{i+1} - T_i)`, with
    `T4 = 0`. Feedforward compensates that load using the opposite sign:
    `R_i * (T_i - T_{i+1})`.
    """

    t1, t2, t3, *_ = validate_vector(state, 6, "state")
    tension_pairs = ((t1, t2), (t2, t3), (t3, 0.0))
    return tuple(
        params.roller_radius_m[i] * (t_i - t_next)
        for i, (t_i, t_next) in enumerate(tension_pairs)
    )


def feedforward_torques(
    state: Sequence[float],
    params: R2RParameters,
) -> tuple[float, float, float]:
    """Return `u_ff_i = tension_load_term + f_i * omega_i`."""

    x = validate_vector(state, 6, "state")
    omega = x[3:]
    tension_load = tension_load_feedforward_terms(x, params)
    return tuple(tension_load[i] + params.kf[i] * omega[i] for i in range(3))


@dataclass
class CascadePIController:
    """Cascade PI controller with outer tension loop and inner velocity loop."""

    config: ControllerConfig = field(default_factory=ControllerConfig)
    tension_integral_N_s: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity_integral_rad: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    def reset(self) -> None:
        self.tension_integral_N_s = [0.0, 0.0, 0.0]
        self.velocity_integral_rad = [0.0, 0.0, 0.0]

    def update(
        self,
        state: Sequence[float],
        dt_s: float,
        params: R2RParameters | None = None,
    ) -> ControlAction:
        """Compute held motor-torque inputs for the next controller interval."""

        active_params = params or R2RParameters()
        x = validate_vector(state, 6, "state")
        measured_tension = x[:3]
        measured_omega = x[3:]
        tension_error = tuple(
            self.config.target_tension_N[i] - measured_tension[i] for i in range(3)
        )
        signed_error = tuple(SIGMA[i] * tension_error[i] for i in range(3))
        for i in range(3):
            self.tension_integral_N_s[i] += signed_error[i] * dt_s

        v_corr_m_s = tuple(
            (active_params.span_length_m[i] / active_params.EA)
            * self.config.effective_Kp_star
            * (signed_error[i] + self.tension_integral_N_s[i] / self.config.TI_s)
            for i in range(3)
        )
        omega_ss = steady_state_omega(active_params, self.config.line_speed_m_s, self.config.target_tension_N)
        velocity_ref = tuple(
            omega_ss[i] + v_corr_m_s[i] / active_params.roller_radius_m[i]
            for i in range(3)
        )
        velocity_error = tuple(velocity_ref[i] - measured_omega[i] for i in range(3))

        kvel = velocity_gains(active_params, self.config.alpha)
        feedforward_torque = (
            feedforward_torques(x, active_params)
            if self.config.feedforward_enabled
            else (0.0, 0.0, 0.0)
        )
        torque_limits = tuple(active_params.kt[i] * self.config.max_voltage_V for i in range(3))
        feedback_torque = tuple(
            _clamp(kvel[i] * velocity_error[i], -torque_limits[i], torque_limits[i])
            for i in range(3)
        )
        torque_cmd = tuple(
            feedback_torque[i] + feedforward_torque[i]
            for i in range(3)
        )
        return ControlAction(
            motor_torque_Nm=torque_cmd,
            velocity_ref_rad_s=velocity_ref,
            tension_error_N=tension_error,
            signed_tension_error_N=signed_error,
            tension_integral_N_s=tuple(self.tension_integral_N_s),
            velocity_gain_Nm_per_rad_s=kvel,
            velocity_error_rad_s=velocity_error,
            feedforward_torque_Nm=feedforward_torque,
        )
