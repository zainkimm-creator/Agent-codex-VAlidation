from dataclasses import replace
from math import isfinite

from backend.models.r2r_dynamics import R2RDynamicsParams, r2r_derivatives


def test_derivative_output_shape_is_6_and_finite():
    params = R2RDynamicsParams()
    state = [12.0, 12.0, 12.0, 0.5 / 0.15, 0.5 / 0.1, 0.5 / 0.15]

    dx = r2r_derivatives(state, [0.0, 0.0, 0.0], params)

    assert len(dx) == 6
    assert all(isfinite(value) for value in dx)


def test_increasing_downstream_velocity_changes_tension_derivative():
    params = R2RDynamicsParams()
    base_state = [12.0, 12.0, 12.0, 0.5 / 0.15, 0.5 / 0.1, 0.5 / 0.15]
    faster_nip = [12.0, 12.0, 12.0, 0.5 / 0.15, 0.7 / 0.1, 0.5 / 0.15]

    base_dx = r2r_derivatives(base_state, [0.0, 0.0, 0.0], params)
    faster_dx = r2r_derivatives(faster_nip, [0.0, 0.0, 0.0], params)

    assert faster_dx[1] > base_dx[1]


def test_friction_term_reduces_roller_acceleration():
    no_friction = R2RDynamicsParams(f_Nms_per_rad=(0.0, 0.0, 0.0))
    with_friction = replace(no_friction, f_Nms_per_rad=(1.0, 1.0, 1.0))
    state = [0.0, 0.0, 0.0, 10.0, 10.0, 10.0]
    inputs = [1.0, 1.0, 1.0]

    dx_no_friction = r2r_derivatives(state, inputs, no_friction)
    dx_with_friction = r2r_derivatives(state, inputs, with_friction)

    assert dx_with_friction[3] < dx_no_friction[3]
    assert dx_with_friction[4] < dx_no_friction[4]
    assert dx_with_friction[5] < dx_no_friction[5]
