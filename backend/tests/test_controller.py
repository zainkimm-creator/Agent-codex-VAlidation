from pytest import approx

from backend.models.controller import (
    CascadePIController,
    ControllerConfig,
    feedforward_torques,
    steady_state_omega,
)
from backend.models.equations import R2RParameters


def _nominal_state(params: R2RParameters) -> tuple[float, ...]:
    omega = steady_state_omega(params, 1.0, params.tension_ref_N)
    return params.tension_ref_N + omega


def test_zero_error_returns_feedforward_only_torque():
    params = R2RParameters()
    state = _nominal_state(params)
    controller = CascadePIController(
        ControllerConfig(
            target_tension_N=params.tension_ref_N,
            line_speed_m_s=1.0,
        )
    )

    action = controller.update(state, 0.01, params)

    assert action.velocity_error_rad_s == approx((0.0, 0.0, 0.0))
    assert action.motor_torque_Nm == approx(feedforward_torques(state, params))
    assert action.motor_torque_Nm == approx(action.feedforward_torque_Nm)


def test_larger_kp_star_creates_larger_corrective_torque():
    params = R2RParameters()
    state = (
        params.tension_ref_N[0] - 1.0,
        params.tension_ref_N[1],
        params.tension_ref_N[2],
        *steady_state_omega(params, 1.0, params.tension_ref_N),
    )
    low_gain = CascadePIController(
        ControllerConfig(target_tension_N=params.tension_ref_N, Kp_star=25.0)
    )
    high_gain = CascadePIController(
        ControllerConfig(target_tension_N=params.tension_ref_N, Kp_star=100.0)
    )

    low_action = low_gain.update(state, 0.01, params)
    high_action = high_gain.update(state, 0.01, params)

    low_correction = abs(low_action.motor_torque_Nm[0] - low_action.feedforward_torque_Nm[0])
    high_correction = abs(high_action.motor_torque_Nm[0] - high_action.feedforward_torque_Nm[0])
    assert high_correction > low_correction


def test_uw_signed_error_maps_to_higher_web_speed_reference():
    params = R2RParameters()
    steady_omega = steady_state_omega(params, 1.0, params.tension_ref_N)
    state = (
        params.tension_ref_N[0] - 1.0,
        params.tension_ref_N[1],
        params.tension_ref_N[2],
        *steady_omega,
    )
    controller = CascadePIController(
        ControllerConfig(target_tension_N=params.tension_ref_N, Kp_star=100.0)
    )

    action = controller.update(state, 0.01, params)

    assert action.signed_tension_error_N[0] < 0.0
    assert action.velocity_ref_rad_s[0] > steady_omega[0]


def test_controller_returns_three_motor_torques():
    params = R2RParameters()
    controller = CascadePIController(ControllerConfig(target_tension_N=params.tension_ref_N))

    action = controller.update(_nominal_state(params), 0.01, params)

    assert len(action.motor_torque_Nm) == 3
    assert not hasattr(action, "inputs_V")


def test_integral_state_updates_with_signed_tension_error():
    params = R2RParameters()
    state = (
        params.tension_ref_N[0] - 2.0,
        params.tension_ref_N[1] - 3.0,
        params.tension_ref_N[2] + 4.0,
        *steady_state_omega(params, 1.0, params.tension_ref_N),
    )
    controller = CascadePIController(ControllerConfig(target_tension_N=params.tension_ref_N))

    action = controller.update(state, 0.5, params)

    assert action.tension_error_N == approx((2.0, 3.0, -4.0))
    assert action.signed_tension_error_N == approx((-2.0, 3.0, -4.0))
    assert action.tension_integral_N_s == approx((-1.0, 1.5, -2.0))
    assert tuple(controller.tension_integral_N_s) == approx((-1.0, 1.5, -2.0))
