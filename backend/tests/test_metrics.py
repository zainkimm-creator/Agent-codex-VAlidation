from pytest import approx

from backend.sysid.metrics import rmse_theta


def test_rmse_theta_known_example_passes():
    theta_true = {
        "kt_UW": 1.0,
        "kt_Nip": 2.0,
        "kt_RW": 4.0,
        "kf_UW": 5.0,
        "kf_Nip": 10.0,
        "kf_RW": 20.0,
        "EA": 100.0,
    }
    theta_est = {
        "kt_UW": 1.0,
        "kt_Nip": 2.2,
        "kt_RW": 3.2,
        "kf_UW": 6.5,
        "kf_Nip": 6.0,
        "kf_RW": 30.0,
        "EA": 40.0,
    }

    assert rmse_theta(theta_est, theta_true) == approx(0.3)
