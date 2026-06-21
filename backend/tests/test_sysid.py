from pathlib import Path

import pytest

from backend.models.equations import R2RParameters
from backend.models.simulation import SimulationConfig, simulate
from backend.sysid.cost import one_step_prediction_cost, theta_from_params
from backend.sysid.estimator import estimate_parameters, load_parameters_from_config
from backend.validation.excitations import get_excitation_profile


def _sysid_rows():
    sim = simulate(
        config=SimulationConfig(duration_s=0.5, log_sample_time_s=0.010),
        excitation=get_excitation_profile("E_Toggle", 0.08),
        write_output=False,
    )
    return sim.rows


def test_theta_true_gives_lower_cost_than_wrong_theta():
    params = R2RParameters()
    rows = _sysid_rows()
    theta_true = theta_from_params(params)
    theta_wrong = {name: value * 1.5 for name, value in theta_true.items()}

    true_cost = one_step_prediction_cost(theta_true, rows, params)
    wrong_cost = one_step_prediction_cost(theta_wrong, rows, params)

    assert true_cost < wrong_cost


def test_estimator_returns_7_parameters_and_convergence_status():
    result = estimate_parameters(_sysid_rows(), summary_name=None)

    assert set(result.theta_est) == {"kt_UW", "kt_Nip", "kt_RW", "kf_UW", "kf_Nip", "kf_RW", "EA"}
    assert result.estimates == result.theta_est
    assert len(result.error_table) == 7
    assert result.convergence_status
    assert isinstance(result.success, bool)
    assert result.nfev > 0


def test_missing_config_fails_clearly(tmp_path: Path):
    missing_config = tmp_path / "missing_plants.yaml"

    with pytest.raises(FileNotFoundError, match="Plant config not found"):
        load_parameters_from_config("P01", missing_config)
