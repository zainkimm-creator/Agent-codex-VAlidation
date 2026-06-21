"""Fourth-order Runge-Kutta integration helpers."""

from __future__ import annotations

from math import isfinite
from typing import Callable, Sequence, TypeVar

ParamsT = TypeVar("ParamsT")
DerivativeFn = Callable[[Sequence[float], Sequence[float], ParamsT], Sequence[float]]


def _validate_step_vector(values: Sequence[float], expected: int, name: str) -> tuple[float, ...]:
    if len(values) != expected:
        raise ValueError(f"{name} must contain exactly {expected} values")
    result = tuple(float(value) for value in values)
    if not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def _add_scaled(base: Sequence[float], slope: Sequence[float], scale: float) -> tuple[float, ...]:
    return tuple(float(base[index]) + scale * float(slope[index]) for index in range(len(base)))


def rk4_step(
    f: DerivativeFn[ParamsT],
    x: Sequence[float],
    u: Sequence[float],
    params: ParamsT,
    dt: float,
) -> tuple[float, ...]:
    """Advance `x` one fixed RK4 step while holding `u` constant."""

    if dt <= 0 or not isfinite(dt):
        raise ValueError("dt must be finite and positive")

    state = _validate_step_vector(x, 6, "x")
    inputs = _validate_step_vector(u, 3, "u")

    k1 = _validate_step_vector(f(state, inputs, params), 6, "k1")
    k2 = _validate_step_vector(f(_add_scaled(state, k1, 0.5 * dt), inputs, params), 6, "k2")
    k3 = _validate_step_vector(f(_add_scaled(state, k2, 0.5 * dt), inputs, params), 6, "k3")
    k4 = _validate_step_vector(f(_add_scaled(state, k3, dt), inputs, params), 6, "k4")

    return tuple(
        state[index] + (dt / 6.0) * (k1[index] + 2.0 * k2[index] + 2.0 * k3[index] + k4[index])
        for index in range(6)
    )
