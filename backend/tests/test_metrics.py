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
        "kt_UW": 1.1,
        "kt_Nip": 1.8,
        "kt_RW": 4.4,
        "kf_UW": 4.5,
        "kf_Nip": 11.0,
        "kf_RW": 18.0,
        "EA": 110.0,
    }

    assert rmse_theta(theta_est, theta_true) == approx(0.1)
