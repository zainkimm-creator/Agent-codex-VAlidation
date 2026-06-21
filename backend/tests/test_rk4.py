from math import isfinite

from backend.models.r2r_dynamics import R2RDynamicsParams, r2r_derivatives
from backend.models.rk4 import rk4_step


def test_rk4_updates_state_without_nan():
    params = R2RDynamicsParams()
    state = [12.0, 12.0, 12.0, 0.5 / 0.15, 0.5 / 0.1, 0.5 / 0.15]
    inputs = [0.0, 0.0, 0.0]

    next_state = rk4_step(r2r_derivatives, state, inputs, params, 0.001)

    assert len(next_state) == 6
    assert all(isfinite(value) for value in next_state)
    assert next_state != tuple(state)
